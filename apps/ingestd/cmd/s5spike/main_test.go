package main

import (
	"io"
	"os"
	"strings"
	"testing"
)

// Review of #47: -runs 0 or a misspelled -scenario used to run nothing and still print
// "no failure in any run". Both must now fail before any database is touched.
func TestInvocationsThatRunNothingCannotPass(t *testing.T) {
	for _, args := range [][]string{
		{"-runs", "0"},
		{"-runs", "-3"},
		{"-scenario", "B9-bogus"},
		{"-scenario", "b2-pause"}, // names are exact, not case-folded
	} {
		out, err := captured(func() error { return runAll(args) })
		if err == nil {
			t.Errorf("%v: want an error, got none", args)
		}
		if strings.Contains(out, "no failure") || strings.Contains(out, "pass ") {
			t.Errorf("%v: printed a result without running: %q", args, out)
		}
	}
}

func captured(f func() error) (string, error) {
	r, w, _ := os.Pipe()
	stdout := os.Stdout
	os.Stdout = w
	err := f()
	w.Close()
	os.Stdout = stdout
	out, _ := io.ReadAll(r)
	return string(out), err
}
