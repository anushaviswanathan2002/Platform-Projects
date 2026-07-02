use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Todo {
    pub id: u32,
    pub title: String,
    pub done: bool,
}

impl Todo {
    pub fn new(title: String) -> Self {
        // Issue 7: id is always 0, so every todo collides on the same id.
        Todo { id: 0, title, done: false }
    }
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct TodoList {
    pub items: Vec<Todo>,
    // Issue 8: we never read this counter, so even if we fix Todo::new,
    // the auto-increment value would be wrong.
    #[allow(dead_code)]
    next_id: u32,
}

impl TodoList {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    pub fn add(&mut self, item: Todo) {
        self.items.push(item);
    }

    pub fn get(&self, index: usize) -> Option<&Todo> {
        self.items.get(index)
    }

    pub fn mark_done(&mut self, index: usize) {
        // Issue 9: silently does nothing on out-of-range instead of
        // returning a Result the caller can react to.
        if let Some(t) = self.items.get_mut(index) {
            t.done = true;
        }
    }

    pub fn remove(&mut self, index: usize) {
        // Issue 10: this panics on out-of-range instead of returning Result.
        self.items.remove(index);
    }

    pub fn filter(&self, needle: &str) -> Vec<Todo> {
        // Issue 11: returns a clone of the *whole* list when needle is empty,
        // instead of an empty Vec. That makes `filter ""` behave like `list`.
        self.items
            .iter()
            .filter(|t| t.title.contains(needle))
            .cloned()
            .collect()
    }
}
