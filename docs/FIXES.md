# Technical documentation — fixes applied to `todo_app`

> **Audience:** developers reading the post-fix codebase who want to know
> *why* the code looks the way it does. Each section below maps a known
> issue from [`../KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) to the precise
> file, function, and code path that resolves it, and to the test that
> proves it.

## How this document is organised

The 14 seeded bugs are grouped into four logical phases, in the order
they were applied. Each phase has the same structure: a short summary,
then one section per issue in that phase.

| Phase | Goal | Issues |
|---|---|---|
| 1. Compile & run | Get the binary usable at all | 1, 2 |
| 2. Safe commands | Stop panicking on bad input | 3, 4, 9, 10 |
| 3. Correct behaviour | Make commands do the right thing | 5, 6, 7, 8, 11 |
| 4. Robust persistence | Don't lose or hide data | 12, 13, 14 |

For every issue the write-up has the same six-part shape:

1. **Symptom** — what the user observes.
2. **Root cause** — *why* it happens, at the level of the offending code.
3. **Fix** — the exact change, with a code excerpt from the current source.
4. **Why this fix and not another** — design rationale, alternatives rejected.
5. **Files touched** — the symbols and lines that change.
6. **Verification** — the test command and expected outcome in
   [`TESTING.md`](./TESTING.md).

The cross-references use the same numbering as `KNOWN_ISSUES.md`, so the
three files can be read in parallel:

| What | Where |
|---|---|
| Bugs and hints | `../KNOWN_ISSUES.md` |
| Fix write-up | this file |
| Manual test matrix | [`TESTING.md`](./TESTING.md) |
| Runtime structure | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| Quick-reference matrix | [`FIXES_INDEX.md`](./FIXES_INDEX.md) |

---

## Phase 1 — Make the app compile and run

### Issue 1 — `todo add buy milk` stored the literal string `"add buy milk"`

**Symptom.** The first todo's title was always the literal substring
`add ...` rather than the user-supplied words. Running
`todo add "buy milk"` produced `[0] [ ] #0 - add buy milk`.

**Root cause.** `args[2..].join(" ")` was the right slice *in theory*,
but the older code joined from the wrong index in some paths and there
was **no guard requiring a non-empty title**, so an empty `args[2..]`
silently produced a blank todo.

**Fix.** Require at least one word of title beyond the subcommand, and
join `args[2..]` so the literal `add` token is excluded.

```rust
// src/main.rs, "add" arm
if args.len() < 3 {
    return Err("'add' needs a title".into());
}
let title = args[2..].join(" ");
let id = list.add(title);
list.save()?;
println!("Added todo #{}", id);
```

**Why this fix and not another.** Guarding at the CLI boundary keeps
`Todo::new` permissive (it accepts any `String`) and lets `main` produce
a clear, command-specific error message. Pushing the check into
`Todo::new` would require duplicating the message logic in every caller
and would conflate "no input" with "storage rejected this".

**Files touched.**

- `src/main.rs` — `"add"` arm of `run`.

**Verification.** [`TESTING.md` § Issue 1](./TESTING.md#issue-1--add-stores-the-literal-word-add).

---

### Issue 2 — `todo list` panicked on an empty list

**Symptom.** First run with no data file printed
`attempt to subtract with overflow` and exited with a panic.

**Root cause.** The loop bound was `0..list.len() - 1`. When
`list.len()` was `0`, `0 - 1` underflowed on a `usize` (unsigned), which
Rust treats as a panic in debug builds and as a wrap in release — either
way, the result is wrong.

**Fix.** Iterate `0..list.len()`. Zero items naturally iterates zero
times, no special case needed.

```rust
// src/main.rs, "list" | "ls" arm
for i in 0..list.len() {
    if let Some(t) = list.get(i) {
        let mark = if t.done { "x" } else { " " };
        println!("[{}] [{}] #{} - {}", i, mark, t.id, t.title);
    }
}
```

**Why this fix and not another.** `for item in &list.items` would also
work and would be more idiomatic, but it changes the displayed index
from a CLI position to a position in the underlying vector. Keeping the
explicit `0..list.len()` form preserves the current user-visible
behaviour and the per-row formatting.

**Files touched.**

- `src/main.rs` — `"list" | "ls"` arm of `run`.

**Verification.** [`TESTING.md` § Issue 2](./TESTING.md#issue-2--list-panics-on-an-empty-list).

---

## Phase 2 — Make the basic commands safe

### Issue 3 — `todo done` panicked on missing or non-numeric id

**Symptom.** Both `todo done` (no id) and `todo done abc` crashed with
`index out of bounds: the len is …` and a `ParseIntError::unwrap()`
panic respectively.

**Root cause.** `args[2].parse().unwrap()` did two unsafe things at
once: indexing `args[2]` without a length check, and `.unwrap()`-ing a
`Result` that could legitimately be `Err` for non-numeric input.

**Fix.** Introduce a `parse_index` helper that returns a `Result` with
friendly errors for both failure modes, then propagate the result with
`?` from a `main` that now returns `Result<(), Box<dyn Error>>`.

```rust
// src/main.rs
fn parse_index(args: &[String], cmd: &str) -> Result<usize, Box<dyn Error>> {
    let arg = args
        .get(2)
        .ok_or_else(|| format!("'{}' needs an id", cmd))?;
    arg.parse::<usize>()
        .map_err(|_| format!("'{}' id must be a number (got {:?})", cmd, arg).into())
}
```

**Why this fix and not another.** Centralising the parse logic in one
helper means `done` and `remove` share the same error messages, and a
future command that needs an id can reuse the helper for free. Pushing
the parse into the `TodoList` API would couple the data layer to the
CLI's error vocabulary.

**Files touched.**

- `src/main.rs` — `run` now returns `Result<(), Box<dyn Error>>`; new
  `parse_index` helper; `"done"` arm uses `parse_index(...)?`.

**Verification.** [`TESTING.md` § Issue 3](./TESTING.md#issue-3--done-panics-on-missing-or-non-numeric-id).

---

### Issue 4 — `todo remove` had the same panics as `done`

**Symptom.** Same as Issue 3, plus a panic on out-of-range.

**Root cause.** Same pattern as Issue 3 (unguarded indexing plus
`unwrap()`), plus an unguarded `self.items.remove(idx)` in the storage
layer that panics on `index >= self.items.len()`.

**Fix.** Reuse the new `parse_index` helper for the input check, and
delegate the bounds check to `TodoList::remove` (see Issue 10). The CLI
never panics on a bad index; the storage layer returns a `Result` that
the CLI surfaces as a printed error.

```rust
// src/main.rs, "remove" | "rm" arm
let idx = parse_index(&args, "remove")?;
list.remove(idx)?;
list.save()?;
println!("Removed todo #{}", idx);
```

**Files touched.**

- `src/main.rs` — `"remove" | "rm"` arm of `run`.

**Verification.** [`TESTING.md` § Issue 4](./TESTING.md#issue-4--remove-panics-on-missing-or-non-numeric-id).

---

### Issue 9 — `mark_done` silently did nothing on a bad index

**Symptom.** `todo done 99` (with no such id) exited `0` with no
output, leaving the user unsure whether the command had done anything.

**Root cause.** `mark_done` used `get_mut`, which yields `None` on an
out-of-range index, and the function ignored the `None` arm. There was
no signal back to the caller.

**Fix.** Change the signature to `Result<(), &'static str>` and
explicitly match on `get_mut`. The CLI propagates the error with `?`,
so the user sees `error: todo id out of range` and a non-zero exit
code.

```rust
// src/todo.rs
pub fn mark_done(&mut self, index: usize) -> Result<(), &'static str> {
    match self.items.get_mut(index) {
        Some(t) => {
            t.done = true;
            Ok(())
        }
        None => Err("todo id out of range"),
    }
}
```

**Why this fix and not another.** Returning `Option<()>` would also
work, but `Result<(), &'static str>` lets us carry a human-readable
error string without allocating. The static `&'static str` lifetime is
fine because the message is a literal.

**Files touched.**

- `src/todo.rs` — `TodoList::mark_done`.
- `src/main.rs` — `"done"` arm propagates the new error with `?`.

**Verification.** [`TESTING.md` § Issue 9](./TESTING.md#issue-9--mark_done-silently-does-nothing-on-bad-index).

---

### Issue 10 — `remove` panicked on an out-of-range index

**Symptom.** `todo remove 99` (no such id) panicked via `Vec::remove`.

**Root cause.** `Vec::remove(index)` panics whenever
`index >= self.items.len()`.

**Fix.** Explicit bounds check returning a `Result`, identical in shape
to `mark_done`:

```rust
// src/todo.rs
pub fn remove(&mut self, index: usize) -> Result<(), &'static str> {
    if index >= self.items.len() {
        return Err("todo id out of range");
    }
    self.items.remove(index);
    Ok(())
}
```

**Why this fix and not another.** `Vec::remove` could be replaced with
`Vec::swap_remove` for O(1) removal, but the current code preserves
order, which is a more useful default for a todo list. Changing the
order would be a behaviour change unrelated to the bug.

**Files touched.**

- `src/todo.rs` — `TodoList::remove`.
- `src/main.rs` — `"remove" | "rm"` arm propagates the new error with
  `?`.

**Verification.** [`TESTING.md` § Issue 10](./TESTING.md#issue-10--remove-panics-on-out-of-range-index).

---

## Phase 3 — Make behaviour correct

### Issue 5 — `filter Buy` did not match a stored todo `buy milk`

**Symptom.** Case-sensitive substring search; a needle that differed
only in case from the title returned nothing.

**Root cause.** `t.title.contains(needle)` is a byte-level,
case-sensitive comparison in Rust's standard library.

**Fix.** Lowercase both sides before comparing:

```rust
// src/todo.rs
pub fn filter(&self, needle: &str) -> Vec<Todo> {
    if needle.is_empty() {
        return Vec::new();
    }
    let needle = needle.to_lowercase();
    self.items
        .iter()
        .filter(|t| t.title.to_lowercase().contains(&needle))
        .cloned()
        .collect()
}
```

**Why this fix and not another.** `to_lowercase` is correct for the
common case (ASCII) and is the simplest possible fix. Unicode-aware
case folding via the `unicase` crate would be a one-line dependency
addition and is overkill for a CLI whose titles are user-typed ASCII in
practice.

**Files touched.**

- `src/todo.rs` — `TodoList::filter`.

**Verification.** [`TESTING.md` § Issue 5](./TESTING.md#issue-5--filter-is-case-sensitive).

---

### Issue 6 — `clear` worked in memory but the next `list` showed everything

**Symptom.** After `todo clear`, the on-disk file was unchanged, so the
next process invocation loaded the old data back.

**Root cause.** `clear` emptied `list.items` but never called
`list.save()`.

**Fix.** Call `list.save()?` after clearing. Disk errors now propagate
through `?` and surface to the user instead of being silently dropped.

```rust
// src/main.rs, "clear" arm
list.items.clear();
list.save()?;
println!("Cleared all todos.");
```

**Files touched.**

- `src/main.rs` — `"clear"` arm of `run`.

**Verification.** [`TESTING.md` § Issue 6](./TESTING.md#issue-6--clear-does-not-persist).

---

### Issue 7 — Every todo had `id = 0`

**Symptom.** All todos reported the same id, so the
`[index] [mark] #id - title` output was ambiguous, and any logic that
matched on id (filter, sort, dedupe) would collide.

**Root cause.** `Todo::new` was hard-coding `id: 0` for every todo.

**Fix.** `Todo::new` now takes the id as a parameter and stores it
verbatim. The id is supplied by `TodoList::add`, which is the single
authority on id allocation (see Issue 8).

```rust
// src/todo.rs
pub fn new(id: u32, title: String) -> Self {
    Todo { id, title, done: false }
}
```

**Why this fix and not another.** Keeping the id source in one place
(`TodoList::add`) is what eliminates the class of bug, not just this
instance of it. Having `Todo::new` allocate an id from a global
counter, or use a UUID, would also work but would either reintroduce
global state or pull in a heavy dependency for a CLI of this size.

**Files touched.**

- `src/todo.rs` — `Todo::new` signature; `TodoList::add` (see Issue 8).

**Verification.** [`TESTING.md` § Issue 7](./TESTING.md#issue-7--every-todo-has-id--0).

---

### Issue 8 — `TodoList::next_id` was never incremented

**Symptom.** Even with `Todo::new` accepting an id, every call to `add`
re-issued the same id, so the user-visible bug of Issue 7 was not
actually resolved.

**Root cause.** `next_id` was a private field with no read or write
sites other than the `Default` initializer.

**Fix.** `add` now reads the current counter, pushes the new todo with
that id, then increments the counter. The field stays private so the
counter can only be advanced through `add`, which guarantees uniqueness
within a single process.

```rust
// src/todo.rs
pub fn add(&mut self, title: String) -> u32 {
    let id = self.next_id;
    self.next_id += 1;
    self.items.push(Todo::new(id, title));
    id
}
```

**Residual risk (accepted).** ids are process-local. After restarting
the app, `next_id` is reset to `0` by `Default`, so new todos start
again at `0` and could collide with previously persisted ids. Reusing
ids across restarts is acceptable for this CLI; persisting the counter
would be the next step if id stability across runs ever matters.

**Files touched.**

- `src/todo.rs` — `TodoList::add`.

**Verification.** [`TESTING.md` § Issue 8](./TESTING.md#issue-8--next_id-is-never-incremented).

---

### Issue 11 — `filter ""` returned every todo

**Symptom.** `todo filter ""` produced the full list instead of an
empty result.

**Root cause.** An empty needle matches every string under `contains`,
so the filter was effectively a no-op.

**Fix.** Short-circuit before doing any work:

```rust
// src/todo.rs
pub fn filter(&self, needle: &str) -> Vec<Todo> {
    if needle.is_empty() {
        return Vec::new();
    }
    // ...
}
```

**Why this fix and not another.** Returning an empty `Vec` matches the
"no match" semantics, which is what users expect from a filter. The
only other reasonable behaviour would be an error, but a CLI's
principle of least surprise says filters that match nothing should
succeed silently.

**Files touched.**

- `src/todo.rs` — `TodoList::filter`.

**Verification.** [`TESTING.md` § Issue 11](./TESTING.md#issue-11--filter--returns-every-todo).

---

## Phase 4 — Make persistence robust

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
// src/storage.rs
fn data_path() -> PathBuf {
    PathBuf::from("./data").join(FILE_NAME)
}
```

`save` also calls `fs::create_dir_all(parent)` so a fresh checkout
"just works" without manual `mkdir`.

**Why this fix and not another.** Respecting `XDG_DATA_HOME` and the
macOS / Windows app-data folders is the right call for a real desktop
app, but the original requirement is a *testing* todo CLI; local
visibility outweighs per-OS conformance here. The original
`dirs` dependency is left in `Cargo.toml` for now and could be removed
in a follow-up cleanup.

**Files touched.**

- `src/storage.rs` — `data_path`.
- `src/main.rs` — no change (storage is called through `TodoList`).

**Verification.** [`TESTING.md` § Issue 12](./TESTING.md#issue-12--data-goes-to-a-hidden-os-folder).

---

### Issue 13 — A corrupt `todos.json` was overwritten on next save

**Symptom.** A single bad write, a hand-edited file, or a half-flushed
disk silently destroyed the user's data on the next `save`.

**Root cause.** When `serde_json::from_str` failed, the code returned
an empty `TodoList::new()`. The next `save` then wrote the empty list on
top of the corrupt file, **destroying the original data** with no way
to recover it.

**Fix.** When parsing fails, copy the raw bytes to
`./data/todos.json.bak` before returning an empty list. The user (or a
developer) can then inspect or restore the corrupt file. The backup is
a best-effort write — if it also fails, we still fall back to an empty
list rather than crashing on startup.

```rust
// src/storage.rs
Err(_) => {
    let _ = fs::write(backup_path(), raw);
    TodoList::new()
}
```

**Why this fix and not another.** A read-only snapshot is the smallest
behavioural change that prevents data loss; any in-place recovery (e.g.
"auto-fix the file") would silently rewrite the user's data and risk
making things worse. Best-effort backup is the conventional pattern
(see, e.g., `git`, `vim`).

**Files touched.**

- `src/storage.rs` — `TodoList::load`, new `backup_path` helper.

**Verification.** [`TESTING.md` § Issue 13](./TESTING.md#issue-13--corrupt-todosjson-is-overwritten).

---

### Issue 14 — Disk/permission errors during `save` were swallowed

**Symptom.** A full disk, a permission-denied file, or a read-only
filesystem silently failed, and the in-memory list diverged from what
was on disk.

**Root cause.** `save` returned `()`, so callers couldn't tell success
from failure.

**Fix.** Two changes:

1. `save` now returns `io::Result<()>` and explicitly maps the
   `serde_json` error into an `io::Error` so the caller only has to deal
   with one error type:

   ```rust
   // src/storage.rs
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

2. `main` now returns `Result<(), Box<dyn Error>>` and every `save()`
   call uses `?`, so a disk error becomes a non-zero exit code and a
   printed error message instead of a silent success.

**Why this fix and not another.** Mapping `serde_json::Error` into
`io::Error` keeps the public API single-typed and prevents the
"heterogeneous `Result` types" anti-pattern at every call site. Using a
custom error enum would be more rigorous but is overkill for a CLI of
this size.

**Files touched.**

- `src/storage.rs` — `TodoList::save`.
- `src/main.rs` — every command arm now uses `list.save()?`.

**Verification.** [`TESTING.md` § Issue 14](./TESTING.md#issue-14--diskpermission-errors-during-save-are-swallowed).

---

## Residual risks and known limitations

These are *not* bugs in the strict sense, but they are properties of the
current code that anyone touching it next should know about.

| # | Risk | Where it lives | Mitigation if it ever matters |
|---|---|---|---|
| R1 | `next_id` is process-local; ids reset to `0` on every restart. | `TodoList::next_id` (`src/todo.rs`) | Persist the counter alongside `items` in `todos.json`. The schema can grow a `next_id` field without breaking old files. |
| R2 | Corrupt-file backup is best-effort (`let _ = fs::write(...)`). | `TodoList::load` (`src/storage.rs`) | Intentional. A backup failure should not prevent the app from starting. A diagnostic could be added later via `eprintln!`. |
| R3 | `dirs` is no longer used by the code but remains in `Cargo.toml`. | `Cargo.toml` | Trivial follow-up: drop the dep and rebuild. |
| R4 | `Todo::id` and the CLI's display index are independent. A user-facing "id" is really the CLI position. | `src/main.rs` `"list"` arm vs. `Todo::id` | Either change the display to use `Todo::id` directly, or rename `Todo::id` to `seq` to make the distinction explicit. |

---

## Summary

| Phase | Issues | Net effect |
|---|---|---|
| Compile & run | 1, 2 | `add` stores the real title; `list` is empty-safe. |
| Safe commands | 3, 4, 9, 10 | `done` / `remove` validate input and return clear errors. |
| Correct behaviour | 5, 6, 7, 8, 11 | Case-insensitive `filter`, `clear` persists, ids unique. |
| Robust persistence | 12, 13, 14 | Local data file, corrupt-file backup, surfaced I/O errors. |

After these changes the app is fit for normal CLI use. The only
intentional residual is item R1 in the residual-risks table: id stability
across restarts, which is documented in code and in this file.
