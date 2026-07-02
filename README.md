# todo_app (testing version)

A small Rust CLI todo app. **This version intentionally contains bugs.**
It exists so you can practice the workflow of:

1. Installing the project (`cargo build`).
2. Reproducing the bugs by running the binary.
3. Fixing them, then re-running.

See `KNOWN_ISSUES.md` for the full list of seeded bugs and hints.

## Build

```bash
cargo build
```

## Run

```bash
cargo run -- add "Buy milk"
cargo run -- list
cargo run -- done 0
cargo run -- remove 0
cargo run -- filter buy
cargo run -- clear
```

## Project layout

```
.
├── Cargo.toml
├── KNOWN_ISSUES.md
├── README.md
└── src
    ├── main.rs     # CLI parsing
    ├── todo.rs     # Todo / TodoList types
    └── storage.rs  # JSON load/save
```
