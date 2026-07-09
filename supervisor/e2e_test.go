//go:build e2e

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestSupervisorEchoEndToEnd(t *testing.T) {
	packDir := os.Getenv("FLASH_ECHO_PACK_DIR")
	if packDir == "" {
		t.Skip("set FLASH_ECHO_PACK_DIR to the packs/python-echo directory")
	}
	// Accept whatever python3 the host has, so the seam test isn't gated on
	// the host having a 3.10-3.13 interpreter.
	verOut, err := exec.Command("python3", "-c",
		"import sys;print('%d.%d'%sys.version_info[:2])").Output()
	if err != nil {
		t.Skipf("no python3 on host: %v", err)
	}
	hostVer := strings.TrimSpace(string(verOut))
	os.Setenv("FLASH_SUPERVISOR_PORT", "8899")
	os.Setenv("FLASH_PACK_DIR", packDir)
	os.Setenv("FLASH_SUPPORTED_PYTHONS", hostVer)

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
	healthy := false
	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		resp, err := http.Get("http://127.0.0.1:8899/ping")
		if err == nil && resp.StatusCode == 200 {
			resp.Body.Close()
			healthy = true
			break
		}
		if resp != nil {
			resp.Body.Close()
		}
		time.Sleep(200 * time.Millisecond)
	}
	if !healthy {
		t.Fatalf("supervisor did not become healthy within 15s")
	}

	body := bytes.NewReader([]byte(`{"greeting":"hi"}`))
	resp, err := http.Post("http://127.0.0.1:8899/invoke", "application/json", body)
	if err != nil {
		t.Fatalf("invoke: %v", err)
	}
	defer resp.Body.Close()
	var out struct {
		Result map[string]string `json:"result"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&out)
	if out.Result["greeting"] != "hi" {
		t.Fatalf("result = %+v, want echo of greeting", out.Result)
	}
}
