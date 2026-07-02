use std::fs;
use std::path::PathBuf;

use crate::todo::TodoList;

const FILE_NAME: &str = "todos.json";

fn data_path() -> PathBuf {
    // Issue 12: using dirs::data_dir() puts the file in a per-OS app-data
    // folder (e.g. ~/.local/share on Linux). That's a real, but hidden,
    // location — beginners won't find it. Use a project-local path instead.
    if let Some(mut p) = dirs::data_dir() {
        p.push(FILE_NAME);
        return p;
    }
    PathBuf::from(FILE_NAME)
}

impl TodoList {
    pub fn load() -> Self {
        let path = data_path();
        // Issue 13: we return an empty list if the file is missing *or*
        // if it fails to parse — so a corrupted todos.json silently
        // destroys the user's data on next save.
        let raw = match fs::read_to_string(&path) {
            Ok(s) => s,
            Err(_) => return TodoList::new(),
        };
        match serde_json::from_str(&raw) {
            Ok(list) => list,
            Err(_) => TodoList::new(),
        }
    }

    pub fn save(&self) {
        let path = data_path();
        // Issue 14: we ignore the result of both the serialize and write —
        // a permission error or a full disk will fail silently.
        let json = serde_json::to_string_pretty(self).unwrap();
        let _ = fs::write(&path, json);
    }
}
