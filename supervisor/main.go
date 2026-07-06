package main

import (
	"context"
	"log"
	"os"
	"strings"
)

func main() {
	// FLASH_PACK_CMD: space-separated command that starts the language pack,
	// e.g. "python /opt/flash/pack/pack.py". The supervisor appends --socket.
	packCmdRaw := os.Getenv("FLASH_PACK_CMD")
	if packCmdRaw == "" {
		log.Fatal("FLASH_PACK_CMD not set")
	}
	packCmd := strings.Fields(packCmdRaw)

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
