# Fixes index — quick reference

A one-page summary of the 14 fixes, designed for scanning. For the
full per-issue write-up see [`FIXES.md`](./FIXES.md).

## Matrix

| # | Phase | File | Symbol | One-line fix | Test |
|---|---|---|---|---|---|
| 1 | Compile & run | `src/main.rs` | `run` (`"add"` arm) | Guard `args.len() < 3`; join `args[2..]`. | [T1](./TESTING.md#issue-1--add-stores-the-literal-word-add) |
| 2 | Compile & run | `src/main.rs` | `run` (`"list"` arm) | Use `0..list.len()` instead of `0..list.len() - 1`. | [T2](./TESTING.md#issue-2--list-panics-on-an-empty-list) |
| 3 | Safe commands | `src/main.rs` | `parse_index` (new) | Helper that maps missing/non-numeric id to `Result`. | [T3](./TESTING.md#issue-3--done-panics-on-missing-or-non-numeric-id) |
| 4 | Safe commands | `src/main.rs` | `run` (`"remove"` arm) | Reuse `parse_index`; bounds-check via `TodoList::remove`. | [T4](./TESTING.md#issue-4--remove-panics-on-missing-or-non-numeric-id) |
| 5 | Correct behaviour | `src/todo.rs` | `TodoList::filter` | Lowercase both sides before `contains`. | [T5](./TESTING.md#issue-5--filter-is-case-sensitive) |
| 6 | Correct behaviour | `src/main.rs` | `run` (`"clear"` arm) | Call `list.save()?` after clearing. | [T6](./TESTING.md#issue-6--clear-does-not-persist) |
| 7 | Correct behaviour | `src/todo.rs` | `Todo::new` | Take `id` as a parameter instead of hard-coding `0`. | [T7](./TESTING.md#issue-7--every-todo-has-id--0) |
| 8 | Correct behaviour | `src/todo.rs` | `TodoList::add` | Read `next_id`, push, then increment. | [T8](./TESTING.md#issue-8--next_id-is-never-incremented) |
| 9 | Safe commands | `src/todo.rs` | `TodoList::mark_done` | Return `Result<(), &'static str>`; use `get_mut`. | [T9](./TESTING.md#issue-9--mark_done-silently-does-nothing-on-bad-index) |
| 10 | Safe commands | `src/todo.rs` | `TodoList::remove` | Explicit bounds check returning `Result`. | [T10](./TESTING.md#issue-10--remove-panics-on-out-of-range-index) |
| 11 | Correct behaviour | `src/todo.rs` | `TodoList::filter` | Short-circuit on empty needle. | [T11](./TESTING.md#issue-11--filter--returns-every-todo) |
| 12 | Robust persistence | `src/storage.rs` | `data_path` | Use `./data/todos.json` instead of `dirs::data_dir()`. | [T12](./TESTING.md#issue-12--data-goes-to-a-hidden-os-folder) |
| 13 | Robust persistence | `src/storage.rs` | `TodoList::load` | On parse failure, write `todos.json.bak` then return empty. | [T13](./TESTING.md#issue-13--corrupt-todosjson-is-overwritten) |
| 14 | Robust persistence | `src/storage.rs` | `TodoList::save` | Return `io::Result<()>`; map `serde_json::Error` into `io::Error`. | [T14](./TESTING.md#issue-14--diskpermission-errors-during-save-are-swallowed) |

## Symbol-level diff summary

```text
src/main.rs
  + fn parse_index(args: &[String], cmd: &str) -> Result<usize, Box<dyn Error>>
  ~ run() returns Result<(), Box<dyn Error>> instead of ()
  ~ "add"      arm: require args.len() >= 3; join args[2..]
  ~ "list|ls"  arm: iterate 0..list.len()
  ~ "done"     arm: parse_index + list.mark_done + list.save?
  ~ "remove|rm" arm: parse_index + list.remove    + list.save?
  ~ "filter"   arm: require args.len() >= 3
  ~ "clear"    arm: call list.save()? after clear

src/todo.rs
  ~ Todo::new(id: u32, title: String) takes id from caller
  ~ TodoList::add reads next_id, pushes, then increments; returns id
  ~ TodoList::mark_done returns Result<(), &'static str>
  ~ TodoList::remove    returns Result<(), &'static str>; bounds-checked
  ~ TodoList::filter    case-insensitive; short-circuits on empty needle

src/storage.rs
  ~ data_path()           uses ./data/todos.json
  + backup_path()         new helper
  ~ TodoList::load        backs up corrupt file to todos.json.bak
  ~ TodoList::save        returns io::Result<()>; maps serde error into io::Error
```

## Reading order

If you have not seen this codebase before, read in this order:

1. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — runtime structure of the
   post-fix code.
2. [`FIXES.md`](./FIXES.md) — per-issue fix write-up (the long form of
   this index).
3. [`TESTING.md`](./TESTING.md) — manual test matrix, one shell
   sequence per issue.
4. `../KNOWN_ISSUES.md` — the original bug list, for historical
   reference.

## Phases at a glance

| Phase | Goal | Issues |
|---|---|---|
| 1. Compile & run | Get the binary usable at all | 1, 2 |
| 2. Safe commands | Stop panicking on bad input | 3, 4, 9, 10 |
| 3. Correct behaviour | Make commands do the right thing | 5, 6, 7, 8, 11 |
| 4. Robust persistence | Don't lose or hide data | 12, 13, 14 |
