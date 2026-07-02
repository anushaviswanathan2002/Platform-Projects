# Known issues (seeded on purpose)

These are real bugs planted in the app so you can practise fixing them.
Each entry names the file, the symptom, and a hint.

| #  | File           | Symptom                                                                 | Hint                                                                 |
|----|----------------|-------------------------------------------------------------------------|----------------------------------------------------------------------|
| 1  | `src/main.rs`  | `todo add buy milk` stores the literal string `"add buy milk"`.         | Skip `args[1]` when joining.                                         |
| 2  | `src/main.rs`  | `todo list` panics with "attempt to subtract with overflow" on an empty list. | Replace `0..list.len() - 1` with `0..list.len()`.                    |
| 3  | `src/main.rs`  | `todo done` panics if you forget the id, or type something non-numeric. | Guard `args.len()` and use a fallible parse with a friendly error.  |
| 4  | `src/main.rs`  | `todo remove` has the same panics as `done` and also panics on out-of-range. | Validate `idx < list.len()`.                                         |
| 5  | `src/todo.rs`  | `todo filter Buy` doesn't match a stored todo `buy milk`.               | Lowercase both sides before comparing.                               |
| 6  | `src/main.rs`  | `todo clear` looks like it works, but the next `list` shows everything.  | Call `list.save()` after clearing.                                   |
| 7  | `src/todo.rs`  | Every todo has `id = 0`, so they all collide.                           | Generate a unique id per todo (e.g. use the list's `next_id` counter). |
| 8  | `src/todo.rs`  | `TodoList::next_id` is never incremented.                               | Bump it inside `add`.                                                |
| 9  | `src/todo.rs`  | `mark_done` silently does nothing on bad index.                         | Return `Result<(), &'static str>` and bubble it up in `main`.        |
| 10 | `src/todo.rs`  | `remove` panics on out-of-range index.                                  | Return `Result` and check bounds in `main`.                          |
| 11 | `src/todo.rs`  | `filter ""` returns every todo instead of none.                         | Short-circuit when `needle` is empty.                                |
| 12 | `src/storage.rs`| Todos are written to a hidden OS app-data folder that's hard to find.  | Write next to the project (e.g. `./data/todos.json`).                |
| 13 | `src/storage.rs`| A corrupt `todos.json` is overwritten on next save → data loss.        | Back the file up (`.bak`) before replacing it when parse fails.      |
| 14 | `src/storage.rs`| Disk/permission errors during save are swallowed.                      | Propagate the `io::Result` and print a clear error in `main`.        |

## Suggested fix order

1. Make the app **compile and run** (issues 1, 2).
2. Make the basic commands **safe** (3, 4, 9, 10).
3. Make behaviour **correct** (5, 6, 7, 8, 11).
4. Make persistence **robust** (12, 13, 14).
