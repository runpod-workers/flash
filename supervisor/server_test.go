package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestPingReturnsHealthy(t *testing.T) {
	srv := newServer(func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
		return json.RawMessage(`null`), nil
	})
	req := httptest.NewRequest(http.MethodGet, "/ping", nil)
	rec := httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("ping status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"status":"healthy"`) {
		t.Fatalf("ping body = %q, want healthy", rec.Body.String())
	}
}

func TestInvokeReturnsDispatchResult(t *testing.T) {
	srv := newServer(func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
		return json.RawMessage(`{"echoed":true}`), nil
	})
	req := httptest.NewRequest(http.MethodPost, "/invoke", strings.NewReader(`{"x":1}`))
	rec := httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("invoke status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"echoed":true`) {
		t.Fatalf("invoke body = %q, want dispatch result", rec.Body.String())
	}
}

func TestWrongMethodReturns405(t *testing.T) {
	srv := newServer(func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
		return json.RawMessage(`null`), nil
	})

	req := httptest.NewRequest(http.MethodPost, "/ping", nil)
	rec := httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("POST /ping status = %d, want 405", rec.Code)
	}

	req = httptest.NewRequest(http.MethodGet, "/invoke", nil)
	rec = httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("GET /invoke status = %d, want 405", rec.Code)
	}
}

func TestInvokeInvalidResultReturnsError(t *testing.T) {
	srv := newServer(func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
		return json.RawMessage(`{not valid json`), nil
	})
	req := httptest.NewRequest(http.MethodPost, "/invoke", strings.NewReader(`{"x":1}`))
	rec := httptest.NewRecorder()
	srv.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("invoke status = %d, want 500", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"error"`) {
		t.Fatalf("invoke body = %q, want error shape", rec.Body.String())
	}
}
