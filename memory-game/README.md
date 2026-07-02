# Memory Game (Java)

A small Java implementation of the classic Memory (card-matching) game.
It is intentionally shipped with **known bugs** and a JUnit 4 test suite
that pins down the expected behaviour. The project is meant to be used
as a sandbox for:

1. Installing project dependencies (`mvn`).
2. Running the test suite to see the bugs reproduced.
3. Fixing the bugs in `src/main/java` until all tests pass.

## Requirements

- Java 11+ (the project targets Java 11).
- Maven 3.6+.

## Build & test

```bash
# Resolve and download dependencies (JUnit 4 etc.)
mvn -q dependency:resolve

# Compile main + test sources
mvn -q test-compile

# Run the JUnit suite - several tests will FAIL on the buggy build
mvn -q test
```

You should see several failing tests, including ones related to:

- `Board.getValueAt` silently returning `0` for out-of-range indices.
- `Board.isComplete` having an off-by-one error.
- `Board.flip` not actually revealing cards on a match, and
  incrementing the match counter on every attempt (not only matches).
- `MemoryGame` starting the player's score at `size` instead of `0`.

## Run the game (once the bugs are fixed)

```bash
mvn -q -DskipTests package
mvn -q exec:java -Dexec.args="4"
```

## Project layout

```
memory-game/
├── pom.xml
├── README.md
└── src
    ├── main/java/com/example/memory/
    │   ├── Board.java        # the game board (contains the bugs)
    │   └── MemoryGame.java   # CLI driver
    └── test/java/com/example/memory/
        └── BoardTest.java    # behavioural tests (will fail on buggy build)
```
