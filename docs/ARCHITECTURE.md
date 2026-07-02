# Architecture

A small Rust CLI that stores a JSON-serialised todo list on disk. This
document describes the runtime structure of the post-fix code.

## Module layout

```
src/
├── main.rs     # CLI parsing, error propagation
├── todo.rs     # Todo / TodoList types, in-memory operations
└── storage.rs  # JSON load / save, project-local data directory
```

The dependency graph is acyclic: `main` depends on `todo` and `storage`,
and `storage` depends on `todo`. There is no global state — every command
loads the list, mutates it in memory, and saves it before returning.

## Data model

```rust
pub struct Todo {
    pub id: u32,        // unique within a process; assigned by TodoList::add
    pub title: String,
    pub done: bool,
}

pub struct TodoList {
    pub items: Vec<Todo>,
    next_id: u32,       // private; bumped inside TodoList::add
}
```

### Invariants

1. `items` is the only source of truth for stored todos.
2. `next_id` is **process-local**; it is reset to `0` on every restart by
   `Default`. ids are therefore only guaranteed unique within a single
   process. Persisting the counter would extend uniqueness across restarts
   and is the obvious next step if id stability across runs ever matters.
3. `Todo::new` accepts an id from the caller; it does not invent one. This
   keeps id allocation in exactly one place (`TodoList::add`), which is
   the reason id collisions are now impossible.
4. All mutating operations on `TodoList` either return `Result<(), &'static str>`
   (`mark_done`, `remove`) or a typed value (`add` returns the assigned id).
   They never panic on bad input.

## Storage flow

```
run() ──► TodoList::load() ──► mutate ──► TodoList::save() ──► stdout
```

`load` and `save` are the only two functions in `storage.rs`.

### `load`

1. Read `./data/todos.json`. If the file is missing, return an empty list.
2. Parse the JSON.
   - On success: return the parsed list.
   - On failure: copy the raw bytes to `./data/todos.json.bak` (best effort)
     and return an empty list. The `.bak` file lets a developer recover the
     original data instead of having it silently overwritten by the next
     save.

### `save`

1. Serialise the list to pretty JSON.
2. `fs::create_dir_all` the parent directory so a fresh checkout works
   without manual `mkdir`.
3. `fs::write` the JSON to `./data/todos.json`.
4. Return `io::Result<()>`. Serialization errors are mapped into
   `io::Error` so the caller only has to deal with one error type.

## Error-propagation contract

`main` is a thin wrapper around `run()`, which returns
`Result<(), Box<dyn Error>>`. Every command arm that can fail uses `?`,
and `main` prints `error: <message>` to stderr and exits with code `1`
on failure. Happy paths exit `0`.

The user-visible error contract is:

| Condition | Message | Exit |
|---|---|---|
| `add` with no title | `'add' needs a title` | 1 |
| `done` / `remove` with no id | `'done' needs an id` / `'remove' needs an id` | 1 |
| `done` / `remove` with non-numeric id | `'<cmd>' id must be a number (got "...")` | 1 |
| `done` / `remove` with out-of-range id | `todo id out of range` | 1 |
| `filter` with no needle | `'filter' needs a needle` | 1 |
| Disk error during save | underlying `io::Error` (e.g. `Permission denied (os error 13)`) | 1 |

No command path panics on user input.
