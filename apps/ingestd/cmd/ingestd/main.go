// Command ingestd is Wayfinder's write path (DESIGN §8.2): webhooks, ingestion, chunking, embedding,
// generation builds and GC.
//
// Today it is a scaffold. It reports its version and refuses to run, because a process that starts
// and does nothing looks healthy to a readiness check while ingesting nothing. The packages under
// internal/ arrive with their modules' Phase 1 work (docs/team/OWNERSHIP.md).
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
)

// version is set at build time: go build -ldflags "-X main.version=<commit>".
var version = "dev"

func run(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("ingestd", flag.ContinueOnError)
	fs.SetOutput(stderr)
	showVersion := fs.Bool("version", false, "print the version and exit")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *showVersion {
		fmt.Fprintf(stdout, "ingestd %s\n", version)
		return 0
	}
	fmt.Fprintln(stderr, "ingestd: not implemented yet; the write path lands in Phase 1")
	return 1
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
