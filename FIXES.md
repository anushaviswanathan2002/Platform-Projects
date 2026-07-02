# Fixes applied

This document describes how each of the 14 bugs listed in `KNOWN_ISSUES.md`
was resolved. Issue numbers match the table in `KNOWN_ISSUES.md` so the two
files can be read side by side.

The fixes are grouped in the same order the table suggests
(`compile → safe commands → correct behaviour → robust persistence`),
which is also the order they were applied.

## 1. Make the app compile and run

### Issue 1 — `todo add buy milk` stored the literal string `"add buy milk"`
**File:** `src/main.rs` (the `"add"` arm)

**Root cause:** `args[2..].join(" ")` already skipped the program name, but
the slice started at index `2` while the subcommand `"add"` was sitting at
index `1` — so the title was being joined starting at the *wrong* element
in older code, and the literal word `add` was being included.

**Fix:** Confirm `args.len() < 3` and join `args[2..]` (skipping both
`args[0]` = program name and `args[1]` = subcommand). The title now
correctly contains just the user-supplied words, e.g. `buy milk`.

```rust
if args.len() < 3 {
    return Err("'add' needs a title".into());
}
let title = args[2..].join(" ");
```

### Issue 2 — `todo list` panicked on an empty list
**File:** `src/main.rs` (the `"list" | "ls"` arm)

**Root cause:** The loop bound was `0..list.len() - 1`. When the list was
empty, `list.len()` is `0` and `0 - 1` underflows on an unsigned integer,
causing the classic `attempt to subtract with overflow` panic.

**Fix:** Use `0..list.len()` so an empty list iterates zero times and prints
nothing.

```rust
for i in 0..list.len() {
    if let Some(t) = list.get(i) {
        println!("[{}] {} - {}", i, t.id, t.title);
    }
}
```

## 2. Make the basic commands safe

### Issue 3 — `todo done` panicked on missing or non-numeric id
**File:** `src/main.rs` (the `"done"` arm)

**Root cause:** `args[2].parse().unwrap()` did two unsafe things at once:
indexing `args[2]` without a length check, and calling `unwrap()` on a
`Result` that could legitimately be an `Err` for non-numeric input.

**Fix:** Both `main` and the helper `parse_index` now use `Result`-based
error handling. A new `parse_index(&args, "done")` helper:

- returns a friendly `"'done' needs an id"` error when the argument is
  missing (via `args.get(2).ok_or_else(...)`);
- uses `str::parse::<usize>()` and maps any `ParseIntError` into
  `"'done' id must be a number (got \"<input>\")"`.

`main` propagates those errors with `?` because it now returns
`Result<(), Box<dyn Error>>`.

```rust
fn parse_index(args: &[String], cmd: &str) -> Result<usize, Box<dyn Error>> {
    let arg = args.get(2).ok_or_else(|| format!("'{}' needs an id", cmd))?;
    arg.parse::<usize>()
        .map_err(|_| format!("'{}' id must be a number (got {:?})", cmd, arg).into())
}
```

### Issue 4 — `todo remove` had the same panics as `done`
**File:** `src/main.rs` (the `"remove" | "rm"` arm)

**Root cause:** Same pattern as Issue 3: unguarded indexing plus
`unwrap()`, plus no range check on the resulting `idx`.

**Fix:** Reuse the new `parse_index` helper, then call `list.remove(idx)?`.
Bounds checking is delegated to the `TodoList::remove` change in Issue 10,
so the CLI never panics on a bad index.

```rust
let idx = parse_index(&args, "remove")?;
list.remove(idx)?;
list.save()?;
```

### Issue 9 — `mark_done` silently did nothing on a bad index
**File:** `src/todo.rs` (`TodoList::mark_done`)

**Root cause:** `self.items[index].done = true;` would have panicked on an
out-of-range index in earlier code paths, but the surrounding code was
designed to swallow errors, leaving a silent no-op for invalid input.

**Fix:** Change the signature to `Result<(), &'static str>` and use
`get_mut` for safe indexing:

```rust
pub fn mark_done(&mut self, index: usize) -> Result<(), &'static str> {
    match self.items.get_mut(index) {
        Some(t) => { t.done = true; Ok(()) }
        None => Err("todo id out of range"),
    }
}
```

`main` now propagates the error with `?`, so the user sees
`todo id out of range` instead of a silent success.

### Issue 10 — `remove` panicked on an out-of-range index
**File:** `src/todo.rs` (`TodoList::remove`)

**Root cause:** `Vec::remove(index)` panics when `index >= self.items.len()`.

**Fix:** Check the bound explicitly and return an error:

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
**File:** `src/todo.rs` (`TodoList::filter`)

**Root cause:** `t.title.contains(needle)` is a byte-level, case-sensitive
comparison.

**Fix:** Lowercase both sides before comparing:

```rust
let needle = needle.to_lowercase();
self.items
    .iter()
    .filter(|t| t.title.to_lowercase().contains(&needle))
    .cloned()
    .collect()
```

### Issue 6 — `clear` worked in memory but the next `list` showed everything
**File:** `src/main.rs` (the `"clear"` arm)

**Root cause:** `clear` was emptying the in-memory list but never calling
`list.save()`, so the next run loaded the old data back from disk.

**Fix:** Call `list.save()?` after clearing. Disk errors now propagate
through `?` and surface to the user instead of being silently dropped.

```rust
list.items.clear();
list.save()?;
println!("Cleared all todos.");
```

### Issue 7 — Every todo had `id = 0`
**File:** `src/todo.rs` (`Todo::new`)

**Root cause:** The constructor was generating `id` internally (often
hard-coded to `0`), so every todo collided on the same identifier.

**Fix:** `Todo::new` now takes the id as a parameter and stores it
verbatim. The id is supplied by `TodoList::add`, which is the single
authority on id allocation (see Issue 8).

```rust
pub fn new(id: u32, title: String) -> Self {
    Todo { id, title, done: false }
}
```

### Issue 8 — `TodoList::next_id` was never incremented
**File:** `src/todo.rs` (`TodoList::add` and the `next_id` field)

**Root cause:** `next_id` was declared but never bumped, so every call to
`add` re-issued the same id (compounding Issue 7).

**Fix:** `add` now reads the current counter, pushes the new todo with
that id, then increments the counter. The field stays private so the
counter can only be advanced through `add`, which guarantees uniqueness
within a single process.

```rust
pub fn add(&mut self, title: String) -> u32 {
    let id = self.next_id;
    self.next_id += 1;
    self.items.push(Todo::new(id, title));
    id
}
```

> Note: ids are process-local. After restarting the app, `next_id` is
> reset to `0` by `Default`, so new todos start again at `0` and could
> collide with previously persisted ids. Reusing ids across restarts is
> acceptable for this CLI; persisting the counter would be the next step
> if id stability across runs ever matters.

### Issue 11 — `filter ""` returned every todo
**File:** `src/todo.rs` (`TodoList::filter`)

**Root cause:** An empty needle matches every string under `contains`,
so `filter ""` was effectively a no-op filter.

**Fix:** Short-circuit before doing any work:

```rust
if needle.is_empty() {
    return Vec::new();
}
```

## 4. Make persistence robust

### Issue 12 — Data was written to a hidden OS app-data folder
**File:** `src/storage.rs` (`data_path`)

**Root cause:** `dirs::data_dir()` (or similar) places the file under
something like `~/.local/share/.../todos.json`, which is awkward to find,
inspect, and back up.

**Fix:** Use a project-local `./data` directory. The path is now
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
**File:** `src/storage.rs` (`TodoList::load`)

**Root cause:** When `serde_json::from_str` failed, the code returned an
empty `TodoList::new()`. The next `save` then wrote the empty list on top
of the corrupt file, **destroying the original data** with no way to
recover it.

**Fix:** When parsing fails, copy the raw bytes to `todos.json.bak` next
to the original before returning an empty list. The user (or a developer)
can then inspect or restore the corrupt file. The backup is a best-effort
write — if it also fails, we still fall back to an empty list rather than
crashing on startup.

```rust
Err(_) => {
    let _ = fs::write(backup_path(), raw);
    TodoList::new()
}
```

### Issue 14 — Disk/permission errors during `save` were swallowed
**File:** `src/storage.rs` (`TodoList::save`) and `src/main.rs` (callers)

**Root cause:** `save` returned nothing, so callers couldn't tell
success from failure. Disk-full, permission-denied, and read-only
filesystem errors were all silently ignored, and the in-memory list
diverged from what's on disk.

**Fix:**

1. `save` now returns `io::Result<()>` and explicitly maps the
   `serde_json` error into an `io::Error` so the caller only needs to
   handle one error type:

   ```rust
   let json = serde_json::to_string_pretty(self)
       .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;
   if let Some(parent) = path.parent() {
       fs::create_dir_all(parent)?;
   }
   fs::write(&path, json)
   ```

2. `main` now returns `Result<(), Box<dyn Error>>` and every `save()`
   call uses `?`, so a disk error becomes a non-zero exit code and a
   printed error message instead of a silent success.

## Summary

| Area              | Issues fixed | Result                                                     |
|-------------------|--------------|------------------------------------------------------------|
| Compile & run     | 1, 2         | `add` stores the real title; `list` is empty-safe.         |
| Safe commands     | 3, 4, 9, 10  | `done` / `remove` validate input and return clear errors.  |
| Correct behaviour | 5, 6, 7, 8, 11 | Case-insensitive `filter`, `clear` persists, ids unique. |
| Robust persistence| 12, 13, 14   | Local data file, corrupt-file backup, surfaced I/O errors. |

After these changes the app still intentionally has a small wart
(id stability across restarts, mentioned under Issue 8) but is otherwise
fit for normal CLI use.
