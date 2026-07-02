require_relative "lib/todo/version"

Gem::Specification.new do |spec|
  spec.name          = "todo"
  spec.version       = Todo::VERSION
  spec.authors       = ["Test User"]
  spec.email         = ["test@example.com"]

  spec.summary       = "A small CLI todo app (with planted issues for testing)."
  spec.description   = "Used to practice installing dependencies and fixing intentional bugs."
  spec.license       = "MIT"

  spec.required_ruby_version = ">= 3.0.0"

  spec.files = Dir["lib/**/*.rb", "bin/*", "README.md"]
  spec.bindir = "bin"
  spec.executables = ["todo"]
  spec.require_paths = ["lib"]
end
