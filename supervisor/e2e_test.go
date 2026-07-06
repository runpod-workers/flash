//go:build e2e

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"os/exec"
	"syscall"
	"testing"
	"time"
)

func TestSupervisorEchoEndToEnd(t *testing.T) {
	packPath := os.Getenv("FLASH_ECHO_PACK_PATH")
	if packPath == "" {
		t.Skip("set FLASH_ECHO_PACK_PATH to packs/python-echo/pack.py")
	}
	os.Setenv("FLASH_SUPERVISOR_PORT", "8899")
	// python3, not python: this machine only has python3 on PATH.
	os.Setenv("FLASH_PACK_CMD", "python3 "+packPath)

	// Build the supervisor binary directly rather than "go run .": "go run"
	// spawns a compiled binary as a grandchild, and that grandchild in turn
	// spawns the pack subprocess. Killing only the "go run" pid leaves both
	// grandchildren alive holding the inherited stdout/stderr fds open,
	// which makes `go test` hang for up to 60s waiting for I/O to finish.
	binDir := t.TempDir()
	binPath := binDir + "/supervisor"
	build := exec.Command("go", "build", "-o", binPath, ".")
	build.Stdout = os.Stdout
	build.Stderr = os.Stderr
	if err := build.Run(); err != nil {
		t.Fatalf("build supervisor: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	cmd := exec.CommandContext(ctx, binPath)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// New process group so cleanup can kill the supervisor AND the pack
	// subprocess it spawns, instead of leaving the pack orphaned.
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	if err := cmd.Start(); err != nil {
		t.Fatalf("start supervisor: %v", err)
	}
	defer func() { _ = syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL) }()

	// Wait for /ping.
	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		resp, err := http.Get("http://127.0.0.1:8899/ping")
		if err == nil && resp.StatusCode == 200 {
			break
		}
		time.Sleep(200 * time.Millisecond)
	}

	body := bytes.NewReader([]byte(`{"greeting":"hi"}`))
	resp, err := http.Post("http://127.0.0.1:8899/invoke", "application/json", body)
	if err != nil {
		t.Fatalf("invoke: %v", err)
	}
	var out struct {
		Result map[string]string `json:"result"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&out)
	if out.Result["greeting"] != "hi" {
		t.Fatalf("result = %+v, want echo of greeting", out.Result)
	}
}
