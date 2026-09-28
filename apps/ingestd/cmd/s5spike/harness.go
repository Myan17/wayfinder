package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
	"github.com/riverqueue/river/riverdriver/riverpgxv5"
	"github.com/riverqueue/river/rivermigrate"
)

const repoID = 1

// A run: one fresh database, ADR-0004's pinned starting state, one injection, then the rules.
type run struct {
	ctx      context.Context
	dsn      string
	pool     *pgxpool.Pool
	inserter *river.Client[pgx.Tx]
	procs    map[string]*proc
	claimTTL time.Duration
	failures []string
	errs     []string
}

type proc struct {
	id     string
	cmd    *exec.Cmd
	stdin  *os.File
	lines  chan string
	alive  bool
	events []string
}

// freshDatabase creates a database from template0, applies every migration's up section and
// River's own migrations, and returns its DSN (ADR-0004: nothing carried over between runs).
func freshDatabase(ctx context.Context, admin, name, root string) (string, error) {
	a, err := pgx.Connect(ctx, admin)
	if err != nil {
		return "", err
	}
	defer a.Close(ctx)
	if _, err := a.Exec(ctx, fmt.Sprintf(`DROP DATABASE IF EXISTS %q WITH (FORCE)`, name)); err != nil {
		return "", err
	}
	if _, err := a.Exec(ctx, fmt.Sprintf(`CREATE DATABASE %q TEMPLATE template0`, name)); err != nil {
		return "", err
	}
	cfg := a.Config().Copy()
	dsn := strings.Replace(admin, "/"+cfg.Database, "/"+name, 1)
	c, err := pgx.Connect(ctx, dsn)
	if err != nil {
		return "", err
	}
	defer c.Close(ctx)
	files, _ := filepath.Glob(filepath.Join(root, "db", "migrations", "*.sql"))
	upRe := regexp.MustCompile(`(?s)-- migrate:up(.*?)-- migrate:down`)
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			return "", err
		}
		m := upRe.FindSubmatch(b)
		if m == nil {
			return "", fmt.Errorf("%s: no up section", f)
		}
		if _, err := c.Exec(ctx, string(m[1])); err != nil {
			return "", fmt.Errorf("%s: %w", f, err)
		}
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return "", err
	}
	defer pool.Close()
	mig, err := rivermigrate.New(riverpgxv5.New(pool), nil)
	if err != nil {
		return "", err
	}
	_, err = mig.Migrate(ctx, rivermigrate.DirectionUp, nil)
	return dsn, err
}

// seed writes ADR-0004's quiescent starting state: one active baseline generation at
// desired_generation 1, pointed to by the repository, with no claim and no job.
func (r *run) seed() error {
	_, err := r.pool.Exec(r.ctx, `
		INSERT INTO connection (id, mode, account_login, state, state_observed_at, state_valid_until, egress_policy, config)
		VALUES (1, 'public_readonly', 's5', 'active', now(), now() + interval '1 day', '{}', '{}');
		INSERT INTO repository (id, connection_id, github_repo_id, full_name, default_branch, visibility,
		                        visibility_observed_at, visibility_valid_until, serving_state, data_class, desired_generation)
		VALUES (1, 1, 1, 's5/r', 'main', 'public', now(), now() + interval '1 day', 'active', 'public', 1);
		INSERT INTO embedding_spec (model_ref, model_digest, runtime, doc_template, query_template, pooling,
		                            normalize, dimension, truncation, tokenizer_ref)
		VALUES ('s5', 's5', 's5', 'd', 'q', 'mean', true, 768, 'end', 's5');
		INSERT INTO generation (id, repo_id, desired_generation, commit_sha, spec_id, chunker_version, status, activated_at, chunk_count)
		VALUES (1, 1, 1, 'c1-baseline', (SELECT min(id) FROM embedding_spec), 's5', 'active', clock_timestamp(), 0);
		SELECT setval('generation_id_seq', 1);
		UPDATE repository SET active_generation_id = 1 WHERE id = 1;`)
	return err
}

// preconditions asserts all five ADR-0004 starting-state conditions. A failure is an error, not a result.
func (r *run) preconditions() error {
	var n, activeCount, repoD, genD, jobs int
	var activeID *int64
	var claimNull bool
	err := r.pool.QueryRow(r.ctx, `
		SELECT (SELECT count(*) FROM generation WHERE repo_id = 1),
		       (SELECT count(*) FROM generation WHERE repo_id = 1 AND status = 'active'),
		       r.active_generation_id, r.desired_generation,
		       (SELECT desired_generation FROM generation WHERE id = r.active_generation_id),
		       r.claim_token IS NULL AND r.claim_expires_at IS NULL,
		       (SELECT count(*) FROM river_job WHERE kind = 'index_repo' AND finalized_at IS NULL)
		  FROM repository r WHERE r.id = 1`).Scan(&n, &activeCount, &activeID, &repoD, &genD, &claimNull, &jobs)
	switch {
	case err != nil:
		return err
	case n != 1 || activeCount != 1:
		return fmt.Errorf("precondition 1: %d generations, %d active; want exactly one active", n, activeCount)
	case activeID == nil || *activeID != 1:
		return fmt.Errorf("precondition 2: active_generation_id %v, want the baseline", activeID)
	case repoD != 1 || genD != 1:
		return fmt.Errorf("precondition 3: repository desired %d, baseline desired %d, want 1 and 1", repoD, genD)
	case !claimNull:
		return fmt.Errorf("precondition 4: a claim is present")
	case jobs != 0:
		return fmt.Errorf("precondition 5: %d outstanding IndexRepo jobs", jobs)
	}
	return nil
}

// push is an accepted source event: increment desired_generation and enqueue, in one transaction,
// with no unique-job options (S5-5).
func (r *run) push() error {
	tx, err := r.pool.Begin(r.ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(r.ctx) //nolint:errcheck
	if _, err := tx.Exec(r.ctx, `UPDATE repository SET desired_generation = desired_generation + 1 WHERE id = 1`); err != nil {
		return err
	}
	if _, err := r.inserter.InsertTx(r.ctx, tx, IndexRepoArgs{RepoID: repoID}, nil); err != nil {
		return err
	}
	return tx.Commit(r.ctx)
}

func (r *run) start(id, barrier string, failOnce bool) (*proc, error) {
	args := []string{"worker", "-dsn", r.dsn, "-id", id, "-claim-ttl", fmt.Sprintf("%d milliseconds", r.claimTTL.Milliseconds())}
	if barrier != "" {
		args = append(args, "-barrier", barrier)
	}
	if failOnce {
		args = append(args, "-fail-once")
	}
	cmd := exec.Command(os.Args[0], args...)
	inR, inW, err := os.Pipe()
	if err != nil {
		return nil, err
	}
	cmd.Stdin = inR
	out, err := cmd.StdoutPipe()
	if err != nil {
		return nil, err
	}
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	p := &proc{id: id, cmd: cmd, stdin: inW, lines: make(chan string, 256), alive: true}
	go func() {
		s := bufio.NewScanner(out)
		for s.Scan() {
			p.lines <- s.Text()
		}
		close(p.lines)
	}()
	r.procs[id] = p
	if _, err := p.await("READY", 20*time.Second); err != nil {
		return nil, err
	}
	return p, nil
}

// await reads the process's output until a line with the prefix, recording every EVENT line.
func (p *proc) await(prefix string, d time.Duration) (string, error) {
	deadline := time.After(d)
	for {
		select {
		case l, ok := <-p.lines:
			if !ok {
				return "", fmt.Errorf("%s exited before %q", p.id, prefix)
			}
			if strings.HasPrefix(l, "EVENT ") {
				p.events = append(p.events, strings.TrimPrefix(l, "EVENT "))
			}
			if strings.HasPrefix(l, prefix) || strings.HasPrefix(l, "EVENT "+prefix) {
				return l, nil
			}
		case <-deadline:
			return "", fmt.Errorf("%s: no %q within %s", p.id, prefix, d)
		}
	}
}

func (p *proc) resume() { _, _ = p.stdin.WriteString("\n") }

func (p *proc) signal(s syscall.Signal) {
	_ = p.cmd.Process.Signal(s)
	if s == syscall.SIGKILL {
		_, _ = p.cmd.Process.Wait()
		p.alive = false
	}
}

func (r *run) stopAll() {
	for _, p := range r.procs {
		if p.alive {
			_ = p.cmd.Process.Signal(syscall.SIGCONT)
			p.signal(syscall.SIGKILL)
		}
	}
}

func (r *run) liveIDs() []string {
	var ids []string
	for id, p := range r.procs {
		if p.alive {
			ids = append(ids, id)
		}
	}
	return ids
}
