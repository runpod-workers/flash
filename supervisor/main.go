package main

import (
	"context"
	"log"
	"os"
	"path/filepath"
)

func main() {
	// FLASH_PACK_DIR holds the extracted pack (default /opt/flash/pack). The
	// supervisor execs the pack's convention entrypoint `run` and appends
	// --socket; all language-specific launch logic lives in that script.
	packDir := os.Getenv("FLASH_PACK_DIR")
	if packDir == "" {
		packDir = "/opt/flash/pack"
	}
	packCmd := []string{filepath.Join(packDir, "run")}

	ctx := context.Background()
	dispatch, cleanup, err := startPack(ctx, packCmd)
	if err != nil {
		log.Fatalf("failed to start pack: %v", err)
	}
	defer func() { _ = cleanup() }()

	srv := newServer(dispatch)
	log.Printf("supervisor listening on %s", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("supervisor exited: %v", err)
	}
}
