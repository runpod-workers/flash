package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type packRequest struct {
	ID     string          `json:"id"`
	Method string          `json:"method"`
	Input  json.RawMessage `json:"input"`
}

type packReply struct {
	ID     string          `json:"id"`
	Result json.RawMessage `json:"result"`
	Error  *packError      `json:"error"`
}

type packError struct {
	Type    string `json:"type"`
	Message string `json:"message"`
}

// newPackClient builds a dispatchFunc over an already-connected socket.
//
// Only one request may be in flight on the underlying connection at a time
// (the pack protocol is a single-connection request/reply stream), so the
// entire write+read critical section is serialized behind mu. Without this,
// concurrent HTTP requests hitting /invoke would interleave writes to conn
// and concurrently call ReadBytes on the shared bufio.Reader, corrupting
// framing and cross-wiring replies between unrelated callers.
func newPackClient(conn net.Conn) dispatchFunc {
	var (
		mu      sync.Mutex
		counter int64
	)
	reader := bufio.NewReader(conn)
	return func(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
		mu.Lock()
		defer mu.Unlock()

		id := strconv.FormatInt(atomic.AddInt64(&counter, 1), 10)
		req := packRequest{ID: id, Method: "invoke", Input: input}
		line, err := json.Marshal(req)
		if err != nil {
			return nil, err
		}

		// Honor ctx deadline on the socket I/O so a hung pack cannot block
		// forever. Clear the deadline afterward since the conn is reused
		// across sequential requests.
		if deadline, ok := ctx.Deadline(); ok {
			_ = conn.SetDeadline(deadline)
			defer conn.SetDeadline(time.Time{})
		}

		if _, err := conn.Write(append(line, '\n')); err != nil {
			return nil, err
		}

		// Read on a goroutine so we can also react to ctx cancellation
		// (e.g. cancel with no deadline) rather than only a fixed deadline.
		type readResult struct {
			line []byte
			err  error
		}
		resultCh := make(chan readResult, 1)
		go func() {
			replyLine, rerr := reader.ReadBytes('\n')
			resultCh <- readResult{line: replyLine, err: rerr}
		}()

		var replyLine []byte
		select {
		case res := <-resultCh:
			if res.err != nil {
				return nil, res.err
			}
			replyLine = res.line
		case <-ctx.Done():
			// Force the blocked read to unblock by closing the connection's
			// read side via a deadline in the past.
			_ = conn.SetDeadline(time.Now())
			<-resultCh
			return nil, fmt.Errorf("pack dispatch: %w", ctx.Err())
		}

		var reply packReply
		if err := json.Unmarshal(replyLine, &reply); err != nil {
			return nil, err
		}
		if reply.ID != id {
			return nil, fmt.Errorf("pack reply id mismatch: got %q want %q", reply.ID, id)
		}
		if reply.Error != nil {
			return nil, fmt.Errorf("%s: %s", reply.Error.Type, reply.Error.Message)
		}
		return reply.Result, nil
	}
}

// startPack spawns the pack subprocess, waits for it to connect, and returns
// a dispatchFunc plus a cleanup closer.
func startPack(ctx context.Context, packCmd []string) (dispatchFunc, func() error, error) {
	if len(packCmd) == 0 {
		return nil, nil, fmt.Errorf("packCmd is empty")
	}

	dir, err := os.MkdirTemp("", "flash-pack-")
	if err != nil {
		return nil, nil, err
	}
	socketPath := filepath.Join(dir, "pack.sock")

	ln, err := net.Listen("unix", socketPath)
	if err != nil {
		_ = os.RemoveAll(dir)
		return nil, nil, err
	}

	args := append(append([]string{}, packCmd[1:]...), "--socket", socketPath)
	var stderrBuf bytes.Buffer
	cmd := exec.CommandContext(ctx, packCmd[0], args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = io.MultiWriter(os.Stderr, &stderrBuf)
	if err := cmd.Start(); err != nil {
		_ = ln.Close()
		_ = os.RemoveAll(dir)
		return nil, nil, err
	}

	acceptCh := make(chan net.Conn, 1)
	go func() {
		conn, aerr := ln.Accept()
		if aerr == nil {
			acceptCh <- conn
		}
	}()

	waitCh := make(chan error, 1)
	go func() { waitCh <- cmd.Wait() }()

	drainAccept := func() {
		select {
		case c := <-acceptCh:
			_ = c.Close()
		default:
		}
	}

	select {
	case conn := <-acceptCh:
		_ = ln.Close()
		dispatch := newPackClient(conn)
		cleanup := func() error {
			_ = conn.Close()
			_ = cmd.Process.Kill()
			<-waitCh // reap the Wait goroutine
			return os.RemoveAll(dir)
		}
		return dispatch, cleanup, nil
	case werr := <-waitCh:
		_ = ln.Close()
		drainAccept()
		_ = os.RemoveAll(dir)
		tail := stderrBuf.String()
		if len(tail) > 500 {
			tail = tail[len(tail)-500:]
		}
		return nil, nil, fmt.Errorf("pack exited before connecting (%v): %s",
			werr, strings.TrimSpace(tail))
	case <-time.After(30 * time.Second):
		_ = ln.Close()
		drainAccept()
		_ = cmd.Process.Kill()
		<-waitCh
		_ = os.RemoveAll(dir)
		return nil, nil, fmt.Errorf("pack did not connect within 30s")
	}
}
