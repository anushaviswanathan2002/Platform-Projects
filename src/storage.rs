use std::fs;
use std::io;
use std::path::PathBuf;

use crate::todo::TodoList;

const FILE_NAME: &str = "todos.json";
const BACKUP_NAME: &str = "todos.json.bak";

// Issue 12 fix: store data next to the project (`./data/todos.json`) so it's
// easy to find, inspect, and back up. The `./data` directory is covered by
// `.gitignore`.
fn data_path() -> PathBuf {
    PathBuf::from("./data").join(FILE_NAME)
}

fn backup_path() -> PathBuf {
    PathBuf::from("./data").join(BACKUP_NAME)
}

impl TodoList {
    pub fn load() -> Self {
        let path = data_path();
        let raw = match fs::read_to_string(&path) {
            Ok(s) => s,
            Err(_) => return TodoList::new(),
        };
        match serde_json::from_str(&raw) {
            Ok(list) => list,
            // Issue 13 fix: when the on-disk file is corrupt, back it up to
            // `todos.json.bak` before returning an empty list, so the user's
            // data isn't silently destroyed on the next save.
            Err(_) => {
                let _ = fs::write(backup_path(), raw);
                TodoList::new()
            }
        }
    }

    // Issue 14 fix: surface disk/serialization errors to the caller instead
    // of swallowing them. We map the serde error into an `io::Error` so the
    // caller only has to deal with one error type.
    pub fn save(&self) -> io::Result<()> {
        let path = data_path();
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&path, json)
    }
}
