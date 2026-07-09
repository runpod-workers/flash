package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

// fakePack accepts one connection and echoes {"id","result":input} per line.
func fakePack(t *testing.T, socketPath string, ready chan<- struct{}) {
	ln, err := net.Listen("unix", socketPath)
	if err != nil {
		t.Errorf("listen: %v", err)
		return
	}
	defer ln.Close()
	close(ready)
	conn, err := ln.Accept()
	if err != nil {
		return
	}
	defer conn.Close()
	dec := json.NewDecoder(conn)
	for {
		var req map[string]json.RawMessage
		if err := dec.Decode(&req); err != nil {
			return
		}
		reply := map[string]json.RawMessage{"id": req["id"], "result": req["input"]}
		_ = json.NewEncoder(conn).Encode(reply)
	}
}

func TestStartPackSurfacesEarlyExit(t *testing.T) {
	// A "pack" that prints to stderr and exits 3 without ever connecting.
	start := time.Now()
	_, _, err := startPack(context.Background(),
		[]string{"sh", "-c", "echo boom-msg >&2; exit 3"})
	elapsed := time.Since(start)
	if err == nil {
		t.Fatal("expected error when pack exits before connecting, got nil")
	}
	if elapsed > 10*time.Second {
		t.Fatalf("startPack took %v; should surface early exit promptly, not wait 30s", elapsed)
	}
	if !strings.Contains(err.Error(), "exited before connecting") {
		t.Fatalf("error = %q, want it to mention early exit", err.Error())
	}
	if !strings.Contains(err.Error(), "boom-msg") {
		t.Fatalf("error = %q, want it to include the pack's stderr", err.Error())
	}
}

func TestDispatchRoundTrips(t *testing.T) {
	dir := t.TempDir()
	socketPath := filepath.Join(dir, "pack.sock")
	ready := make(chan struct{})
	go fakePack(t, socketPath, ready)
	<-ready

	conn, err := net.Dial("unix", socketPath)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	d := newPackClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	out, err := d(ctx, json.RawMessage(`{"hello":"world"}`))
	if err != nil {
		t.Fatalf("dispatch err: %v", err)
	}
	if string(out) != `{"hello":"world"}` {
		t.Fatalf("dispatch out = %s, want echo", out)
	}
	_ = os.Remove(socketPath)
}

// silentPack accepts one connection and never replies.
func silentPack(t *testing.T, socketPath string, ready chan<- struct{}, done <-chan struct{}) {
	ln, err := net.Listen("unix", socketPath)
	if err != nil {
		t.Errorf("listen: %v", err)
		close(ready)
		return
	}
	defer ln.Close()
	close(ready)
	conn, err := ln.Accept()
	if err != nil {
		return
	}
	defer conn.Close()
	<-done
}

func TestDispatchHonorsCtxTimeout(t *testing.T) {
	testDone := make(chan struct{})
	defer close(testDone)

	resultCh := make(chan error, 1)
	go func() {
		dir := t.TempDir()
		socketPath := filepath.Join(dir, "pack.sock")
		ready := make(chan struct{})
		packDone := make(chan struct{})
		defer close(packDone)
		go silentPack(t, socketPath, ready, packDone)
		<-ready

		conn, err := net.Dial("unix", socketPath)
		if err != nil {
			resultCh <- err
			return
		}
		defer conn.Close()

		d := newPackClient(conn)
		ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
		defer cancel()

		_, err = d(ctx, json.RawMessage(`{"hello":"world"}`))
		resultCh <- err
	}()

	select {
	case err := <-resultCh:
		if err == nil {
			t.Fatalf("dispatch err = nil, want non-nil error on ctx timeout")
		}
	case <-time.After(1 * time.Second):
		t.Fatalf("dispatch did not return within 1s of ctx timeout (blocked forever)")
	}
}

// mismatchPack accepts one connection and always replies with a fixed wrong id.
func mismatchPack(t *testing.T, socketPath string, ready chan<- struct{}) {
	ln, err := net.Listen("unix", socketPath)
	if err != nil {
		t.Errorf("listen: %v", err)
		close(ready)
		return
	}
	defer ln.Close()
	close(ready)
	conn, err := ln.Accept()
	if err != nil {
		return
	}
	defer conn.Close()
	dec := json.NewDecoder(conn)
	for {
		var req map[string]json.RawMessage
		if err := dec.Decode(&req); err != nil {
			return
		}
		reply := map[string]json.RawMessage{
			"id":     json.RawMessage(`"wrong-id"`),
			"result": req["input"],
		}
		_ = json.NewEncoder(conn).Encode(reply)
	}
}

func TestDispatchRejectsReplyIDMismatch(t *testing.T) {
	dir, err := os.MkdirTemp("", "pack-mismatch-")
	if err != nil {
		t.Fatalf("mkdirtemp: %v", err)
	}
	defer os.RemoveAll(dir)
	socketPath := filepath.Join(dir, "pack.sock")
	ready := make(chan struct{})
	go mismatchPack(t, socketPath, ready)
	<-ready

	conn, err := net.Dial("unix", socketPath)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	d := newPackClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	_, err = d(ctx, json.RawMessage(`{"hello":"world"}`))
	if err == nil {
		t.Fatalf("dispatch err = nil, want mismatch error")
	}
	if !strings.Contains(err.Error(), "mismatch") {
		t.Fatalf("dispatch err = %v, want error mentioning mismatch", err)
	}
}

// TestDispatchConcurrentSafe fires many concurrent dispatch() calls over a
// single pack connection, the same access pattern net/http uses when
// concurrent HTTP requests each call dispatch() directly from their own
// per-request goroutine. Without serializing the write+read critical section
// in newPackClient, concurrent writes to conn and concurrent ReadBytes calls
// on the shared bufio.Reader would race and cross-wire replies between
// unrelated callers. Run with -race to validate the fix.
func TestDispatchConcurrentSafe(t *testing.T) {
	dir := t.TempDir()
	socketPath := filepath.Join(dir, "pack.sock")
	ready := make(chan struct{})
	go fakePack(t, socketPath, ready)
	<-ready

	conn, err := net.Dial("unix", socketPath)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	d := newPackClient(conn)

	const numCalls = 50
	var wg sync.WaitGroup
	errs := make([]error, numCalls)
	outs := make([]string, numCalls)
	for i := 0; i < numCalls; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			input := json.RawMessage(fmt.Sprintf(`{"n":%d}`, i))
			out, err := d(ctx, input)
			errs[i] = err
			if err == nil {
				outs[i] = string(out)
			}
		}(i)
	}
	wg.Wait()

	for i := 0; i < numCalls; i++ {
		if errs[i] != nil {
			t.Fatalf("call %d: dispatch err = %v, want nil", i, errs[i])
		}
		want := fmt.Sprintf(`{"n":%d}`, i)
		if outs[i] != want {
			t.Fatalf("call %d: dispatch out = %s, want %s (cross-wired reply)", i, outs[i], want)
		}
	}
}
