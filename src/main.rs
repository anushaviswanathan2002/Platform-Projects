mod todo;
mod storage;

use std::env;
use std::error::Error;

use todo::TodoList;

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {}", e);
        std::process::exit(1);
    }
}

// `run` returns Result so all error paths use `?` and surface a non-zero
// exit code with a printed message instead of panicking.
fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_usage();
        return Ok(());
    }

    let mut list = TodoList::load();

    match args[1].as_str() {
        "add" => {
            // Issue 1 fix: require at least one word of title beyond the
            // subcommand, and join `args[2..]` so the literal word "add"
            // is excluded.
            if args.len() < 3 {
                return Err("'add' needs a title".into());
            }
            let title = args[2..].join(" ");
            let id = list.add(title);
            list.save()?;
            println!("Added todo #{}", id);
        }
        "list" | "ls" => {
            // Issue 2 fix: iterate `0..list.len()` (no underflow on empty).
            for i in 0..list.len() {
                if let Some(t) = list.get(i) {
                    let mark = if t.done { "x" } else { " " };
                    println!("[{}] [{}] #{} - {}", i, mark, t.id, t.title);
                }
            }
        }
        "done" => {
            // Issue 3 fix: use the `parse_index` helper to validate input.
            let idx = parse_index(&args, "done")?;
            list.mark_done(idx)?;
            list.save()?;
            println!("Marked todo #{} as done", idx);
        }
        "remove" | "rm" => {
            // Issue 4 fix: safe parsing plus bounds-checked removal.
            let idx = parse_index(&args, "remove")?;
            list.remove(idx)?;
            list.save()?;
            println!("Removed todo #{}", idx);
        }
        "filter" => {
            // Issue 5 fix is in `TodoList::filter` (case-insensitive).
            if args.len() < 3 {
                return Err("'filter' needs a needle".into());
            }
            let needle = &args[2..].join(" ");
            for t in list.filter(needle) {
                println!("- {}", t.title);
            }
        }
        "clear" => {
            // Issue 6 fix: persist the clear so it survives a restart.
            list.items.clear();
            list.save()?;
            println!("Cleared all todos.");
        }
        "help" | "-h" | "--help" => {
            print_usage();
        }
        other => {
            eprintln!("Unknown command: {}", other);
            print_usage();
        }
    }
    Ok(())
}

// Issue 3/4 helper: parse the id argument with friendly errors for both
// "missing" and "not a number" instead of panicking via `unwrap`.
fn parse_index(args: &[String], cmd: &str) -> Result<usize, Box<dyn Error>> {
    let arg = args
        .get(2)
        .ok_or_else(|| format!("'{}' needs an id", cmd))?;
    arg.parse::<usize>()
        .map_err(|_| format!("'{}' id must be a number (got {:?})", cmd, arg).into())
}

fn print_usage() {
    println!("todo — a small todo CLI");
    println!();
    println!("USAGE:");
    println!("    todo <command> [args]");
    println!();
    println!("COMMANDS:");
    println!("    add <title>      Add a new todo");
    println!("    list | ls        List all todos");
    println!("    done <id>        Mark a todo as done");
    println!("    remove | rm <id> Remove a todo");
    println!("    filter <needle>  Show todos whose title contains <needle>");
    println!("    clear            Remove all todos");
    println!("    help             Show this message");
}
