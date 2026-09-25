package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/riverqueue/river"
	"github.com/riverqueue/river/riverdriver/riverpgxv5"
	"github.com/riverqueue/river/rivertype"
)

// barriers stops the worker at one named point, once, until the harness answers on stdin.
// Deterministic by construction: the harness acts while the worker is parked, never on a timer.
type barriers struct {
	target string
	once   sync.Once
	in     *bufio.Reader
}

func (b *barriers) hit(name string) {
	if b == nil || name != b.target {
		return
	}
	b.once.Do(func() {
		fmt.Fprintf(os.Stdout, "BARRIER %s\n", name)
		_, _ = b.in.ReadString('\n') // parked until the harness says continue
	})
}

// fastRetry keeps B5's retry within the run instead of River's default backoff.
type fastRetry struct{}

func (fastRetry) NextRetry(*rivertype.JobRow) time.Time {
	return time.Now().Add(100 * time.Millisecond)
}

func runWorker(args []string) error {
	fs := flag.NewFlagSet("worker", flag.ContinueOnError)
	dsn := fs.String("dsn", "", "database to work against")
	id := fs.String("id", "w1", "River client ID; running jobs record it as attempted_by")
	barrier := fs.String("barrier", "", "stop once at this barrier (B1..B5, B4')")
	failOnce := fs.Bool("fail-once", false, "first attempt of each job fails before claiming")
	claimTTL := fs.String("claim-ttl", "2 seconds", "claim lease as a Postgres interval")
	if err := fs.Parse(args); err != nil {
		return err
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, *dsn)
	if err != nil {
		return err
	}
	defer pool.Close()
	workers := river.NewWorkers()
	var b *barriers
	if *barrier != "" {
		b = &barriers{target: *barrier, in: bufio.NewReader(os.Stdin)}
	}
	river.AddWorker(workers, &indexWorker{pool: pool, barriers: b, claimTTL: *claimTTL, failOnce: *failOnce})
	client, err := river.NewClient(riverpgxv5.New(pool), &river.Config{
		ID:                *id,
		Queues:            map[string]river.QueueConfig{river.QueueDefault: {MaxWorkers: 1}},
		Workers:           workers,
		RetryPolicy:       fastRetry{},
		FetchPollInterval: 50 * time.Millisecond,
		FetchCooldown:     10 * time.Millisecond,
	})
	if err != nil {
		return err
	}
	if err := client.Start(ctx); err != nil {
		return err
	}
	fmt.Fprintln(os.Stdout, "READY")
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGTERM, syscall.SIGINT)
	<-stop
	sctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	return client.Stop(sctx)
}
