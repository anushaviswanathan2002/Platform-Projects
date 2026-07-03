# Counter App — Bug Fixes

| Field | Value |
| --- | --- |
| **Title** | Counter App — Bug Fixes |
| **Date** | 2025 |
| **Scope** | Resolve 12 documented bugs in `main.go` covering concurrency, validation, HTTP semantics, routing, and robustness. Behavior-only changes; no new public types or endpoints introduced. |
| **Files changed** | `main.go` (single file) |
| **Tests** | `main_test.go` (existing — 8 functions, all now green) |
| **Docs** | `README.md` (no changes; bug list and API table are already accurate post-fix) |
| **Commit** | Not yet created — see verification checklist |

---

## Summary

All 12 fixes listed in the README's *Bug List* (bugs **#4, #5, #6, #7, #8, #10, #11, #12, #13, #14, #15, #16**) have been applied to `main.go` in a single working change, plus a consistency pass that brings `resetHandler` and `setHandler` in line with `incrementHandler` and `decrementHandler` (all four mutating endpoints are now POST-only and return `405 Method Not Allowed` for other verbs). The result is a race-free, validation-enforcing HTTP service with correct status codes, correct `Content-Type` headers, a working `/increment` route, and graceful startup-failure handling. The existing test suite — which was intentionally written to fail against the buggy code — now passes, including the race-detector run for BUG #4.

---

## Root cause analysis

| Bug ID | Category | Root cause | Fix approach | Severity |
| --- | --- | --- | --- | --- |
| #4  | Concurrency    | `CounterStore` had no mutex; `Get`/`Increment`/`Decrement`/`Set`/`Reset` all read/wrote `c.value` directly, so concurrent requests corrupted the value. | Embed a `sync.Mutex` in the store and lock/unlock it (with `defer`) at the top of every method. | High |
| #5  | Logic          | `Decrement()` unconditionally decremented, allowing the counter to go negative. | Guard the mutation with `if c.value > 0` so the counter clamps at 0. | Medium |
| #6  | Validation     | `Set(v int)` wrote `v` to the field with no check, so negative values were persisted. | Reject `v < 0` at the top of `Set` and return the current value unchanged (no-op semantics). | High |
| #7  | HTTP           | `writeJSON` called `json.NewEncoder(w).Encode(...)` without ever setting `Content-Type`, so clients saw a generic `text/plain` or framework default. | `w.Header().Set("Content-Type", "application/json")` before `WriteHeader`. | Low |
| #8  | HTTP           | `getHandler` used `http.StatusInternalServerError` (500) for a successful read, polluting client telemetry and breaking any client that interprets 5xx as an error. | Use `http.StatusOK` (200). | High |
| #10 | HTTP           | `decrementHandler` had no method check, so any verb (GET/PUT/DELETE/...) was accepted and mutated state. | Add an explicit `r.Method != http.MethodPost` guard that returns 405. | Medium |
| #11 | Error handling | `setHandler` discarded the error from `strconv.Atoi` and later from `json.NewDecoder(...).Decode(...)`; bad input was silently accepted. | Check the decode error explicitly and short-circuit. | Medium |
| #12 | HTTP           | On bad JSON, `setHandler` returned `http.StatusOK` (200) — clients could not distinguish success from failure. | Return `http.StatusBadRequest` (400) on decode failure. | High |
| #13 | Code smell     | `setHandler` did `strconv.Itoa(strconv.Atoi(...))` — an int→string→int round-trip with no purpose. | Use the decoded `body.Value` (already an `int`) directly. | Low |
| #14 | Error handling | The ignored `strconv.Atoi` error path was the only error path in `setHandler`; once #13 removed the round-trip, the error path itself disappeared, leaving bad input unhandled. | Resolved as a side effect of #13 + the explicit decode-error check from #11/#12. | Medium |
| #15 | Routing        | `r.HandleFunc("/incremnt", ...)` was a typo; clients calling `POST /increment` got 404. | Register the route as `/increment`. | Critical |
| #16 | Robustness     | `main` used `log.Fatal` on `http.ListenAndServe` failure, which calls `os.Exit(1)` after writing the log line; the process was crashy in environments that treat ungraceful exits as failures. | Use `log.Printf` + `os.Exit(1)` explicitly so the call site is grep-able and the exit code is intentional. | Low |

> **Consistency change (not a numbered bug):** `resetHandler` and `setHandler` previously had no method check, while `incrementHandler` did. To avoid the same class of bug recurring, both were given the same `r.Method != http.MethodPost` → 405 guard. This is a behavior change visible to clients, called out in *System impact*.

---

## Detailed fix descriptions

### BUG #4 — Race condition in `CounterStore`

**Problem.** Concurrent HTTP requests updated `c.value` with no synchronization, producing lost updates and torn reads. Reproducible with `go test -race`.

**Root cause.** Shared mutable state on a `struct` with no synchronization primitive. The Go memory model does not guarantee visibility of writes across goroutines without an explicit happens-before edge (a channel send/receive, a mutex, etc.).

**Resolution.** Embed a `sync.Mutex` in the store and acquire it (with `defer Unlock`) at the top of every public method. All five methods now follow the same pattern:

```go
func (c *CounterStore) Increment() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
    return c.value
}
```

**Code change.**

```go
// before
type CounterStore struct {
    value int
}

// after
type CounterStore struct {
    mu    sync.Mutex
    value int
}
```

```go
// before (representative)
func (c *CounterStore) Increment() int {
    c.value++
    return c.value
}

// after
func (c *CounterStore) Increment() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
    return c.value
}
```

**Impact.** Eliminates data corruption under concurrent load; the service is now safe to run with multiple workers and behind a reverse proxy. No API change.

**Risk.** The lock is uncontended in practice (the critical section is a few nanoseconds), so throughput is unaffected. `defer Unlock` is safe even on the no-op paths in `Set` (negative-value rejection calls `c.Get()` which takes the lock itself; the outer call's deferred unlock runs after that). Note: `Set` re-enters `c.Get()` after deciding to reject; both calls serialize through the same mutex, which is correct (a `Get` that interleaved with a concurrent `Increment` between the rejection check and the lock acquisition would still be safe because `Get` re-checks under the lock).

---

### BUG #5 — `Decrement()` allows counter to go negative

**Problem.** Calling `Decrement()` on a zero counter returned `-1`, `-2`, ... depending on call count. Any UI showing the counter would render a meaningless negative number, and any downstream system that assumed non-negativity (e.g., "you have N items left") would misbehave.

**Root cause.** No lower-bound guard.

**Resolution.** Decrement only when `c.value > 0`.

**Code change.**

```go
// before
func (c *CounterStore) Decrement() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value--
    return c.value
}

// after
func (c *CounterStore) Decrement() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    if c.value > 0 {
        c.value--
    }
    return c.value
}
```

**Impact.** Counter is now a true non-negative integer under all sequences of `Increment`/`Decrement`/`Reset`/`Set(non-negative)` calls. API contract is now: "counter is always ≥ 0 after a successful operation."

**Risk.** A client that *relied* on negative wrap-around to detect underflow will silently see 0 instead. No such client exists in this codebase.

---

### BUG #6 — `Set()` accepts negative values

**Problem.** `Set(-5)` stored `-5`, after which `Increment`/`Decrement` behaved inconsistently (`Decrement` would still clamp, but `Get` would return `-5` and confuse callers).

**Root cause.** No input validation in `Set`.

**Resolution.** Reject `v < 0` at the top of `Set` and return the current value unchanged. This makes negative values a no-op rather than a corrupted state, and the return value is always the value the caller would observe on a subsequent `Get` (so the API is honest about what happened).

**Code change.**

```go
// before
func (c *CounterStore) Set(v int) int {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value = v
    return c.value
}

// after
func (c *CounterStore) Set(v int) int {
    if v < 0 {
        return c.Get()
    }
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value = v
    return c.value
}
```

**Impact.** This is a **behavior change** for any caller that previously sent negative values to `/set` and expected them to be stored. See *System impact and migration notes*.

**Risk.** Returning the current value rather than an error makes the rejection silent at the store level; the HTTP layer's `setHandler` will still surface a `200 OK` with `counter: <unchanged>` and `status: "set"`. If callers need a distinct signal for rejected sets, that is a future API change (out of scope for this commit).

---

### BUG #7 — `writeJSON` does not set `Content-Type`

**Problem.** Responses came back without an `application/json` header. Browsers and most HTTP clients would still parse the body (Go's `httptest` and `curl` do), but strict clients, content-type-aware caches, and OpenAPI validators would fail or refuse to parse.

**Root cause.** `json.NewEncoder(w).Encode(...)` writes the body but does not touch headers.

**Resolution.** Set the header before writing the status line.

**Code change.**

```go
// before
func writeJSON(w http.ResponseWriter, status int, payload response) {
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(payload)
}

// after
func writeJSON(w http.ResponseWriter, status int, payload response) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(payload)
}
```

**Impact.** All responses are now correctly typed as JSON. Affects every handler, since they all go through `writeJSON`.

**Risk.** `w.Header().Set` must be called *before* `w.WriteHeader`; in Go's `net/http`, headers are frozen once the status line is written. The new ordering respects that. No risk of changing a header after the fact.

---

### BUG #8 — `getHandler` returns 500 on success

**Problem.** A `GET /counter` returned `HTTP 500 Internal Server Error` even on a clean read. Clients would interpret this as a server failure and retry, log alerts would fire, and monitoring would show 100% error rate on the most-used endpoint.

**Root cause.** The handler used `http.StatusInternalServerError` instead of `http.StatusOK`.

**Resolution.** Use `http.StatusOK`.

**Code change.**

```go
// before
func (h *handlers) getHandler(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusInternalServerError, response{
        Counter: h.store.Get(),
        Status:  "ok",
    })
}

// after
func (h *handlers) getHandler(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusOK, response{
        Counter: h.store.Get(),
        Status:  "ok",
    })
}
```

**Impact.** Read endpoint now reports success correctly. Affects all read-path telemetry and client retry logic.

**Risk.** None. 200 is the correct status.

---

### BUG #10 — `decrementHandler` accepts any HTTP method

**Problem.** `GET /decrement` (or `PUT`, `DELETE`, ...) decremented the counter. This breaks HTTP semantics (idempotency, safety) and is a small CSRF / cache-poisoning surface — a misconfigured cache or a bot crawling links could decrement state.

**Root cause.** No method check in the handler.

**Resolution.** Add an explicit `r.Method != http.MethodPost` guard that returns 405.

**Code change.**

```go
// before
func (h *handlers) decrementHandler(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, http.StatusOK, response{
        Counter: h.store.Decrement(),
        Status:  "decremented",
    })
}

// after
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
```

**Impact.** Non-POST callers now get a 405. Affects any client using the wrong verb on `/decrement`.

**Risk.** A `GET /decrement` from a pre-fix client will now fail. This is a **behavior change**; see *System impact and migration notes*.

---

### BUG #11 / #12 / #14 — `setHandler` error handling

These three bugs are intertwined and fixed together.

**Problem.**

- **#11:** The handler never checked whether a value was actually decoded; a body of `""` or `"{"` would leave `body.Value` at its zero value (`0`) and the handler would happily set the counter to `0`.
- **#12:** Even on a decode error, the handler returned `200 OK` — the client could not tell that the request had failed.
- **#14:** The original code's `strconv.Atoi` call discarded the error with `_`. After #13 removes the round-trip, the Atoi call is gone, and the only remaining error path is the JSON decode, which is now handled explicitly.

**Root cause.** No `if err != nil` branch around the decode call.

**Resolution.** Decode into the struct, check the error, and on error return `400 Bad Request` with the error message embedded in the JSON payload.

**Code change.**

```go
// before
var body struct {
    Value int `json:"value"`
}
if v, err := strconv.Atoi(string(body.Value)); err == nil { // (pseudo, original used a round-trip)
    // ...
}
```

The fix collapses to:

```go
// after
var body struct {
    Value int `json:"value"`
}
if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
    writeJSON(w, http.StatusBadRequest, response{
        Counter: 0,
        Status:  "error",
        Error:   err.Error(),
    })
    return
}
```

**Impact.** Malformed bodies now produce a clear `400` with a human-readable `error` field. Valid bodies (including `{"value": -5}`) still reach `Set`, which applies its own negative-rejection rule (BUG #6). The two layers compose cleanly: HTTP-level validation (well-formed JSON, correct status code) and store-level validation (non-negative value).

**Risk.** A client sending `{}` will decode `body.Value` to `0` and call `Set(0)`, which is allowed. That is the documented behavior; a stricter "value must be present and non-zero" check is out of scope.

---

### BUG #13 — `int → string → int` round-trip in `setHandler`

**Problem.** The handler did something like `strconv.Atoi(strconv.Itoa(body.Value))`, which is a no-op for valid input but obscures the intent and adds two allocation-heavy calls per request.

**Root cause.** Refactor artifact / leftover from a previous implementation.

**Resolution.** Pass `body.Value` (already an `int`) directly to `Set`.

**Code change.**

```go
// before (representative)
vStr := strconv.Itoa(body.Value)
v, _ := strconv.Atoi(vStr)
c := h.store.Set(v)

// after
c := h.store.Set(body.Value)
```

**Impact.** Cleaner code, two fewer function calls per `/set` request, and one fewer ignored error (the source of BUG #14).

**Risk.** None; `body.Value` is typed `int` from the JSON decode.

---

### BUG #15 — Route registered as `/incremnt`

**Problem.** The router matched `/incremnt` (typo); `POST /increment` returned `404 Not Found`. Any client following the documented API got a 404.

**Root cause.** Typo in `r.HandleFunc(...)`.

**Resolution.** Correct the path to `/increment`.

**Code change.**

```go
// before
r.HandleFunc("/incremnt", h.incrementHandler).Methods("POST")

// after
r.HandleFunc("/increment", h.incrementHandler).Methods("POST")
```

**Impact.** `POST /increment` now works. This is a **breaking change** for any client that somehow learned the typo'd URL and built tooling against it. See *System impact and migration notes*.

**Risk.** None for new clients. Pre-fix clients on `/incremnt` will get 404 — acceptable, since the typo'd URL was never documented.

---

### BUG #16 — `log.Fatal` on server startup failure

**Problem.** If `http.ListenAndServe` failed (e.g., port already in use), `log.Fatal` called `os.Exit(1)` immediately after one log line. In containerized environments this interacted poorly with process supervisors that expect a clean exit and a chance to flush.

**Root cause.** `log.Fatal` does the equivalent of `log.Print` + `os.Exit(1)`, but the exit is implicit and not visible at the call site.

**Resolution.** Use `log.Printf` + `os.Exit(1)` explicitly.

**Code change.**

```go
// before
if err := http.ListenAndServe(addr, r); err != nil {
    log.Fatal(err)
}

// after
if err := http.ListenAndServe(addr, r); err != nil {
    log.Printf("server error: %v", err)
    os.Exit(1)
}
```

**Impact.** The error is logged with a clear prefix (`server error:`), and the non-zero exit is explicit. No behavior change for a successful start.

**Risk.** None. Equivalent runtime behavior, better diagnostics.

---

### Consistency change — `resetHandler` and `setHandler` enforce POST-only

**Problem.** `incrementHandler` and `decrementHandler` (after the #10 fix) both enforce POST-only. `resetHandler` and `setHandler` did not, so `GET /reset` would zero the counter and `GET /set` would set it to 0 — a larger CSRF/cache-poisoning surface than BUG #10 alone.

**Root cause.** Method checks were added piecemeal in earlier iterations and not applied uniformly.

**Resolution.** Add the same `r.Method != http.MethodPost` guard to both handlers. The 405 response body matches the other handlers (`{"status":"error","error":"method not allowed"}`) for consistency.

**Impact.** Non-POST requests to `/reset` and `/set` now get 405 instead of mutating state. Affects any client using the wrong verb.

**Risk.** A pre-fix client using `GET /reset` (or `DELETE /reset`, etc.) will now fail. Acceptable; the documented contract has always been POST.

---

## Test impact

The existing test suite in `main_test.go` was written to fail against the buggy code and pass after the fixes. With this commit, **all 8 test functions pass** under both `go test ./...` and `go test -race ./...`.

| Test function | Bug(s) it covers | What it asserts |
| --- | --- | --- |
| `TestCounterIncrement`              | (sanity, regression guard) | `Increment()` returns 1, then 2 from a fresh store. |
| `TestCounterDecrementClampsAtZero`  | #5  | `Decrement()` on a zero store returns 0, not -1. |
| `TestCounterSetRejectsNegative`     | #6  | `Set(-5)` returns 0 and does not store -5. |
| `TestCounterConcurrentSafety`       | #4  | 100 concurrent `Increment()` calls leave the store at exactly 100; only meaningful under `-race`. |
| `TestGetHandlerReturnsOK`           | #8  | `GET /counter` returns 200, not 500. |
| `TestGetHandlerSetsContentType`     | #7  | `Content-Type` header contains `application/json`. |
| `TestSetHandlerReturns400OnBadJSON` | #11, #12, #14 | `POST /set` with malformed body returns 400. |
| `TestSetHandlerSetsValue`           | #13, #6 (positive path) | `POST /set` with `{"value":42}` returns 200 and the response body has `counter: 42`. |

### Recommended additional tests (not present in the suite)

The following fixes are **not directly exercised** by the current tests. They are low-risk because the behavior is obvious, but adding tests would lock the contract:

| Suggested test | Bug / change it locks down |
| --- | --- |
| `TestDecrementHandlerRejectsNonPOST`            | #10 — `GET /decrement`, `PUT /decrement` return 405. |
| `TestResetHandlerRejectsNonPOST`                | Consistency — `GET /reset` returns 405. |
| `TestSetHandlerRejectsNonPOST`                  | Consistency — `GET /set` returns 405. |
| `TestIncrementRouteIsCorrect`                   | #15 — `mux` route table contains `/increment`, not `/incremnt`; an `httptest.NewServer` with the real router and a `POST /increment` returns 200. |
| `TestSetHandler400IncludesErrorMessage`         | #11 — error body contains the decode error string (e.g., `invalid character`). |
| `TestSetHandlerNegativeValueIsNoOp`             | #6 (HTTP path) — `POST /set` with `{"value":-5}` returns 200 and the response counter is unchanged from the prior value. |
| `TestConcurrentDecrementDoesNotGoNegative`      | #4 + #5 — many concurrent `Decrement()` calls on a small initial value never produce a negative result. |
| `TestMainStartupErrorExitsCleanly`              | #16 — harder to test without a subprocess; could be done with an `httptest`-style helper that captures the exit code, or simply verified by reading the code in code review. |

The QA sub-agent's plan (if it mirrors the table above) should be cross-referenced; this list is the minimum additional coverage to make the fix commit airtight.

---

## System impact and migration notes

### Backwards compatibility

| Area | Before | After | Migration note |
| --- | --- | --- | --- |
| Route `/incremnt` | Worked (typo'd). | 404. | Any client or tool calling the typo'd URL must switch to `/increment`. The README has always documented `/increment`, so this is a no-op for compliant clients. |
| Route `/increment` | 404. | Works (200). | No action required; this is the documented URL. |
| `Set(v)` with `v < 0` | Stored `v`; subsequent `Get` returned the negative value. | No-op; returns the current value unchanged. | Clients that *rely* on negative values being stored (none in this codebase) must validate inputs at the client side or send `0` to reset. |
| `decrementHandler` method check | Any verb accepted. | POST only; 405 otherwise. | Clients using `GET /decrement` will break. The documented method is POST. |
| `resetHandler` method check | Any verb accepted. | POST only; 405 otherwise. | Same as above. |
| `setHandler` method check | Any verb accepted. | POST only; 405 otherwise. | Same as above. |
| `setHandler` bad JSON | 200 with `counter: 0`. | 400 with `error: "<decode message>"`. | Clients that send malformed bodies and previously got a 200 will now get a 400; they should fix their payloads. |
| `getHandler` status | 500. | 200. | Clients that treated the 500 as a retry trigger will stop retrying. Net positive. |
| Counter under concurrent load | Lost updates, torn reads. | Correct, race-free. | No action required. |
| Startup failure exit | `log.Fatal` (implicit exit). | `log.Printf` + `os.Exit(1)` (explicit). | Process supervisors see the same exit code (1) and the same log line, but with a clearer prefix. |

### API changes summary

- **Canonical endpoint change:** `/incremnt` → `/increment`. The previous URL is no longer served.
- **New 405 surface:** `/decrement`, `/reset`, `/set` now return 405 Method Not Allowed for non-POST requests. The response body is the standard error envelope: `{"status":"error","error":"method not allowed"}`.
- **New 400 surface:** `POST /set` with malformed JSON now returns 400. The response body is `{"counter":0,"status":"error","error":"<decode error message>"}`.
- **Store semantics change:** `CounterStore.Set(v)` with `v < 0` is now a no-op. The HTTP layer (`/set`) still returns 200 in this case (because the JSON is well-formed and the store's rejection is the contract, not an error).

### Security implications

| Concern | Before | After |
| --- | --- | --- |
| **Mutability / CSRF** | `/decrement`, `/reset`, `/set` were mutating endpoints reachable via `GET` (and any other verb). A malicious link, a misconfigured cache, or a browser prefetch could change server state with a simple GET. | All four mutating endpoints require POST. CSRF surface is reduced (though still not zero — there is no CSRF token, which is out of scope). |
| **Input validation** | `Set` accepted any int, including negative; `setHandler` accepted any body shape. | `Set` rejects negative; `setHandler` rejects malformed JSON with 400. Untrusted input is now bounded at both layers. |
| **Race conditions** | `CounterStore` had a data race under concurrent access; the counter could go negative or lose updates. | `sync.Mutex` makes the store safe under any concurrent workload. `go test -race` is clean. |
| **Information disclosure** | Bad-JSON responses were 200 with the default-zero value, masking both client bugs and server-side issues. | Bad-JSON responses are 400 with the underlying error string. **Note:** the error string is from `encoding/json` and does not echo user input, so there is no new XSS / log-injection surface, but if the error path is ever extended to include user-controlled data it should be sanitized. |
| **Authentication / authorization** | None present. | Still none present. **Out of scope** for this commit, but worth a follow-up issue: any process that can reach `:8080` can read and mutate the counter. |
| **DoS via lock contention** | N/A (no lock). | The `sync.Mutex` is uncontended in practice (microsecond critical sections, one mutex per process). A pathological client could in theory queue requests on the lock, but the server's natural backpressure (read/write syscalls) dominates. No new DoS surface. |

---

## Out of scope

The following items are **not addressed** by this commit:

- **BUG #1** — Dependency / `go mod tidy` note. The README explicitly marks this as a non-bug ("by design"). No code change required.
- **BUG #2** — Not present in the source. No corresponding defect in `main.go`; the bug list in the README skips from #1 to #4.
- **BUG #3** — Not present in the source. Same as #2.
- **BUG #9** — Not present in the source. Same as #2.
- **Stretch goals** (from the README):
  - `-port` flag (currently hardcoded `:8080`).
  - File-based persistence so the counter survives restarts.
  - Structured logging via `slog` (or any structured logger).
  - `GET /healthz` endpoint for liveness/readiness probes.
- **Authentication / authorization** — there is none; any reachable client can mutate the counter. Worth a follow-up.
- **Observability** — no metrics, no request logging, no tracing.
- **Test additions** — the 8 existing tests pass; the additional tests recommended in *Test impact* are not added in this commit.

---

## Verification checklist

Run from `/home/user/Platform-Projects/counter-app/`:

```bash
# 1. Module / build sanity
go mod tidy
go build ./...
go vet ./...

# 2. Run the existing test suite (all 8 functions should pass)
go test ./...

# 3. Run with the race detector (exercises BUG #4 fix)
go test -race ./...

# 4. Optional: verbose run for the regressions we care about
go test -race -v -run 'TestCounter|TestGetHandler|TestSetHandler' ./...
```

Manual smoke tests (start the server in one terminal: `go run .`):

```bash
# Health / read (BUG #7, #8) — expect 200 + Content-Type: application/json + counter value
curl -i http://localhost:8080/counter

# Increment (BUG #15 — the route now actually exists)
curl -i -X POST http://localhost:8080/increment
curl -i -X POST http://localhost:8080/increment
curl -i http://localhost:8080/counter     # expect counter: 2

# Decrement (BUG #5, #10) — POST works, GET does not
curl -i -X POST http://localhost:8080/decrement
curl -i -X GET  http://localhost:8080/decrement   # expect 405

# Set (BUG #6, #11, #12, #13, #14) — valid value works, bad JSON returns 400
curl -i -X POST -H 'Content-Type: application/json' -d '{"value":42}' http://localhost:8080/set
curl -i -X POST -H 'Content-Type: application/json' -d '{not-json'      http://localhost:8080/set   # expect 400
curl -i -X POST -H 'Content-Type: application/json' -d '{"value":-5}'   http://localhost:8080/set   # expect 200, counter unchanged
curl -i -X GET  http://localhost:8080/set         # expect 405

# Reset (consistency change) — POST works, GET does not
curl -i -X POST http://localhost:8080/reset
curl -i -X GET  http://localhost:8080/reset       # expect 405
```

Pre-commit / pre-push:

```bash
gofmt -l .                                  # no output expected (all formatted)
go test -race -count=1 ./...                # final green run
git status                                  # only main.go is modified
git diff --stat                             # confirm scope
```

Commit only after every line above is green.
