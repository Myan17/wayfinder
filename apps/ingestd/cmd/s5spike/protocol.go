// Spike S5 (ADR-0004): the IndexRepo protocol of DESIGN §9.3.3–9.3.5, with a stand-in build.
//
// Claim, final head check and fenced activation are the real transactions. The build writes one
// generation with one representation and occurrence instead of chunking and embedding, because S5
// tests scheduling, not indexing. barrier() is where the harness injects pushes, kills and pauses.
package main

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
)

type IndexRepoArgs struct {
	RepoID int64 `json:"repo_id"`
}

func (IndexRepoArgs) Kind() string { return "index_repo" }

type indexWorker struct {
	river.WorkerDefaults[IndexRepoArgs]
	pool     *pgxpool.Pool
	barriers *barriers
	claimTTL string // Postgres interval, e.g. "2 seconds"
	failOnce bool   // B5 scenarios: the first attempt fails before claiming
}

var errInjected = errors.New("s5: injected first-attempt failure")

func (w *indexWorker) Work(ctx context.Context, job *river.Job[IndexRepoArgs]) error {
	if w.failOnce && job.Attempt == 1 {
		return errInjected // DESIGN §9.3.3 "during retry": the retry is attempt 2
	}
	if job.Attempt > 1 {
		w.barriers.hit("B5") // after a failed attempt, before the next claim
	}
	w.barriers.hit("B1") // accepted, before any claim
	repo := job.Args.RepoID
	token := uuid.New()
	var d int64
	var base *int64
	err := w.pool.QueryRow(ctx, `
		UPDATE repository SET claim_token = $2, claim_expires_at = now() + $3::interval
		 WHERE id = $1 AND (claim_expires_at IS NULL OR claim_expires_at < now())
		RETURNING desired_generation, active_generation_id`, repo, token, w.claimTTL).Scan(&d, &base)
	if errors.Is(err, pgx.ErrNoRows) {
		emit("claim busy repo=%d", repo) // another worker holds a live claim; it owns the work
		return nil
	}
	if err != nil {
		return err
	}
	emit("claim token=%s d=%d", token, d)
	for {
		gen, err := w.build(ctx, repo, token, d)
		if err != nil {
			return err
		}
		w.barriers.hit("B3") // final head check: between reading D and deciding
		var now int64
		if err := w.pool.QueryRow(ctx, `SELECT desired_generation FROM repository WHERE id = $1`, repo).Scan(&now); err != nil {
			return err
		}
		if now != d {
			w.fail(ctx, gen, "superseded")
			d = now
			continue // re-claim immediately: the claim is still ours, build toward the new target
		}
		w.barriers.hit("B4'") // before the activation transaction takes the row lock
		ok, err := w.activate(ctx, repo, token, d, base, gen)
		if err != nil {
			return err
		}
		if !ok {
			w.fail(ctx, gen, "activation refused")
			emit("refused gen=%d token=%s", gen, token)
			return nil
		}
		emit("activated gen=%d d=%d token=%s", gen, d, token)
		if err := w.pool.QueryRow(ctx, `SELECT desired_generation FROM repository WHERE id = $1`, repo).Scan(&now); err != nil {
			return err
		}
		if now == d {
			_, err := w.pool.Exec(ctx, `UPDATE repository SET claim_token = NULL, claim_expires_at = NULL
				WHERE id = $1 AND claim_token = $2`, repo, token)
			return err
		}
		base, d = &gen, now // advanced during activation: keep the claim and go again
		if _, err := w.pool.Exec(ctx, `UPDATE repository SET claim_expires_at = now() + $3::interval
			WHERE id = $1 AND claim_token = $2`, repo, token, w.claimTTL); err != nil {
			return err
		}
	}
}

func (w *indexWorker) build(ctx context.Context, repo int64, token uuid.UUID, d int64) (int64, error) {
	var gen int64
	if err := w.pool.QueryRow(ctx, `
		INSERT INTO generation (repo_id, desired_generation, commit_sha, spec_id, chunker_version, status, lease_token)
		VALUES ($1, $2, $4, (SELECT min(id) FROM embedding_spec), 's5', 'building', $3)
		RETURNING id`, repo, d, token, fmt.Sprintf("c%d-%s", d, token)).Scan(&gen); err != nil {
		return 0, err
	}
	w.barriers.hit("B2") // mid-build
	body := fmt.Sprintf("g%d", gen)
	_, err := w.pool.Exec(ctx, `
		WITH c AS (INSERT INTO content (content_hash, body, token_count) VALUES (sha256($3::bytea), $3, 1) RETURNING content_hash),
		     r AS (INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header, body_text)
		           SELECT $1, (SELECT min(id) FROM embedding_spec), content_hash, content_hash, 'h', $3 FROM c RETURNING id)
		INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha, start_line, end_line)
		SELECT $1, $2, id, 'f.go', 'b', 1, 1 FROM r`, repo, gen, body)
	if err != nil {
		return 0, err
	}
	_, err = w.pool.Exec(ctx, `UPDATE generation SET status = 'ready', chunk_count = 1 WHERE id = $1`, gen)
	return gen, err
}

// activate is §9.3.5's fenced transaction. It returns false, not an error, when a fence refuses it.
func (w *indexWorker) activate(ctx context.Context, repo int64, token uuid.UUID, d int64, base *int64, gen int64) (bool, error) {
	tx, err := w.pool.Begin(ctx)
	if err != nil {
		return false, err
	}
	defer tx.Rollback(ctx) //nolint:errcheck // no-op after Commit
	var desired int64
	var active *int64
	var claim *uuid.UUID
	var live bool
	if err := tx.QueryRow(ctx, `
		SELECT desired_generation, active_generation_id, claim_token, claim_expires_at > now()
		  FROM repository WHERE id = $1 FOR UPDATE`, repo).Scan(&desired, &active, &claim, &live); err != nil {
		return false, err
	}
	if claim == nil || *claim != token || !live || desired != d || !sameGen(active, base) {
		return false, nil
	}
	steps := []struct {
		sql string
		arg any
	}{
		{`UPDATE representation SET live = true WHERE id IN (SELECT representation_id FROM occurrence WHERE generation_id = $1)`, gen},
		{`UPDATE representation SET live = false WHERE id IN (SELECT representation_id FROM occurrence WHERE generation_id = $1)`, base},
		{`UPDATE generation SET status = 'retired' WHERE id = $1`, base},
		{`UPDATE generation SET status = 'active', activated_at = clock_timestamp() WHERE id = $1`, gen},
	}
	for _, st := range steps {
		if _, err := tx.Exec(ctx, st.sql, st.arg); err != nil {
			return false, err
		}
	}
	tag, err := tx.Exec(ctx, `UPDATE repository SET active_generation_id = $1, updated_at = now()
		WHERE id = $2 AND active_generation_id IS NOT DISTINCT FROM $3`, gen, repo, base)
	if err != nil {
		return false, err
	}
	if tag.RowsAffected() != 1 {
		return false, nil
	}
	w.barriers.hit("B4") // inside the transaction, before COMMIT
	return true, tx.Commit(ctx)
}

func (w *indexWorker) fail(ctx context.Context, gen int64, why string) {
	_, _ = w.pool.Exec(ctx, `UPDATE generation SET status = 'failed' WHERE id = $1 AND status IN ('building','ready')`, gen)
	emit("failed gen=%d reason=%q", gen, why)
}

func sameGen(a, b *int64) bool {
	return (a == nil && b == nil) || (a != nil && b != nil && *a == *b)
}

// emit writes one protocol event line for the harness. Stdout is the harness's only channel.
func emit(format string, args ...any) {
	fmt.Fprintf(os.Stdout, "EVENT "+format+"\n", args...)
}
