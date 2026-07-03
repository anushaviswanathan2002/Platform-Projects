# Counter App (Go) — Test Project with Intentional Bugs

A small HTTP counter service in Go, intentionally seeded with bugs. Use this
project to practice:

1. Installing Go project dependencies.
2. Running the test suite and reading failures.
3. Fixing the bugs and re-running tests until everything is green.

## Prerequisites

- Go 1.21 or newer.

## Install Dependencies

```bash
cd counter-app
go mod download
go mod tidy
```

## Run the App

```bash
go run .
# counter app listening on :8080
```

## API

| Method | Path         | Body                | Description        |
| ------ | ------------ | ------------------- | ------------------ |
| GET    | `/counter`   | —                   | Read counter value |
| POST   | `/increment` | —                   | Increment counter  |
| POST   | `/decrement` | —                   | Decrement counter  |
| POST   | `/reset`     | —                   | Reset to 0         |
| POST   | `/set`       | `{"value": <int>}`  | Set to specific value |

Example:
```bash
curl -X POST http://localhost:8080/increment
# {"counter":1,"status":"incremented"}
```

## Run Tests

```bash
go test ./...
# or with the race detector to surface BUG #4
go test -race ./...
```

Several tests are written to **fail** against the buggy code. They will pass
once you fix the bugs.

## Bug List (Fix Me!)

The following bugs are intentionally present. Find and fix each one. The
failing tests point to most of them.

| #   | Category            | Description                                                                 |
| --- | ------------------- | --------------------------------------------------------------------------- |
| 1   | Dependency          | `go.mod` may need a `go mod tidy` to populate `go.sum` (non-bug, by design) |
| 4   | Concurrency         | `CounterStore` has no mutex; concurrent requests race on `value`            |
| 5   | Logic               | `Decrement()` allows counter to go below 0                                  |
| 6   | Validation          | `Set()` does not reject negative values                                     |
| 7   | HTTP                | `writeJSON` does not set `Content-Type: application/json`                   |
| 8   | HTTP                | `getHandler` returns 500 on success; should be 200                           |
| 10  | HTTP                | `decrementHandler` accepts any HTTP method; should be POST-only             |
| 11  | Error handling      | `setHandler` does not validate that a value was actually decoded             |
| 12  | HTTP                | `setHandler` returns 200 on bad JSON; should be 400                          |
| 13  | Code smell          | `setHandler` round-trips int -> string -> int for no reason                 |
| 14  | Error handling      | `strconv.Atoi` error is silently ignored in `setHandler`                    |
| 15  | Routing             | Route is registered as `/incremnt` (typo) — clients get 404 on `/increment` |
| 16  | Robustness          | `main` uses `log.Fatal` on server error; should log and exit gracefully      |

## Stretch Goals

- Add a `-port` flag instead of hardcoding `:8080`.
- Persist the counter to a file so it survives restarts.
- Add structured logging (e.g., `slog`).
- Add a `GET /healthz` endpoint.
