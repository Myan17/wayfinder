// Command s5spike is spike S5: ADR-0004's scheduling proof for DESIGN §9.3.3, run against River
// v0.47.0 (pinned in apps/ingestd/go.mod) and the pinned ParadeDB image.
//
//	s5spike run -admin <dsn> -root <repo> [-runs 20] [-scenario B2-pause]
//	s5spike worker ...   (started by run; not for direct use)
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
	"github.com/riverqueue/river/riverdriver/riverpgxv5"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: s5spike run|worker [flags]")
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "worker":
		err = runWorker(os.Args[2:])
	case "run":
		err = runAll(os.Args[2:])
	default:
		err = fmt.Errorf("unknown command %q", os.Args[1])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "s5spike:", err)
		os.Exit(1)
	}
}

func runAll(args []string) error {
	fs := flag.NewFlagSet("run", flag.ContinueOnError)
	admin := fs.String("admin", "", "DSN of a role that may CREATE DATABASE")
	root := fs.String("root", ".", "repository root (for db/migrations)")
	runs := fs.Int("runs", 20, "runs per scenario (ADR-0004: 20)")
	only := fs.String("scenario", "", "run one scenario by name")
	if err := fs.Parse(args); err != nil {
		return err
	}
	type tally struct{ pass, fail, errored int }
	results := map[string]*tally{}
	failures := map[string][]string{}
	var took []time.Duration
	for _, sc := range scenarios() {
		if *only != "" && sc.name != *only {
			continue
		}
		t := &tally{}
		results[sc.name] = t
		for i := 1; i <= *runs; i++ {
			start := time.Now()
			fails, err := oneRun(*admin, *root, sc, i)
			took = append(took, time.Since(start))
			switch {
			case err != nil:
				t.errored++
				failures[sc.name] = append(failures[sc.name], fmt.Sprintf("run %d ERROR: %v", i, err))
			case len(fails) > 0:
				t.fail++
				failures[sc.name] = append(failures[sc.name], fmt.Sprintf("run %d FAIL: %s", i, strings.Join(fails, "; ")))
			default:
				t.pass++
			}
		}
		fmt.Printf("%-12s pass %2d  fail %2d  error %2d\n", sc.name, t.pass, t.fail, t.errored)
	}
	names := make([]string, 0, len(failures))
	for n := range failures {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		for _, f := range failures[n] {
			fmt.Printf("  %s %s\n", n, f)
		}
	}
	sort.Slice(took, func(i, j int) bool { return took[i] < took[j] })
	if len(took) > 0 {
		fmt.Printf("run time (not judged, ADR-0004): median %s, max %s over %d runs\n",
			took[len(took)/2].Round(time.Millisecond), took[len(took)-1].Round(time.Millisecond), len(took))
	}
	total := 0
	for _, t := range results {
		total += t.fail + t.errored
	}
	if total > 0 {
		return fmt.Errorf("%d runs failed or errored; ADR-0004 allows none", total)
	}
	fmt.Println("S5-1..S5-5: no failure in any run of any scenario")
	return nil
}

// oneRun returns the rule failures observed, or an error if the run itself could not be carried out.
func oneRun(admin, root string, sc scenario, i int) ([]string, error) {
	ctx := context.Background()
	dsn, err := freshDatabase(ctx, admin, fmt.Sprintf("s5_run_%d", i), root)
	if err != nil {
		return nil, fmt.Errorf("fresh database: %w", err)
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	defer pool.Close()
	inserter, err := river.NewClient(riverpgxv5.New(pool), &river.Config{}) // insert-only
	if err != nil {
		return nil, err
	}
	r := &run{ctx: ctx, dsn: dsn, pool: pool, inserter: inserter, procs: map[string]*proc{}, claimTTL: 1500 * time.Millisecond}
	defer r.stopAll()
	if err := r.seed(); err != nil {
		return nil, fmt.Errorf("seed: %w", err)
	}
	if err := r.preconditions(); err != nil {
		return nil, err // ADR-0004: a precondition failure is an error, never a result
	}
	if err := r.push(); err != nil { // the initial push: the scenario begins here
		return nil, err
	}
	if err := r.execute(sc); err != nil {
		return nil, err
	}
	if len(r.errs) > 0 {
		return nil, fmt.Errorf("%s", strings.Join(r.errs, "; "))
	}
	return append(r.failures, r.checkRules(sc)...), nil
}
