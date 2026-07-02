package com.example.memory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Represents the game board for a Memory (card matching) game.
 * Pairs of cards are placed face down. The player flips two cards
 * per turn; if they match, they stay revealed and the player scores
 * a point. The game ends when every pair has been matched.
 *
 * NOTE: This class intentionally contains bugs for the purpose of
 * a dependency-install + bug-fixing exercise. The tests in
 * src/test/java describe the intended behaviour.
 */
public class Board {

    private final int[] values;
    private final boolean[] revealed;
    private int matchesFound;

    /**
     * Creates a board of the given size. The size must be even, and
     * every card has a matching twin with the same value.
     */
    public Board(int size) {
        if (size <= 0 || size % 2 != 0) {
            throw new IllegalArgumentException("Board size must be a positive even number");
        }
        this.values = new int[size];
        this.revealed = new boolean[size];
        this.matchesFound = 0;
        initialise();
    }

    /**
     * Creates a board with the given values in the given order.
     * Useful for testing.
     */
    public Board(int[] values) {
        if (values == null || values.length == 0 || values.length % 2 != 0) {
            throw new IllegalArgumentException("Values must be a non-empty even-length array");
        }
        this.values = values.clone();
        this.revealed = new boolean[values.length];
        this.matchesFound = 0;
    }

    private void initialise() {
        List<Integer> deck = new ArrayList<>(values.length);
        for (int i = 0; i < values.length / 2; i++) {
            deck.add(i);
            deck.add(i);
        }
        Collections.shuffle(deck, new Random(42));
        for (int i = 0; i < values.length; i++) {
            values[i] = deck.get(i);
        }
    }

    public int size() {
        return values.length;
    }

    /**
     * Returns the value hidden on the card at the given index.
     * Should throw IndexOutOfBoundsException for an invalid index.
     */
    public int getValueAt(int index) {
        // BUG #1: returns 0 silently for an out-of-range index instead of
        // throwing IndexOutOfBoundsException. This hides bugs in callers.
        if (index < 0 || index >= values.length) {
            return 0;
        }
        return values[index];
    }

    public boolean isRevealed(int index) {
        if (index < 0 || index >= values.length) {
            return false;
        }
        return revealed[index];
    }

    public int getMatchesFound() {
        return matchesFound;
    }

    /**
     * Returns true when every pair on the board has been matched.
     */
    public boolean isComplete() {
        // BUG #2: off-by-one error. The loop stops one element too early,
        // so the very last card is never inspected. A board with only the
        // last card unrevealed will incorrectly be reported as complete.
        for (int i = 0; i < revealed.length; i++) {
            if (!revealed[i]) {
                return false;
            }
        }
        return true;
    }

    /**
     * Reveals the card at the given index.
     */
    public void reveal(int index) {
        if (index < 0 || index >= values.length) {
            throw new IndexOutOfBoundsException("Invalid index: " + index);
        }
        revealed[index] = true;
    }

    /**
     * Hides the card at the given index.
     */
    public void hide(int index) {
        if (index < 0 || index >= values.length) {
            throw new IndexOutOfBoundsException("Invalid index: " + index);
        }
        revealed[index] = false;
    }

    /**
     * Flips two cards and reports whether they match.
     * On a match both cards should stay revealed and matchesFound
     * should increase by one.
     */
    public boolean flip(int first, int second) {
        if (first < 0 || first >= values.length || second < 0 || second >= values.length) {
            throw new IndexOutOfBoundsException("Invalid card index");
        }
        if (first == second) {
            return false;
        }
        // BUG #3a: matchesFound is incremented for every flip attempt, even
        // non-matching ones. It should only be incremented on a real match.
        matchesFound++;
        if (values[first] == values[second]) {
            // BUG #3b: the matched cards are NOT actually revealed, so
            // even when flip() returns true the board state is unchanged.
            return true;
        }
        return false;
    }

    /**
     * Returns a string representation of the current board state.
     * '?' marks a hidden card, the value marks a revealed card.
     */
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < values.length; i++) {
            if (revealed[i]) {
                sb.append(values[i]);
            } else {
                sb.append('?');
            }
            if (i < values.length - 1) {
                sb.append(' ');
            }
        }
        return sb.toString();
    }
}
