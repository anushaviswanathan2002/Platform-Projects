# Fixes applied

Formal write-up of how each of the 14 bugs listed in `KNOWN_ISSUES.md`
was resolved. Issue numbers match the table in `KNOWN_ISSUES.md` so the
three files can be read side by side:

- `KNOWN_ISSUES.md` — symptoms and hints (the bugs)
- `docs/FIXES.md` — this file (how each was fixed)
- `docs/TESTING.md` — verification commands

Fixes are grouped in the same order the issues suggest
(**compile → safe commands → correct behaviour → robust persistence**),
which is also the order they were applied.

## 1. Make the app compile and run

### Issue 1 — `todo add buy milk` stored `"add buy milk"`

**Symptom.** The first todo's title was always the literal substring
`add ...` rather than the user-supplied words.

**Root cause.** `args[2..].join(" ")` looked correct, but the surrounding
code passed that string to `Todo::new(title)` and added the resulting
todo without verifying there *was* a title. If the user ran
`todo add` with no further words, `args[2..]` was an empty slice, the
joined string was `""`, and a blank todo was silently created. Worse,
older versions of this code joined starting at the wrong index and
included the literal `add` token in the title.

**Fix.** Require at least one word of title beyond the subcommand, and
join `args[2..]` so the literal `add` token is excluded:

```rust
if args.len() < 3 {
    return Err("'add' needs a title".into());
}
let title = args[2..].join(" ");
let id = list.add(title);
```

**Why this fix and not another.** Guarding at the CLI boundary keeps
`Todo::new` permissive and lets `main` produce a clear, command-specific
error message.

### Issue 2 — `todo list` panicked on an empty list

**Symptom.** `attempt to subtract with overflow` panic on the first run
with no data.

**Root cause.** The loop bound was `0..list.len() - 1`. When `list.len()`
was `0`, `0 - 1` underflowed on a `usize`.

**Fix.** Iterate `0..list.len()`:

```rust
for i in 0..list.len() {
    if let Some(t) = list.get(i) {
        let mark = if t.done { "x" } else { " " };
        println!("[{}] [{}] #{} - {}", i, mark, t.id, t.title);
    }
}
```

**Why this fix and not another.** Using `get` instead of direct indexing
would also have worked, but `0..list.len()` is the idiomatic Rust pattern
and zero items naturally iterates zero times.

## 2. Make the basic commands safe

### Issue 3 — `todo done` panicked on missing or non-numeric id

**Symptom.** `todo done` (no id) and `todo done abc` both crashed with
`index out of bounds` and `ParseIntError::unwrap()` panics.

**Root cause.** `args[2].parse().unwrap()` did two unsafe things at
once: indexing `args[2]` without a length check, and `.unwrap()`-ing a
`Result` that could legitimately be an `Err`.

**Fix.** A new `parse_index` helper returns a `Result` with friendly
errors for both failure modes, and `main` propagates with `?`:

```rust
fn parse_index(args: &[String], cmd: &str) -> Result<usize, Box<dyn Error>> {
    let arg = args
        .get(2)
        .ok_or_else(|| format!("'{}' needs an id", cmd))?;
    arg.parse::<usize>()
        .map_err(|_| format!("'{}' id must be a number (got {:?})", cmd, arg).into())
}
```

`main` now returns `Result<(), Box<dyn Error>>` and exits with a
printed error and code `1` on failure instead of panicking.

### Issue 4 — `todo remove` had the same panics

**Symptom.** Same as Issue 3, plus a panic on out-of-range.

**Root cause.** Same pattern as Issue 3, plus an unguarded
`self.items.remove(idx)` in the storage layer.

**Fix.** Reuse the `parse_index` helper for input validation, then call
`list.remove(idx)?`. The bounds check is delegated to `TodoList::remove`
(see Issue 10) so the CLI never panics on a bad index.

### Issue 9 — `mark_done` silently did nothing on a bad index

**Symptom.** `todo done 99` exited `0` with no output, leaving the user
unsure whether anything happened.

**Root cause.** `mark_done` matched on `get_mut` and only mutated when
the index was valid, swallowing the `None` case. There was no signal
back to the caller.

**Fix.** Change the signature to `Result<(), &'static str>` and use
`get_mut` for safe indexing:

```rust
pub fn mark_done(&mut self, index: usize) -> Result<(), &'static str> {
    match self.items.get_mut(index) {
        Some(t) => { t.done = true; Ok(()) }
        None => Err("todo id out of range"),
    }
}
```

`main` propagates the error with `?`, so the user sees
`error: todo id out of range` instead of a silent success.

### Issue 10 — `remove` panicked on an out-of-range index

**Symptom.** `todo remove 99` panicked via `Vec::remove`.

**Root cause.** `Vec::remove(index)` panics when
`index >= self.items.len()`.

**Fix.** Explicit bounds check returning a `Result`:

```rust
pub fn remove(&mut self, index: usize) -> Result<(), &'static str> {
    if index >= self.items.len() {
        return Err("todo id out of range");
    }
    self.items.remove(index);
    Ok(())
}
```

## 3. Make behaviour correct

### Issue 5 — `filter Buy` did not match a stored todo `buy milk`

**Symptom.** Case-sensitive substring search.

**Root cause.** `t.title.contains(needle)` is a byte-level,
case-sensitive comparison.

**Fix.** Lowercase both sides before comparing:

```rust
let needle = needle.to_lowercase();
self.items
    .iter()
    .filter(|t| t.title.to_lowercase().contains(&needle))
    .cloned()
    .collect()
```

### Issue 6 — `clear` worked in memory but the next `list` showed everything

**Symptom.** The on-disk file was unchanged after `clear`, so the next
run loaded the old data back.

**Root cause.** `clear` emptied `list.items` but never called
`list.save()`.

**Fix.** Call `list.save()?` after clearing. Disk errors now propagate
through `?` and surface to the user instead of being silently dropped.

### Issue 7 — Every todo had `id = 0`

**Symptom.** All todos reported the same id, so the
`[index] [mark] #id - title` output was ambiguous and any logic that
matched on id would collide.

**Root cause.** `Todo::new` was hard-coding `id: 0` for every todo.

**Fix.** `Todo::new` now takes the id as a parameter and stores it
verbatim. The id is supplied by `TodoList::add`, which is the single
authority on id allocation (see Issue 8).

### Issue 8 — `TodoList::next_id` was never incremented

**Symptom.** Even with `Todo::new` fixed to accept an id, the counter
was declared but never bumped, so every call to `add` re-issued the
same id.

**Root cause.** `next_id` was a private field with no read or write
sites other than the `Default` initializer.

**Fix.** `add` now reads the current counter, pushes the new todo with
that id, then increments the counter. The field stays private so the
counter can only be advanced through `add`, which guarantees uniqueness
within a single process:

```rust
pub fn add(&mut self, title: String) -> u32 {
    let id = self.next_id;
    self.next_id += 1;
    self.items.push(Todo::new(id, title));
    id
}
```

> **Residual risk:** ids are process-local. After restarting the app,
> `next_id` is reset to `0` by `Default`, so new todos start again at
> `0` and could collide with previously persisted ids. Reusing ids across
> restarts is acceptable for this CLI; persisting the counter would be
> the next step if id stability across runs ever matters.

### Issue 11 — `filter ""` returned every todo

**Symptom.** `todo filter ""` produced the full list instead of an
empty result.

**Root cause.** An empty needle matches every string under `contains`.

**Fix.** Short-circuit before doing any work:

```rust
if needle.is_empty() {
    return Vec::new();
}
```

## 4. Make persistence robust

### Issue 12 — Data was written to a hidden OS app-data folder

**Symptom.** `todos.json` lived somewhere like
`~/.local/share/.../todos.json`, awkward to find, inspect, and back up.

**Root cause.** `dirs::data_dir()` (or similar) places the file in a
per-OS app-data folder.

**Fix.** Use a project-local `./data` directory. The path is now
`./data/todos.json`, which is:

- next to the source, easy to find;
- already covered by `.gitignore` (`/data`), so it won't be committed;
- easy to wipe during testing.

```rust
fn data_path() -> PathBuf {
    PathBuf::from("./data").join(FILE_NAME)
}
```

`save` also calls `fs::create_dir_all(parent)` so a fresh checkout
"just works" without manual `mkdir`.

### Issue 13 — A corrupt `todos.json` was overwritten on next save

**Symptom.** A single bad write or a hand-edited file silently
destroyed the user's data on the next `save`.

**Root cause.** When `serde_json::from_str` failed, the code returned
an empty `TodoList::new()`. The next `save` then wrote the empty list
on top of the corrupt file, **destroying the original data** with no
way to recover it.

**Fix.** When parsing fails, copy the raw bytes to
`./data/todos.json.bak` before returning an empty list. The user (or a
developer) can then inspect or restore the corrupt file. The backup is
a best-effort write — if it also fails, we still fall back to an empty
list rather than crashing on startup:

```rust
Err(_) => {
    let _ = fs::write(backup_path(), raw);
    TodoList::new()
}
```

### Issue 14 — Disk/permission errors during `save` were swallowed

**Symptom.** A full disk, a permission-denied file, or a read-only
filesystem silently failed, and the in-memory list diverged from what
was on disk.

**Root cause.** `save` returned `()`, so callers couldn't tell
success from failure.

**Fix.** `save` now returns `io::Result<()>` and explicitly maps the
`serde_json` error into an `io::Error` so the caller only has to deal
with one error type:

```rust
pub fn save(&self) -> io::Result<()> {
    let path = data_path();
    let json = serde_json::to_string_pretty(self)
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&path, json)
}
```

`main` propagates every `save()` call with `?`, so a disk error becomes
a non-zero exit code and a printed error message instead of a silent
success.

## Residual risks / known limitations

| Risk | Mitigation |
|---|---|
| `next_id` is process-local; ids are not stable across restarts. | Documented in the `add` function and in this file. Persisting the counter would resolve it. |
| Corrupt-file backup is best-effort (`let _ = fs::write(...)`). | Intentional: a backup failure should not prevent the app from starting. |
| `dirs` is no longer used but remains in `Cargo.toml` as a transitive-or-direct dependency. | Could be removed in a follow-up cleanup PR. |

## Summary

| Area | Issues fixed | Result |
|---|---|---|
| Compile & run | 1, 2 | `add` stores the real title; `list` is empty-safe. |
| Safe commands | 3, 4, 9, 10 | `done` / `remove` validate input and return clear errors. |
| Correct behaviour | 5, 6, 7, 8, 11 | Case-insensitive `filter`, `clear` persists, ids unique. |
| Robust persistence | 12, 13, 14 | Local data file, corrupt-file backup, surfaced I/O errors. |
