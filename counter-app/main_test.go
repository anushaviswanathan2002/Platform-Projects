package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

// These tests are INTENTIONALLY written to fail until the bugs are fixed.
// Use them to verify your fixes: `go test ./...`

func TestCounterIncrement(t *testing.T) {
	c := NewCounterStore()
	if got := c.Increment(); got != 1 {
		t.Errorf("Increment() = %d, want 1", got)
	}
	if got := c.Increment(); got != 2 {
		t.Errorf("Increment() = %d, want 2", got)
	}
}

func TestCounterDecrementClampsAtZero(t *testing.T) {
	c := NewCounterStore()
	// BUG #5: Decrement goes negative. Should clamp at 0.
	if got := c.Decrement(); got != 0 {
		t.Errorf("Decrement() from 0 = %d, want 0 (clamped)", got)
	}
}

func TestCounterSetRejectsNegative(t *testing.T) {
	c := NewCounterStore()
	// BUG #6: Set should reject negative values.
	if got := c.Set(-5); got != 0 {
		t.Errorf("Set(-5) = %d, want 0 (rejected)", got)
	}
}

func TestCounterConcurrentSafety(t *testing.T) {
	// BUG #4: Race condition - use `go test -race` to detect.
	c := NewCounterStore()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c.Increment()
		}()
	}
	wg.Wait()
	if got := c.Get(); got != 100 {
		t.Errorf("after 100 concurrent increments, Get() = %d, want 100", got)
	}
}

func TestGetHandlerReturnsOK(t *testing.T) {
	h := &handlers{store: NewCounterStore()}
	req := httptest.NewRequest(http.MethodGet, "/counter", nil)
	rr := httptest.NewRecorder()
	h.getHandler(rr, req)

	// BUG #8: getHandler returns 500 instead of 200.
	if rr.Code != http.StatusOK {
		t.Errorf("GET /counter status = %d, want %d", rr.Code, http.StatusOK)
	}
}

func TestGetHandlerSetsContentType(t *testing.T) {
	h := &handlers{store: NewCounterStore()}
	req := httptest.NewRequest(http.MethodGet, "/counter", nil)
	rr := httptest.NewRecorder()
	h.getHandler(rr, req)

	// BUG #7: Content-Type header missing.
	if ct := rr.Header().Get("Content-Type"); !strings.Contains(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

func TestSetHandlerReturns400OnBadJSON(t *testing.T) {
	h := &handlers{store: NewCounterStore()}
	req := httptest.NewRequest(http.MethodPost, "/set", bytes.NewBufferString("{not-json"))
	rr := httptest.NewRecorder()
	h.setHandler(rr, req)

	// BUG #12: Returns 200 on bad JSON instead of 400.
	if rr.Code != http.StatusBadRequest {
		t.Errorf("POST /set with bad JSON status = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestSetHandlerSetsValue(t *testing.T) {
	h := &handlers{store: NewCounterStore()}
	body, _ := json.Marshal(map[string]int{"value": 42})
	req := httptest.NewRequest(http.MethodPost, "/set", bytes.NewReader(body))
	rr := httptest.NewRecorder()
	h.setHandler(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("POST /set status = %d, want %d", rr.Code, http.StatusOK)
	}
	var resp response
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if resp.Counter != 42 {
		t.Errorf("counter = %d, want 42", resp.Counter)
	}
}
