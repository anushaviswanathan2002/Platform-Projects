package com.example.memory;

import org.junit.Test;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * Behavioural tests for {@link Board}.
 *
 * These tests describe the intended behaviour of the Memory game board.
 * When the project is first checked out the tests should FAIL because
 * Board.java contains known bugs; once the bugs are fixed all tests pass.
 */
public class BoardTest {

    @Test
    public void boardRejectsOddSize() {
        try {
            new Board(3);
            fail("Expected IllegalArgumentException for odd size");
        } catch (IllegalArgumentException expected) {
            // ok
        }
    }

    @Test
    public void boardRejectsZeroSize() {
        try {
            new Board(0);
            fail("Expected IllegalArgumentException for size 0");
        } catch (IllegalArgumentException expected) {
            // ok
        }
    }

    @Test
    public void getValueAtReturnsCardValue() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertEquals(0, board.getValueAt(0));
        assertEquals(1, board.getValueAt(1));
        assertEquals(0, board.getValueAt(2));
        assertEquals(1, board.getValueAt(3));
    }

    @Test(expected = IndexOutOfBoundsException.class)
    public void getValueAtThrowsForNegativeIndex() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.getValueAt(-1);
    }

    @Test(expected = IndexOutOfBoundsException.class)
    public void getValueAtThrowsForIndexAtSize() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.getValueAt(4);
    }

    @Test
    public void newBoardHasNoMatchesAndNothingRevealed() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertEquals(0, board.getMatchesFound());
        assertFalse(board.isRevealed(0));
        assertFalse(board.isRevealed(1));
        assertFalse(board.isRevealed(2));
        assertFalse(board.isRevealed(3));
        assertFalse(board.isComplete());
    }

    @Test
    public void flipOnMatchingCardsReturnsTrueAndRevealsBoth() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertTrue(board.flip(0, 2));
        assertTrue(board.isRevealed(0));
        assertTrue(board.isRevealed(2));
    }

    @Test
    public void flipOnNonMatchingCardsReturnsFalseAndRevealsNothing() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertFalse(board.flip(0, 1));
        assertFalse(board.isRevealed(0));
        assertFalse(board.isRevealed(1));
    }

    @Test
    public void matchesFoundOnlyIncrementsOnActualMatch() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.flip(0, 1); // no match
        assertEquals("matchesFound should still be 0 after a non-matching flip",
                0, board.getMatchesFound());
        board.flip(0, 2); // match
        assertEquals("matchesFound should be 1 after one matching flip",
                1, board.getMatchesFound());
        board.flip(1, 3); // match
        assertEquals("matchesFound should be 2 after two matching flips",
                2, board.getMatchesFound());
        board.flip(0, 3); // no match (0 already revealed but still counts as attempt)
        assertEquals("matchesFound should still be 2 after a non-matching flip",
                2, board.getMatchesFound());
    }

    @Test
    public void flippingSameIndexTwiceDoesNotCountAsMatch() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertFalse(board.flip(0, 0));
        assertEquals(0, board.getMatchesFound());
    }

    @Test(expected = IndexOutOfBoundsException.class)
    public void flipWithNegativeIndexThrows() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.flip(-1, 0);
    }

    @Test(expected = IndexOutOfBoundsException.class)
    public void flipWithOutOfRangeIndexThrows() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.flip(0, 4);
    }

    @Test
    public void isCompleteReturnsTrueOnlyWhenAllCardsRevealed() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.flip(0, 2);
        assertFalse("Board should not be complete with two cards still hidden",
                board.isComplete());
        board.flip(1, 3);
        assertTrue("Board should be complete once every pair has been matched",
                board.isComplete());
    }

    @Test
    public void isCompleteIsFalseWhenOnlyLastCardIsHidden() {
        // Regression test for the off-by-one bug: every card except the
        // very last one is revealed, the board should still be incomplete.
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.reveal(0);
        board.reveal(1);
        board.reveal(2);
        // index 3 is still hidden
        assertFalse("Board with the last card still hidden must not be complete",
                board.isComplete());
    }

    @Test
    public void revealAndHideAreInverses() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertFalse(board.isRevealed(0));
        board.reveal(0);
        assertTrue(board.isRevealed(0));
        board.hide(0);
        assertFalse(board.isRevealed(0));
    }

    @Test
    public void renderShowsQuestionMarkForHiddenCards() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        assertArrayEquals(
                new char[]{'?', ' ', '?', ' ', '?', ' ', '?'},
                board.render().toCharArray());
    }

    @Test
    public void renderShowsValueForRevealedCards() {
        Board board = new Board(new int[]{0, 1, 0, 1});
        board.reveal(0);
        board.reveal(2);
        assertArrayEquals(
                new char[]{'0', ' ', '?', ' ', '0', ' ', '?'},
                board.render().toCharArray());
    }
}
