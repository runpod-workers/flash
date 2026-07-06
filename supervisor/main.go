package main

import (
	"context"
	"encoding/json"
	"log"
)

func main() {
	// Placeholder dispatch; replaced by the pack client in Task 3.
	dispatch := func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
		return in, nil
	}
	srv := newServer(dispatch)
	log.Printf("supervisor listening on %s", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("supervisor exited: %v", err)
	}
}
