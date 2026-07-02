# Testing

A manual, end-to-end test matrix. Each row maps one of the 14 issues in
`KNOWN_ISSUES.md` to a copy-pasteable shell command sequence and the
expected output. Run from the repository root with the project built:

```bash
export PATH="/usr/local/rustup/toolchains/1.89.0-x86_64-unknown-linux-gnu/bin:$PATH"
cargo build
```

All tests assume a clean state:

```bash
rm -rf data
```

The binary is `./target/debug/todo` for short.

---

## Issue 1 — `add` stores the literal word `add`

```bash
./target/debug/todo add "buy milk"
./target/debug/todo list
```

Expected: `Added todo #0`, then `[0] [ ] #0 - buy milk`.
The literal word `add` must **not** appear in the title.

Negative case:

```bash
./target/debug/todo add
```

Expected: `error: 'add' needs a title`, exit code `1`.

---

## Issue 2 — `list` panics on an empty list

```bash
rm -rf data
./target/debug/todo list
echo "exit=$?"
```

Expected: no output, exit code `0`. Must not panic.

---

## Issue 3 — `done` panics on missing or non-numeric id

```bash
rm -rf data
./target/debug/todo add "alpha" >/dev/null
./target/debug/todo done
echo "exit=$?"
./target/debug/todo done abc
echo "exit=$?"
./target/debug/todo done -1
echo "exit=$?"
```

Expected: each command prints a friendly error, exits with code `1`,
and never panics. The `data/todos.json` file is unchanged.

---

## Issue 4 — `remove` panics on missing or non-numeric id

```bash
./target/debug/todo remove
echo "exit=$?"
./target/debug/todo remove xyz
echo "exit=$?"
```

Expected: friendly errors, exit code `1`, no panic.

---

## Issue 5 — `filter` is case-sensitive

```bash
./target/debug/todo add "buy milk" >/dev/null
./target/debug/todo add "Buy bread" >/dev/null
./target/debug/todo filter BUY
./target/debug/todo filter Milk
```

Expected: both filters produce at least one match (case-insensitive).

---

## Issue 6 — `clear` does not persist

```bash
./target/debug/todo clear
./target/debug/todo list
```

Expected: `Cleared all todos.`, then an empty `list` (no output).
A new shell invocation of `list` must also be empty:

```bash
./target/debug/todo list
```

Expected: no output.

---

## Issue 7 — Every todo has `id = 0`

```bash
rm -rf data
./target/debug/todo add "a" >/dev/null
./target/debug/todo add "b" >/dev/null
./target/debug/todo add "c" >/dev/null
./target/debug/todo list
```

Expected: ids `#0`, `#1`, `#2` (or, equivalently, three distinct ids).

---

## Issue 8 — `next_id` is never incremented

Same commands as Issue 7. Expected: distinct ids for each todo. The
`next_id` field is private; the on-disk JSON should also reflect the
new state on the next `load`.

---

## Issue 9 — `mark_done` silently does nothing on bad index

```bash
./target/debug/todo done 999
echo "exit=$?"
```

Expected: `error: todo id out of range`, exit code `1`, no panic.

---

## Issue 10 — `remove` panics on out-of-range index

```bash
./target/debug/todo remove 999
echo "exit=$?"
./target/debug/todo rm 5
echo "exit=$?"
```

Expected: `error: todo id out of range`, exit code `1`, no panic.

---

## Issue 11 — `filter ""` returns every todo

```bash
./target/debug/todo filter ""
echo "exit=$?"
```

Expected: no output, exit code `0`. (The empty needle is short-circuited.)

---

## Issue 12 — Data goes to a hidden OS folder

```bash
rm -rf data
./target/debug/todo add "x" >/dev/null
ls -la data
```

Expected: a `data/` directory next to `src/`, containing `todos.json`.
The path is `./data/todos.json`, not under `~/.local/share` or similar.

---

## Issue 13 — Corrupt `todos.json` is overwritten

```bash
rm -rf data
./target/debug/todo add "real" >/dev/null
echo "this is not json" > data/todos.json
./target/debug/todo list
ls -la data
cat data/todos.json.bak
```

Expected:

- `list` returns an empty result without panicking.
- `data/todos.json.bak` exists and contains the literal string
  `this is not json` (the original corrupt payload, preserved).
- `data/todos.json` contains a valid empty list (`"items": []`).

---

## Issue 14 — Disk/permission errors during `save` are swallowed

The exact command depends on the host's permission model. On a host
where `chmod 555` is honoured:

```bash
rm -rf data
./target/debug/todo add "first" >/dev/null
chmod 555 data
./target/debug/todo add "second"
echo "exit=$?"
chmod 755 data
```

Expected: an `error:` line on stderr, exit code `1`, and the
`data/todos.json` file is **not** corrupted or silently overwritten.

In sandboxed environments (Docker, CI) `chmod` may be bypassed; the
important property is that the code path is `?`-propagated from
`save` through `run` to `main`, and that the error message is the
underlying `io::Error` rather than a silent success.

---

## Full happy-path smoke test

```bash
rm -rf data
./target/debug/todo add "Buy milk"
./target/debug/todo add "Buy bread"
./target/debug/todo add "write report"
./target/debug/todo list
./target/debug/todo filter Buy
./target/debug/todo done 1
./target/debug/todo list
./target/debug/todo remove 2
./target/debug/todo list
./target/debug/todo clear
./target/debug/todo list
```

Expected: 3 adds with unique ids, list shows three todos, `filter Buy`
matches the two buy-* todos, `done 1` flips the second todo to `[x]`,
`remove 2` deletes the third, `clear` empties the list and persists.
