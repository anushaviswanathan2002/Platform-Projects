use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Todo {
    pub id: u32,
    pub title: String,
    pub done: bool,
}

impl Todo {
    // Issue 7 fix: id is now supplied by the caller (TodoList::add) so every
    // todo gets a unique identifier instead of all colliding on 0.
    pub fn new(id: u32, title: String) -> Self {
        Todo { id, title, done: false }
    }
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct TodoList {
    pub items: Vec<Todo>,
    // Issue 8 fix: counter is the single source of truth for id allocation
    // and is bumped inside `add`.
    next_id: u32,
}

impl TodoList {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    // Issue 8 fix: pull the current counter, push the new todo with that id,
    // then bump the counter. Returns the assigned id.
    pub fn add(&mut self, title: String) -> u32 {
        let id = self.next_id;
        self.next_id += 1;
        self.items.push(Todo::new(id, title));
        id
    }

    pub fn get(&self, index: usize) -> Option<&Todo> {
        self.items.get(index)
    }

    // Issue 9 fix: return a Result so the caller can react to bad input
    // instead of silently doing nothing.
    pub fn mark_done(&mut self, index: usize) -> Result<(), &'static str> {
        match self.items.get_mut(index) {
            Some(t) => {
                t.done = true;
                Ok(())
            }
            None => Err("todo id out of range"),
        }
    }

    // Issue 10 fix: explicit bounds check returning a Result instead of
    // panicking on out-of-range indexes.
    pub fn remove(&mut self, index: usize) -> Result<(), &'static str> {
        if index >= self.items.len() {
            return Err("todo id out of range");
        }
        self.items.remove(index);
        Ok(())
    }

    // Issues 5 & 11 fix: case-insensitive comparison and short-circuit on an
    // empty needle so `filter ""` returns no todos.
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
}
