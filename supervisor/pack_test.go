package main

import (
	"context"
	"encoding/json"
	"net"
	"os"
	"path/filepath"
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
