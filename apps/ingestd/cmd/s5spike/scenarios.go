package main

import (
	"fmt"
	"strings"
	"syscall"
	"time"
)

type scenario struct {
	name, barrier, injection string // injection: push | kill | pushkill | pause
}

// scenarios is ADR-0004's list: B1..B5 x {push, kill, push then kill}, plus paused at B2 and B4'.
func scenarios() []scenario {
	var s []scenario
	for _, b := range []string{"B1", "B2", "B3", "B4", "B5"} {
		for _, inj := range []string{"push", "kill", "pushkill"} {
			s = append(s, scenario{b + "-" + inj, b, inj})
		}
	}
	return append(s, scenario{"B2-pause", "B2", "pause"}, scenario{"B4'-pause", "B4'", "pause"})
}

// execute runs one scenario on a seeded database whose initial push is already accepted.
func (r *run) execute(sc scenario) error {
	w1, err := r.start("w1", sc.barrier, sc.barrier == "B5")
	if err != nil {
		return err
	}
	if _, err := w1.await("BARRIER", 30*time.Second); err != nil {
		return err
	}
	pushed := make(chan error, 1)
	asyncPush := func() { go func() { pushed <- r.push() }() }
	switch sc.injection {
	case "push":
		asyncPush() // may block on the activation row lock at B4; it lands after COMMIT
		w1.resume()
	case "kill":
		w1.signal(syscall.SIGKILL)
		pushed <- nil
	case "pushkill":
		// Async: at B4 the worker holds the row lock, so a synchronous push would deadlock the
		// harness against its own parked worker. The kill releases the lock and the push lands.
		asyncPush()
		time.Sleep(100 * time.Millisecond) // let the push reach the database before the kill
		w1.signal(syscall.SIGKILL)
	case "pause":
		if err := r.pausedTakeover(w1); err != nil {
			return err
		}
		pushed <- nil
	}
	if err := <-pushed; err != nil {
		return err
	}
	if sc.injection == "kill" || sc.injection == "pushkill" {
		if _, err := r.start("w2", "", false); err != nil { // a replacement process, as in production
			return err
		}
	}
	return r.quiesce(60 * time.Second)
}

// pausedTakeover is S5-4's setup: w1 stopped past its claim, w2 takes over and activates, w1 resumes.
func (r *run) pausedTakeover(w1 *proc) error {
	w1.signal(syscall.SIGSTOP)
	time.Sleep(r.claimTTL + 200*time.Millisecond)
	if err := r.reconcile(); err != nil { // the claim has expired: the reconciler re-enqueues
		return err
	}
	w2, err := r.start("w2", "", false)
	if err != nil {
		return err
	}
	if _, err := w2.await("EVENT activated", 30*time.Second); err != nil {
		return fmt.Errorf("takeover never activated: %w", err)
	}
	w1.signal(syscall.SIGCONT)
	w1.resume()
	line, err := w1.await("EVENT ", 30*time.Second) // the resumed worker's next protocol step
	for err == nil && !strings.Contains(line, "refused") && !strings.Contains(line, "activated") {
		line, err = w1.await("EVENT ", 30*time.Second)
	}
	return err
}

// reconcile is ReconcileSources for one repository: re-enqueue when the desired generation is ahead
// of the active one and nobody holds a live claim. It returns whether it enqueued.
func (r *run) reconcile() error {
	_, err := r.reconcileOnce()
	return err
}

func (r *run) reconcileOnce() (bool, error) {
	var behind, claimed bool
	err := r.pool.QueryRow(r.ctx, `
		SELECT r.desired_generation > g.desired_generation, coalesce(r.claim_expires_at > now(), false)
		  FROM repository r JOIN generation g ON g.id = r.active_generation_id WHERE r.id = 1`).Scan(&behind, &claimed)
	if err != nil || !behind || claimed {
		return false, err
	}
	_, err = r.inserter.Insert(r.ctx, IndexRepoArgs{RepoID: repoID}, nil)
	return err == nil, err
}

// quiesce waits until no job is outstanding on a live worker, no claim is live, and a reconciler
// pass finds nothing to do (ADR-0004: "workers drained, one reconciler pass, claim expiry elapsed").
// It never waits on River's stuck-job rescue: recovery must come from §9.3.3, not from the queue.
func (r *run) quiesce(limit time.Duration) error {
	deadline := time.Now().Add(limit)
	for time.Now().Before(deadline) {
		r.observe()
		var outstanding int
		var claimLive bool
		err := r.pool.QueryRow(r.ctx, `
			SELECT (SELECT count(*) FROM river_job WHERE kind = 'index_repo' AND (
			          state IN ('available','scheduled','retryable','pending')
			          OR (state = 'running' AND attempted_by[array_length(attempted_by, 1)] = ANY($1)))),
			       coalesce((SELECT claim_expires_at > now() FROM repository WHERE id = 1), false)`,
			r.liveIDs()).Scan(&outstanding, &claimLive)
		if err != nil {
			return err
		}
		if outstanding == 0 && !claimLive {
			enqueued, err := r.reconcileOnce()
			if err != nil {
				return err
			}
			if !enqueued {
				return nil
			}
		}
		time.Sleep(100 * time.Millisecond)
	}
	r.failures = append(r.failures, fmt.Sprintf("S5-1: not quiescent within %s", limit))
	return nil
}

// observe checks S5-3 continuously, at every quiescence poll.
func (r *run) observe() {
	var active int
	var matches bool
	if err := r.pool.QueryRow(r.ctx, `
		SELECT count(*), bool_and(g.id = r.active_generation_id)
		  FROM generation g JOIN repository r ON r.id = g.repo_id
		 WHERE g.repo_id = 1 AND g.status = 'active'`).Scan(&active, &matches); err != nil {
		r.errs = append(r.errs, err.Error())
		return
	}
	if active != 1 || !matches {
		r.failures = append(r.failures, fmt.Sprintf("S5-3: %d active generations (pointer matches: %v)", active, matches))
	}
}
