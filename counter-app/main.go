package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/gorilla/mux"
)

// CounterStore holds the counter value.
// FIX #4: Added a mutex to make concurrent access safe.
type CounterStore struct {
	mu    sync.Mutex
	value int
}

// NewCounterStore returns a new counter initialized to 0.
func NewCounterStore() *CounterStore {
	return &CounterStore{value: 0}
}

// Get returns the current counter value.
func (c *CounterStore) Get() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.value
}

// Increment adds 1 to the counter.
func (c *CounterStore) Increment() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.value++
	return c.value
}

// Decrement subtracts 1 from the counter.
// FIX #5: Counter is clamped at 0; it cannot go negative.
func (c *CounterStore) Decrement() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.value > 0 {
		c.value--
	}
	return c.value
}

// Set sets the counter to a specific value.
// FIX #6: Negative values are rejected and the current value is returned unchanged.
func (c *CounterStore) Set(v int) int {
	if v < 0 {
		return c.Get()
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.value = v
	return c.value
}

// Reset sets the counter to 0.
func (c *CounterStore) Reset() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.value = 0
	return c.value
}

// response is the JSON response shape.
type response struct {
	Counter int    `json:"counter"`
	Status  string `json:"status"`
	Error   string `json:"error,omitempty"`
}

// writeJSON writes a JSON response.
// FIX #7: Sets the Content-Type header to application/json.
func writeJSON(w http.ResponseWriter, status int, payload response) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

// handlers holds the dependencies for HTTP handlers.
type handlers struct {
	store *CounterStore
}

// FIX #8: Return 200 OK for a successful read.
func (h *handlers) getHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Get(),
		Status:  "ok",
	})
}

func (h *handlers) incrementHandler(w http.ResponseWriter, r *http.Request) {
	// Method check - only POST allowed.
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, response{
			Status: "error",
			Error:  "method not allowed",
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Increment(),
		Status:  "incremented",
	})
}

// FIX #10: Reject any HTTP method other than POST.
func (h *handlers) decrementHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, response{
			Status: "error",
			Error:  "method not allowed",
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Decrement(),
		Status:  "decremented",
	})
}

func (h *handlers) resetHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, response{
			Status: "error",
			Error:  "method not allowed",
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Reset(),
		Status:  "reset",
	})
}

func (h *handlers) setHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, response{
			Status: "error",
			Error:  "method not allowed",
		})
		return
	}
	var body struct {
		Value int `json:"value"`
	}
	// FIX #11/#12/#14: Return 400 on a decode failure with the error message
	// included in the response payload.
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, response{
			Counter: 0,
			Status:  "error",
			Error:   err.Error(),
		})
		return
	}
	// FIX #13: Use body.Value directly; no int->string->int round-trip.
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Set(body.Value),
		Status:  "set",
	})
}

func main() {
	store := NewCounterStore()
	h := &handlers{store: store}

	r := mux.NewRouter()

	// FIX #15: Correct route path is "/increment" (was "/incremnt").
	r.HandleFunc("/counter", h.getHandler).Methods("GET")
	r.HandleFunc("/increment", h.incrementHandler).Methods("POST")
	r.HandleFunc("/decrement", h.decrementHandler).Methods("POST")
	r.HandleFunc("/reset", h.resetHandler).Methods("POST")
	r.HandleFunc("/set", h.setHandler).Methods("POST")

	addr := ":8080"
	fmt.Printf("counter app listening on %s\n", addr)
	// FIX #16: Log the error and exit with a non-zero status instead of
	// crashing via log.Fatal.
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Printf("server error: %v", err)
		os.Exit(1)
	}
}
