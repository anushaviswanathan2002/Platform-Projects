# todo-ruby

A small Ruby CLI todo app, intentionally shipped with **planted issues** so you can
practice (a) installing dependencies and (b) fixing bugs in the application code.

## Setup

```sh
cd todo-ruby
bundle install
```

> ⚠️ `bundle install` is expected to fail on the first try. See "Planted Issues" below.

## Running the tests

```sh
bundle exec rspec
```

> ⚠️ Several specs are expected to fail until the planted issues are fixed.

## Using the CLI

```sh
bin/todo add "buy milk"
bin/todo list
bin/todo done 1
bin/todo rm 1
```

## Planted Issues

| # | Type | File | Symptom | Fix |
|---|------|------|---------|-----|
| 1 | Dependency | `Gemfile` | `bundle install` fails: `rspec 3.99.0` does not exist | Change to a real version, e.g. `gem "rspec", "~> 3.13"` |
| 2 | Setup | `todo.gemspec` | `bundle install` fails: `required_ruby_version = ">= 99.0.0"` | Change to a realistic version, e.g. `">= 3.0.0"` |
| 3 | Code bug | `lib/todo.rb` (`List#add`) | Reused id, second add collides | Track and increment `@next_id` |
| 4 | Code bug | `lib/todo.rb` (`List#complete`) | `NoMethodError: undefined method 'complete'` | Use the actual method `complete!` |
| 5 | Code bug | `lib/todo.rb` (`List#pending`) | Returns *done* items instead of *pending* | `select { |i| !i.done? }` |
