package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestVersionFlagPrintsVersionAndSucceeds(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run([]string{"-version"}, &out, &errOut); code != 0 {
		t.Fatalf("exit %d, stderr %q", code, errOut.String())
	}
	if got := out.String(); got != "ingestd dev\n" {
		t.Fatalf("stdout %q", got)
	}
}

// A scaffold that exits 0 would pass a readiness check while ingesting nothing.
func TestRunningWithoutWorkFails(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run(nil, &out, &errOut); code == 0 {
		t.Fatal("ingestd exited 0 with nothing implemented")
	}
	if !strings.Contains(errOut.String(), "not implemented") {
		t.Fatalf("stderr %q", errOut.String())
	}
}

func TestUnknownFlagIsAUsageError(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run([]string{"-nope"}, &out, &errOut); code != 2 {
		t.Fatalf("exit %d", code)
	}
}
