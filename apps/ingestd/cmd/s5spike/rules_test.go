package main

import (
	"context"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Review of #46: every rule fails closed. Against a database that cannot be reached, each
// observation must land in r.errs (a run ERROR) and no rule may be judged, so nothing can PASS.
func TestRulesFailClosedWhenTheDatabaseCannotBeRead(t *testing.T) {
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, "postgres://nobody@127.0.0.1:1/none?connect_timeout=1")
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	r := &run{ctx: ctx, pool: pool, procs: map[string]*proc{
		"w1": {events: []string{"refused gen=2 token=t"}}, // S5-4's event checks pass; only the DB can fail it
	}}

	fails := r.checkRules(scenario{name: "B2-pause", barrier: "B2", injection: "pause"})

	for _, rule := range []string{"S5-1:", "S5-2:", "S5-4:", "S5-5:"} {
		found := false
		for _, e := range r.errs {
			found = found || strings.HasPrefix(e, rule)
		}
		if !found {
			t.Errorf("%s query error was not recorded as an error (errs %v)", rule, r.errs)
		}
	}
	if len(r.errs) < 5 { // the four above plus the final S5-3 observe()
		t.Errorf("want 5 observation errors, got %d: %v", len(r.errs), r.errs)
	}
	for _, f := range fails {
		if !strings.Contains(f, "S5-4: the resumed worker") { // event-based, not a DB read
			t.Errorf("a rule was judged on an unread database: %q", f)
		}
	}
}
