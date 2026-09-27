// Command s5spike is spike S5: ADR-0004's scheduling proof for DESIGN §9.3.3, run against River
// v0.47.0 (pinned in apps/ingestd/go.mod) and the pinned ParadeDB image.
//
//	s5spike worker ...   (one IndexRepo worker; the orchestrator that starts it lands next)
package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: s5spike worker [flags]")
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "worker":
		err = runWorker(os.Args[2:])
	default:
		err = fmt.Errorf("unknown command %q", os.Args[1])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "s5spike:", err)
		os.Exit(1)
	}
}
