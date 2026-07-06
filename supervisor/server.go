package main

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
)

type dispatchFunc func(ctx context.Context, input json.RawMessage) (json.RawMessage, error)

func newServer(dispatch dispatchFunc) *http.Server {
	mux := http.NewServeMux()

	mux.HandleFunc("/ping", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	})

	mux.HandleFunc("/invoke", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, "read_error", err.Error())
			return
		}
		result, err := dispatch(r.Context(), body)
		if err != nil {
			writeError(w, "dispatch_error", err.Error())
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		payload, _ := json.Marshal(map[string]json.RawMessage{"result": result})
		_, _ = w.Write(payload)
	})

	port := os.Getenv("FLASH_SUPERVISOR_PORT")
	if port == "" {
		port = "80"
	}
	return &http.Server{Addr: ":" + port, Handler: mux}
}

func writeError(w http.ResponseWriter, typ, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusInternalServerError)
	payload, _ := json.Marshal(map[string]map[string]string{
		"error": {"type": typ, "message": msg},
	})
	_, _ = w.Write(payload)
}
