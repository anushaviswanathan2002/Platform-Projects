mod todo;
mod storage;

use std::env;
use todo::{Todo, TodoList};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_usage();
        return;
    }

    let mut list = TodoList::load();

    match args[1].as_str() {
        "add" => {
            // Issue 1: we slice off the program name but not the subcommand,
            // so the first todo ends up being the literal word "add".
            let title = args[2..].join(" ");
            let item = Todo::new(title);
            list.add(item);
            list.save();
            println!("Added todo #{}", list.len());
        }
        "list" | "ls" => {
            // Issue 2: off-by-one when there are zero items — the loop bound
            // is `list.len() - 1` which underflows on an empty list.
            for i in 0..list.len() - 1 {
                if let Some(t) = list.get(i) {
                    println!("[{}] {} - {}", i, t.id, t.title);
                }
            }
        }
        "done" => {
            // Issue 3: we never check that args[2] actually exists,
            // and we pass it straight to parse without handling the error.
            let idx: usize = args[2].parse().unwrap();
            list.mark_done(idx);
            list.save();
        }
        "remove" | "rm" => {
            // Issue 4: same index parsing hazard as `done`, plus we
            // don't validate the range.
            let idx: usize = args[2].parse().unwrap();
            list.remove(idx);
            list.save();
        }
        "filter" => {
            // Issue 5: filter is case-sensitive, so a search for
            // "Buy" won't match a stored todo of "buy milk".
            let needle = &args[2..].join(" ");
            for t in list.filter(needle) {
                println!("- {}", t.title);
            }
        }
        "clear" => {
            // Issue 6: this wipes the in-memory list but never persists
            // the change, so the next run shows the same todos again.
            list.items.clear();
        }
        "help" | "-h" | "--help" => {
            print_usage();
        }
        other => {
            eprintln!("Unknown command: {}", other);
            print_usage();
        }
    }
}

fn print_usage() {
    println!("todo — a small todo CLI (testing version, has known issues)");
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
