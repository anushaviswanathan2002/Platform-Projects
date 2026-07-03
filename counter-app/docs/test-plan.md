# Test Plan: Counter App Bug Fixes (main.go)

## 1. Overview

This test plan exercises the 13 documented bug fixes in `main.go` (BUG #4–#8, #10–#16, plus the consistency fix that makes `resetHandler` and `setHandler` POST-only). The approach is layered: **unit tests** for `CounterStore` logic (BUG #4, #5, #6, #13), **handler-level tests** driven through `httptest` for HTTP semantics (BUG #7, #8, #10, #11, #12, #14, plus the additional POST-only behavior), and **route-level tests** through the real `mux.Router` (BUG #15, and method enforcement in aggregate). A **cross-cutting layer** validates concurrency under `go test -race`, Content-Type on every handler, method enforcement, routing, and graceful-shutdown ergonomics (BUG #16). Each case is tagged with a TC ID, its bug, and whether it is already covered by an existing test in `main_test.go` or represents a gap. No Go code is written in this document; it is a test-design artifact only.

## 2. Test Cases Grouped by Bug

### BUG #4 — Concurrency: `CounterStore` is now protected by `sync.Mutex`

- **TC-4.1 — Concurrent increments are atomic**
  - Preconditions: Fresh `CounterStore`; `value = 0`.
  - Steps: Spawn N goroutines (e.g. 1000) each calling `Increment()`; `WaitGroup.Wait()`; call `Get()`.
  - Expected: `Get()` returns exactly N. No data race is reported under `go test -race`.
  - Bug validated: BUG #4.
  - Coverage: Already covered by `TestCounterConcurrentSafety` (basic case with N=100).

- **TC-4.2 — Mixed concurrent Increment/Decrement/Set/Get**
  - Preconditions: `CounterStore` initialized to 0.
  - Steps: Run several goroutines concurrently mixing `Increment`, `Decrement` (clamped), `Set(42)`, `Get` for a fixed duration or N iterations. After `Wait`, call `Get()`.
  - Expected: Final value is one of the values that was last set or a value consistent with the final operation that touched it; **no race detector report**; no torn reads.
  - Bug validated: BUG #4.

- **TC-4.3 — Concurrent `Set` with negative arguments is rejected safely**
  - Preconditions: Fresh store.
  - Steps: Spawn goroutines each calling `Set(-i)` while others call `Get()`. After `Wait`, `Get()` should equal 0 (or the value set by non-negative calls if any mixed in).
  - Expected: Value never goes negative; `-race` clean.
  - Bug validated: BUG #4, BUG #6.

### BUG #5 — Logic: `Decrement()` clamps at zero

- **TC-5.1 — Decrement at zero stays at zero** *(happy / boundary)*
  - Preconditions: `CounterStore` value 0.
  - Steps: Call `Decrement()` once, then again.
  - Expected: Returns 0 both times; `Get()` returns 0.
  - Bug validated: BUG #5.
  - Coverage: Already covered by `TestCounterDecrementClampsAtZero`.

- **TC-5.2 — Decrement from 1 yields 0, next decrement stays 0** *(boundary)*
  - Preconditions: Value = 1.
  - Steps: `Increment()` to 1, then `Decrement()` twice.
  - Expected: First `Decrement()` returns 0; second `Decrement()` returns 0.
  - Bug validated: BUG #5.

- **TC-5.3 — Decrement from large positive value works correctly** *(happy path)*
  - Preconditions: Value = 1,000,000.
  - Steps: `Set(1_000_000)`, then `Decrement()`; verify 999,999.
  - Expected: Returns 999,999, no underflow.
  - Bug validated: BUG #5 (no underflow / signed wrap).

- **TC-5.4 — Many consecutive decrements eventually clamp** *(edge)*
  - Preconditions: Value = 5.
  - Steps: Call `Decrement()` 100 times.
  - Expected: First 5 return 4,3,2,1,0; remaining 95 return 0.
  - Bug validated: BUG #5.

### BUG #6 — Validation: `Set(v int)` ignores negative `v`

- **TC-6.1 — `Set(-1)` returns current value unchanged** *(negative case)*
  - Preconditions: Value = 0.
  - Steps: `Set(-1)`; then `Get()`.
  - Expected: `Set` returns 0; `Get` returns 0.
  - Bug validated: BUG #6.
  - Coverage: Already covered by `TestCounterSetRejectsNegative` (uses -5).

- **TC-6.2 — `Set(0)` is allowed and resets the counter** *(happy path / boundary)*
  - Preconditions: Value = 42.
  - Steps: `Set(0)`; then `Get()`.
  - Expected: Returns 0; counter is now 0.
  - Bug validated: BUG #6 (0 is non-negative and must be accepted).

- **TC-6.3 — `Set` accepts the maximum `int` value** *(edge / BUG #13 round-trip absence)*
  - Preconditions: Value = 0.
  - Steps: `Set(math.MaxInt)`; then `Get()`.
  - Expected: Both calls return `math.MaxInt`. (Validates that no string round-trip silently truncates large values — relevant to BUG #13 fix.)
  - Bug validated: BUG #6, BUG #13.

- **TC-6.4 — `Set(very_large_negative)` is rejected** *(negative edge)*
  - Preconditions: Value = 7.
  - Steps: `Set(math.MinInt)`; then `Get()`.
  - Expected: `Set` returns 7; `Get` returns 7.
  - Bug validated: BUG #6.

### BUG #7 — HTTP: `writeJSON` sets `Content-Type: application/json`

- **TC-7.1 — `GET /counter` returns `Content-Type: application/json`** *(happy path)*
  - Preconditions: Fresh store; handler invoked through `httptest`.
  - Steps: `GET /counter`; inspect response header.
  - Expected: `Content-Type` contains `application/json`.
  - Bug validated: BUG #7.
  - Coverage: Already covered by `TestGetHandlerSetsContentType`.

- **TC-7.2 — All mutating handlers also set the JSON content type** *(gap)*
  - Preconditions: Fresh store for each call.
  - Steps: For each of `incrementHandler`, `decrementHandler`, `resetHandler`, `setHandler` (both success and error paths), invoke via `httptest` and inspect the response header.
  - Expected: Every response, including 400 and 405, advertises `application/json`.
  - Bug validated: BUG #7.

- **TC-7.3 — `writeJSON` is the only encoder (no `text/plain` leak)** *(negative case)*
  - Preconditions: Handler that triggers an error path.
  - Steps: Call `setHandler` with bad JSON; inspect the raw recorder.
  - Expected: Header must not be `text/plain` or absent; charset suffix is acceptable.
  - Bug validated: BUG #7.

### BUG #8 — HTTP: `getHandler` returns 200 OK

- **TC-8.1 — `GET /counter` returns 200** *(happy path)*
  - Preconditions: Fresh store.
  - Steps: `httptest` request `GET /counter`.
  - Expected: `rr.Code == http.StatusOK`.
  - Bug validated: BUG #8.
  - Coverage: Already covered by `TestGetHandlerReturnsOK`.

- **TC-8.2 — `GET /counter` response body decodes to a `response` with `counter` and `status` fields** *(happy path)*
  - Preconditions: Value = 5.
  - Steps: `Set(5)`; then `GET /counter`; decode body.
  - Expected: `resp.Counter == 5`, `resp.Status == "ok"`, `resp.Error == ""`.
  - Bug validated: BUG #8.

- **TC-8.3 — `GET /counter` is idempotent** *(edge)*
  - Preconditions: Fresh store.
  - Steps: Two consecutive `GET /counter` calls.
  - Expected: Both return 200 with the same body.
  - Bug validated: BUG #8.

### BUG #10 — HTTP: `decrementHandler` rejects non-POST with 405

- **TC-10.1 — `GET /decrement` returns 405** *(negative case)*
  - Preconditions: Fresh store.
  - Steps: `httptest` request `GET /decrement` against the handler.
  - Expected: `rr.Code == http.StatusMethodNotAllowed`; body `error` field set.
  - Bug validated: BUG #10.
  - Coverage: **GAP** — not covered by existing tests.

- **TC-10.2 — `PUT /decrement` returns 405** *(negative edge)*
  - Preconditions: Fresh store.
  - Steps: Send a `PUT` request.
  - Expected: 405.
  - Bug validated: BUG #10.

- **TC-10.3 — `DELETE /decrement` returns 405** *(negative edge)*
  - Preconditions: Fresh store.
  - Steps: Send a `DELETE` request.
  - Expected: 405.
  - Bug validated: BUG #10.

- **TC-10.4 — `POST /decrement` returns 200 and decrements** *(happy path)*
  - Preconditions: Value = 3.
  - Steps: `POST /decrement`.
  - Expected: 200; body `counter == 2`; `status == "decremented"`.
  - Bug validated: BUG #10 (regression: ensure POST still works).

### BUG #11 — Error handling: `setHandler` validates the body and returns 400 on failure

- **TC-11.1 — `POST /set` with empty body returns 400** *(negative / edge)*
  - Preconditions: Fresh store.
  - Steps: Send `POST /set` with body length 0.
  - Expected: 400; `status == "error"`; `error` field populated.
  - Bug validated: BUG #11.
  - Coverage: **GAP** — `TestSetHandlerReturns400OnBadJSON` covers malformed JSON, not empty body.

- **TC-11.2 — `POST /set` with body missing the `value` field returns 400 or zero-set** *(edge)*
  - Preconditions: Fresh store, value initially 7.
  - Steps: Send `{"foo": 1}` (no `value` key).
  - Expected: Either 400 (decode-incompatible shape causes error) or, if decode succeeds, `value` defaults to 0 — but the handler must not silently retain the previous value through some string path. Either way, the response must be 200 with `counter == 0` or 400, but never 200 with a stale value.
  - Bug validated: BUG #11, BUG #13.

- **TC-11.3 — `POST /set` with wrong types returns 400** *(negative)*
  - Preconditions: Fresh store.
  - Steps: Send `{"value": "not-an-int"}`.
  - Expected: 400; `error` contains a type-related decode error message.
  - Bug validated: BUG #11, BUG #14.

### BUG #12 — HTTP: `setHandler` returns 400 on bad JSON (was 200)

- **TC-12.1 — Malformed JSON yields 400** *(negative case)*
  - Preconditions: Fresh store.
  - Steps: `POST /set` body `{not-json`.
  - Expected: 400; `status == "error"`.
  - Bug validated: BUG #12.
  - Coverage: Already covered by `TestSetHandlerReturns400OnBadJSON`.

- **TC-12.2 — Trailing garbage yields 400** *(negative edge)*
  - Preconditions: Fresh store.
  - Steps: `POST /set` body `{"value": 1}garbage`.
  - Expected: 400.
  - Bug validated: BUG #12.

- **TC-12.3 — Empty JSON object is accepted and sets counter to 0** *(happy edge — proves the body decoded)*
  - Preconditions: Fresh store.
  - Steps: `POST /set` body `{}`.
  - Expected: 200; `counter == 0`.
  - Bug validated: BUG #11 (body was decoded), BUG #12 (valid JSON is allowed).

### BUG #13 — Code smell: `setHandler` no longer does `int→string→int` round-trip

- **TC-13.1 — `POST /set` with the max int value passes through unmodified** *(edge / happy path)*
  - Preconditions: Fresh store.
  - Steps: `POST /set` with `{"value": 9223372036854775807}` (`math.MaxInt64` on 64-bit).
  - Expected: 200; `counter` reflects the exact large value (no truncation).
  - Bug validated: BUG #13.
  - Coverage: **GAP** — none of the existing tests stress a value that would expose an `int→strconv` round-trip truncation.

- **TC-13.2 — `POST /set` with negative value triggers the new in-store rejection** *(cross-bug)*
  - Preconditions: Fresh store; value = 5.
  - Steps: `POST /set` with `{"value": -3}`.
  - Expected: 200; `counter == 5` (unchanged — `Set` rejected it).
  - Bug validated: BUG #6 + BUG #13 (no round-trip means `-3` is delivered to `Set` as `-3` and rejected as before).

### BUG #14 — Error handling: no more silent `strconv.Atoi` path; fail fast on JSON decode

- **TC-14.1 — Malformed JSON short-circuits with 400, counter not modified** *(negative case)*
  - Preconditions: Value = 9.
  - Steps: `POST /set` with `{not-json`; then `Get()`.
  - Expected: 400; `Get()` returns 9 (counter not silently zeroed or corrupted).
  - Bug validated: BUG #14.
  - Coverage: Partial — `TestSetHandlerReturns400OnBadJSON` checks the 400 but not the "no side effect" property.

- **TC-14.2 — Successful decode calls `Set` exactly once** *(cross-bug)*
  - Preconditions: Fresh store.
  - Steps: `POST /set` with valid `{"value": 4}`; observe counter.
  - Expected: 200; `counter == 4`; no second pass / no error swallowed.
  - Bug validated: BUG #14 (no fallback string conversion path).

### BUG #15 — Routing: `/increment` is correctly spelled

- **TC-15.1 — `POST /increment` reaches `incrementHandler` and returns 200** *(happy path)*
  - Preconditions: Fresh store; `mux.NewRouter()` is built exactly as in `main()`.
  - Steps: Send `POST /increment` to the router via `httptest.NewRecorder`.
  - Expected: 200; body `counter == 1`; `status == "incremented"`.
  - Bug validated: BUG #15.
  - Coverage: **GAP** — handler is only tested directly, not through the router.

- **TC-15.2 — `POST /incremnt` (the typo) returns 404** *(negative case — regression guard)*
  - Preconditions: Router built as in `main()`.
  - Steps: `POST /incremnt`.
  - Expected: 404 from the gorilla router (no handler matched). This guarantees the typo is gone.
  - Bug validated: BUG #15.

- **TC-15.3 — All five routes are reachable and method-constrained** *(integration-style edge)*
  - Preconditions: Router built as in `main()`.
  - Steps: For each route (`/counter GET`, `/increment POST`, `/decrement POST`, `/reset POST`, `/set POST`), send the **wrong** method and the **right** method.
  - Expected: Wrong method → 404 (gorilla returns 404 for path-but-not-method, or 405 if we register a global method-not-allowed handler — current behavior is 404 for method mismatch without that handler). Right method → 200.
  - Bug validated: BUG #15, BUG #10, plus the additional POST-only fix on `resetHandler` and `setHandler`.

### BUG #16 — Robustness: `main()` uses `log.Print + os.Exit(1)` instead of `log.Fatal`

- **TC-16.1 — `main()`-style error path is testable in isolation** *(happy / negative hybrid)*
  - Preconditions: Refactor or extract the server-start expression into a helper, or test the idiom in a small wrapper. Otherwise this case is best covered by an **integration test** that runs the binary with an in-use port.
  - Steps: Bind a listener on `:0`; start the same `http.ListenAndServe` flow; close the listener; assert that the error-handling branch logs and exits with code 1.
  - Expected: `os.Exit(1)` is reached (or, if untestable directly, the call shape `log.Printf(...); os.Exit(1)` is grepped in the source).
  - Bug validated: BUG #16.
  - Coverage: **GAP** — there is no automated test for BUG #16. (See Recommendations.)

- **TC-16.2 — Process exits with non-zero status on port-bind failure** *(integration / negative)*
  - Preconditions: Build the binary (`go build`); pre-bind port 8080 in another process or `nc`.
  - Steps: Run the built binary.
  - Expected: Process logs an error and exits with code 1 (verifiable via `$?` in shell).
  - Bug validated: BUG #16.

### Additional fix — `resetHandler` and `setHandler` now enforce POST-only with 405

- **TC-A1 — `GET /reset` returns 405** *(negative)*
  - Preconditions: Fresh store.
  - Steps: `httptest` `GET /reset`.
  - Expected: 405; `status == "error"`; `error` mentions "method not allowed".
  - Bug validated: Additional fix.
  - Coverage: **GAP**.

- **TC-A2 — `GET /set` returns 405** *(negative)*
  - Preconditions: Fresh store.
  - Steps: `httptest` `GET /set`.
  - Expected: 405; `status == "error"`.
  - Bug validated: Additional fix.
  - Coverage: **GAP**.

- **TC-A3 — `PUT /reset` and `DELETE /reset` return 405** *(negative edge)*
  - Preconditions: Fresh store.
  - Steps: `PUT /reset`; `DELETE /reset`.
  - Expected: Both 405.
  - Bug validated: Additional fix.

- **TC-A4 — `POST /reset` returns 200 and zeroes the counter** *(happy path)*
  - Preconditions: Value = 9.
  - Steps: `POST /reset`.
  - Expected: 200; `counter == 0`; `status == "reset"`.
  - Bug validated: Additional fix (regression: ensure POST still works after the gate was added).

## 3. Coverage Matrix

| Bug | Description | Test cases | Status |
| --- | --- | --- | --- |
| #4 | Concurrency: `sync.Mutex` | TC-4.1, TC-4.2, TC-4.3 | Partially covered — `TestCounterConcurrentSafety` covers TC-4.1 only; mixed and Set/rejection races are gaps. |
| #5 | `Decrement` clamps at 0 | TC-5.1, TC-5.2, TC-5.3, TC-5.4 | Partially covered — `TestCounterDecrementClampsAtZero` covers TC-5.1; multi-step and large-value paths are gaps. |
| #6 | `Set` rejects negative | TC-6.1, TC-6.2, TC-6.3, TC-6.4 | Partially covered — `TestCounterSetRejectsNegative` covers TC-6.1; 0 acceptance and `MaxInt`/`MinInt` edges are gaps. |
| #7 | `Content-Type: application/json` | TC-7.1, TC-7.2, TC-7.3 | Partially covered — `TestGetHandlerSetsContentType` covers TC-7.1 on `getHandler` only; the other handlers and error paths are gaps. |
| #8 | `getHandler` returns 200 | TC-8.1, TC-8.2, TC-8.3 | Covered — `TestGetHandlerReturnsOK` covers TC-8.1; TC-8.2/TC-8.3 are minor gaps. |
| #10 | `decrementHandler` non-POST → 405 | TC-10.1, TC-10.2, TC-10.3, TC-10.4 | **GAP** — none of the four cases are covered by existing tests. |
| #11 | `setHandler` validates body | TC-11.1, TC-11.2, TC-11.3 | **GAP** — empty body and wrong-type body are not tested. |
| #12 | `setHandler` returns 400 on bad JSON | TC-12.1, TC-12.2, TC-12.3 | Partially covered — `TestSetHandlerReturns400OnBadJSON` covers TC-12.1; trailing-garbage and empty-object cases are gaps. |
| #13 | No `int→string→int` round-trip | TC-13.1, TC-13.2 | **GAP** — no existing test sends a value large enough to expose a `strconv` round-trip truncation. |
| #14 | Fail fast on JSON decode | TC-14.1, TC-14.2 | Partially covered — TC-14.1's 400 assertion exists in `TestSetHandlerReturns400OnBadJSON`, but the "no side effect" property is a gap. |
| #15 | Route is `/increment` | TC-15.1, TC-15.2, TC-15.3 | **GAP** — handlers are tested in isolation; the router wiring is not. |
| #16 | `log.Print + os.Exit(1)` on server error | TC-16.1, TC-16.2 | **GAP** — no automated test. |
| Additional | `resetHandler` and `setHandler` POST-only | TC-A1, TC-A2, TC-A3, TC-A4 | **GAP** — none covered. |

## 4. Cross-Cutting Tests

These are not tied to a single bug number; they exercise properties that span multiple fixes.

- **CC-1 — Race detector on the whole suite**
  - Approach: Run `go test -race ./...` after each change.
  - Covers: BUG #4, BUG #6 (rejection under contention), BUG #13 (correctness of large values under contention).
  - Expected: No `WARNING: DATA RACE` output. All existing `CounterStore` tests pass under `-race`.

- **CC-2 — `Content-Type` is `application/json` on every response**
  - Approach: A table-driven handler test invoking every handler and asserting the header on success and error responses (200, 400, 405).
  - Covers: BUG #7 across all handlers.

- **CC-3 — Method enforcement is uniform**
  - Approach: Table-driven test with rows for `(route, method, expectedStatus)` covering all four POST-only routes and the one GET route, on both supported and unsupported methods.
  - Covers: BUG #10, additional POST-only fix on `resetHandler` and `setHandler`, regression for `getHandler` and `incrementHandler`.

- **CC-4 — Routing wiring**
  - Approach: Build the same `mux.NewRouter()` as `main()`; send a request to each documented path with the correct method and assert the route exists (non-404).
  - Covers: BUG #15, plus an integrity check that all five routes are registered.

- **CC-5 — JSON shape stability**
  - Approach: For each successful response, decode into `response` and assert `counter`, `status` are populated; for each error response, assert `error` is populated and `status == "error"`.
  - Covers: BUG #11, BUG #12, BUG #14, plus the additional POST-only fix.

- **CC-6 — Graceful error reporting from `main()`**
  - Approach: Either an integration test that runs the binary against a busy port, or a refactored helper that exposes the `http.ListenAndServe` + `log.Printf + os.Exit(1)` idiom. Verify exit code is 1 and a non-empty error is logged.
  - Covers: BUG #16.

- **CC-7 — Side-effect-free failure**
  - Approach: For each handler's error path, snapshot the counter, send a failing request, then re-read the counter and assert it is unchanged.
  - Covers: BUG #11, BUG #12, BUG #14.

## 5. Recommendations — New Go Test Functions for `main_test.go`

The following suggested `Test*` functions close the gaps identified in the matrix. Names follow the existing `TestXxxYyy` convention in `main_test.go`. **No Go code is provided here** — only a brief description and the bug it targets.

1. `TestCounterDecrementFromPositive` — Verifies `Decrement()` from a positive value yields the correct sequence and then clamps (TC-5.2, TC-5.3, TC-5.4). Targets BUG #5.
2. `TestCounterSetAcceptsZero` — Asserts `Set(0)` is allowed and returns 0 (TC-6.2). Targets BUG #6 boundary.
3. `TestCounterSetAcceptsMaxInt` — Sends `math.MaxInt` to `Set` and asserts no truncation, exposing a regression of the old `int→string→int` round-trip (TC-13.1). Targets BUG #6 and BUG #13.
4. `TestCounterConcurrentMixedOps` — Runs `Increment`, `Decrement`, `Set`, and `Get` in parallel and asserts `-race` is clean and final value is in the expected set (TC-4.2). Targets BUG #4.
5. `TestWriteJSONContentTypeOnAllHandlers` — Table-driven; for every handler and status, asserts `Content-Type` includes `application/json` (TC-7.2). Targets BUG #7.
6. `TestDecrementHandlerRejectsNonPOST` — Sends `GET`, `PUT`, `DELETE` to `/decrement` and asserts 405 (TC-10.1, TC-10.2, TC-10.3). Targets BUG #10.
7. `TestDecrementHandlerAcceptsPOST` — Sends `POST /decrement` from value 3 and asserts 200 and `counter == 2` (TC-10.4). Regression for BUG #10.
8. `TestSetHandlerRejectsEmptyBody` — Sends `POST /set` with no body and asserts 400 (TC-11.1). Targets BUG #11.
9. `TestSetHandlerRejectsWrongType` — Sends `POST /set` with `{"value": "x"}` and asserts 400 with a populated `error` field (TC-11.3). Targets BUG #11 and BUG #14.
10. `TestSetHandlerAcceptsEmptyObject` — Sends `POST /set` with `{}` and asserts 200 and `counter == 0` (TC-12.3). Targets BUG #11 (body decoded successfully).
11. `TestSetHandlerNoSideEffectOnBadJSON` — Sends malformed JSON after setting the counter to 9, asserts 400 **and** that `Get()` is still 9 (TC-14.1). Targets BUG #14.
12. `TestRouterIncrementRoute` — Builds a real `mux.Router` matching `main()`'s wiring, sends `POST /increment`, and asserts 200 (TC-15.1). Also asserts `POST /incremnt` returns 404 (TC-15.2). Targets BUG #15.
13. `TestRouterMethodEnforcement` — Table-driven; for each of the four POST-only routes (`/increment`, `/decrement`, `/reset`, `/set`), sends `GET` and asserts 405. Sends `GET /counter` and asserts 200. Targets BUG #10 and the additional POST-only fix.
14. `TestResetHandlerRejectsNonPOST` — Sends `GET`, `PUT`, `DELETE` to `/reset` and asserts 405 (TC-A1, TC-A3). Targets additional fix.
15. `TestResetHandlerAcceptsPOST` — From value 9, sends `POST /reset` and asserts 200 and `counter == 0` (TC-A4). Regression for additional fix.
16. `TestSetHandlerRejectsNonPOST` — Sends `GET /set` and asserts 405 (TC-A2). Targets additional fix.
17. `TestMainExitsNonZeroOnListenError` — Integration or refactored test that exercises the `log.Printf + os.Exit(1)` path (TC-16.1, TC-16.2). Targets BUG #16. (Implementation note: a small refactor — extracting the listen-and-handle-error block into a helper function — makes this fully testable; otherwise this test is an integration test that runs the built binary against a busy port.)
