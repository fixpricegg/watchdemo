package main

import (
	st "github.com/markus-wa/demoinfocs-golang/v5/pkg/demoinfocs/sendtables"
	"testing"
)

// Embedded interface supplies unused methods; pointer identity models SDK entities.
type entityStub struct {
	st.Entity
	marker int
}

func TestPruneReplacedEntities(t *testing.T) {
	old := &entityStub{marker: 1}
	current := &entityStub{marker: 2}
	tracked := map[int]st.Entity{401: old, 249: current, 500: old}
	created := map[int]int{401: 3304, 249: 3400, 500: 3200}
	live := map[int]st.Entity{401: &entityStub{marker: 3}, 249: current}
	pruneReplacedEntities(tracked, created, live)
	if len(tracked) != 1 || tracked[249] != current || len(created) != 1 || created[249] != 3400 {
		t.Fatalf("stale/replaced objects retained: tracked=%v created=%v", tracked, created)
	}
}
