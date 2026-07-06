package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
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
// Sequential request/reply (one in flight); sufficient for the skeleton.
func newPackClient(conn net.Conn) dispatchFunc {
	var counter int64
	reader := bufio.NewReader(conn)
	return func(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
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
	cmd := exec.CommandContext(ctx, packCmd[0], args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
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

	select {
	case conn := <-acceptCh:
		_ = ln.Close()
		dispatch := newPackClient(conn)
		cleanup := func() error {
			_ = conn.Close()
			_ = cmd.Process.Kill()
			_ = cmd.Wait()
			return os.RemoveAll(dir)
		}
		return dispatch, cleanup, nil
	case <-time.After(30 * time.Second):
		_ = ln.Close()
		// Drain a conn that may have raced in right as the listener closed,
		// so we don't leak its fd.
		select {
		case conn := <-acceptCh:
			_ = conn.Close()
		default:
		}
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		_ = os.RemoveAll(dir)
		return nil, nil, fmt.Errorf("pack did not connect within 30s")
	}
}
