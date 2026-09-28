package main

import (
	"context"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Review of #46: against an unreachable database every observation must land in r.errs (a run
// ERROR) and no rule may be judged on it, so nothing can PASS.
func TestRulesFailClosedWhenTheDatabaseCannotBeRead(t *testing.T) {
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, "postgres://nobody@127.0.0.1:1/none?connect_timeout=1")
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	// S5-4's event checks pass, so only a database read could fail it.
	r := &run{ctx: ctx, pool: pool, procs: map[string]*proc{"w1": {events: []string{"refused gen=2"}}}}
	fails := r.checkRules(scenario{name: "B2-pause", barrier: "B2", injection: "pause"})
	errs := strings.Join(r.errs, "\n")
	for _, rule := range []string{"S5-1:", "S5-2:", "S5-4:", "S5-5:"} {
		if !strings.Contains(errs, rule) {
			t.Errorf("%s query error was not recorded as an error:\n%s", rule, errs)
		}
	}
	if len(r.errs) != 5 || len(fails) != 0 { // the four above plus the final S5-3 observe()
		t.Errorf("want 5 errors and no judged rules, got %d errors, fails %v", len(r.errs), fails)
	}
}

// Review of #47: oneRun used to evaluate append(r.failures, r.checkRules(sc)...), which reads
// r.failures before checkRules' final observe() appends to it, and never read r.errs afterwards.
func TestTheVerdictIsTakenAfterTheFinalObservation(t *testing.T) {
	r := &run{}
	fails := []string{"S5-1: x"}
	r.failures = append(r.failures, "S5-3: added by the final observe")
	if got, err := verdict(r, fails); err != nil || len(got) != 2 {
		t.Errorf("want both failures, got %v, %v", got, err)
	}
	r.errs = append(r.errs, "S5-3: added by the final observe")
	if got, err := verdict(r, nil); err == nil {
		t.Errorf("an observation error became a result: %v", got)
	}
}
