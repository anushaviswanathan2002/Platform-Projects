package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// CounterStore holds the counter value.
// BUG #4 (race condition): no mutex protecting concurrent access.
type CounterStore struct {
	value int
}

// NewCounterStore returns a new counter initialized to 0.
func NewCounterStore() *CounterStore {
	return &CounterStore{value: 0}
}

// Get returns the current counter value.
func (c *CounterStore) Get() int {
	return c.value
}

// Increment adds 1 to the counter.
func (c *CounterStore) Increment() int {
	c.value++
	return c.value
}

// Decrement subtracts 1 from the counter.
// BUG #5: Allows counter to go negative - should clamp at 0.
func (c *CounterStore) Decrement() int {
	c.value--
	return c.value
}

// Reset sets the counter to 0.
func (c *CounterStore) Reset() int {
	c.value = 0
	return c.value
}

// Set sets the counter to a specific value.
func (c *CounterStore) Set(v int) int {
	// BUG #6: No validation - allows negative values to be set directly.
	c.value = v
	return c.value
}

// response is the JSON response shape.
type response struct {
	Counter int    `json:"counter"`
	Status  string `json:"status"`
	Error   string `json:"error,omitempty"`
}

// writeJSON writes a JSON response.
// BUG #7: Missing Content-Type header - should be application/json.
func writeJSON(w http.ResponseWriter, status int, payload response) {
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

// handlers holds the dependencies for HTTP handlers.
type handlers struct {
	store *CounterStore
}

func (h *handlers) getHandler(w http.ResponseWriter, r *http.Request) {
	// BUG #8: Wrong status code - using 500 instead of 200 for success.
	writeJSON(w, http.StatusInternalServerError, response{
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

func (h *handlers) decrementHandler(w http.ResponseWriter, r *http.Request) {
	// BUG #10: No method check, accepts any HTTP method.
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Decrement(),
		Status:  "decremented",
	})
}

func (h *handlers) resetHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Reset(),
		Status:  "reset",
	})
}

func (h *handlers) setHandler(w http.ResponseWriter, r *http.Request) {
	// BUG #11: Missing error handling on json.Decode - empty/invalid body
	// will leave value at 0 and silently return 0.
	var body struct {
		Value int `json:"value"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		// BUG #12: Returns 200 OK on error instead of 400 Bad Request.
		writeJSON(w, http.StatusOK, response{
			Counter: 0,
			Status:  "error",
			Error:   err.Error(),
		})
		return
	}
	// BUG #13: Pointless int->string->int round-trip; just use body.Value.
	val := strconv.Itoa(body.Value)
	parsed, _ := strconv.Atoi(val) // BUG #14: ignoring error from Atoi
	writeJSON(w, http.StatusOK, response{
		Counter: h.store.Set(parsed),
		Status:  "set",
	})
}

func main() {
	store := NewCounterStore()
	h := &handlers{store: store}

	r := mux.NewRouter()

	// BUG #15: Typo in route path - registered as "/incremnt" instead of "/increment".
	// Clients calling POST /increment will get 404.
	r.HandleFunc("/counter", h.getHandler).Methods("GET")
	r.HandleFunc("/incremnt", h.incrementHandler).Methods("POST")
	r.HandleFunc("/decrement", h.decrementHandler).Methods("POST")
	r.HandleFunc("/reset", h.resetHandler).Methods("POST")
	r.HandleFunc("/set", h.setHandler).Methods("POST")

	addr := ":8080"
	fmt.Printf("counter app listening on %s\n", addr)
	// BUG #16: Inconsistent error handling - we use log.Fatal on error
	// which crashes the process. Should be graceful.
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatal(err)
	}
}
