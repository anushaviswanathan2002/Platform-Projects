package com.example.memory;

import java.util.Scanner;

/**
 * Simple command-line driver for the Memory game.
 *
 * Usage:
 *   mvn -q -DskipTests package
 *   mvn -q exec:java -Dexec.args="4"
 *
 * Pass an even board size as the first argument (defaults to 4).
 */
public final class MemoryGame {

    private MemoryGame() {
    }

    public static void main(String[] args) {
        int size = 4;
        if (args.length > 0) {
            try {
                size = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                System.err.println("Invalid size argument, falling back to 4.");
            }
        }
        if (size <= 0 || size % 2 != 0) {
            System.err.println("Size must be a positive even number. Using 4.");
            size = 4;
        }

        Board board = new Board(size);
        // BUG #4: the score should start at 0. Initialising it to `size`
        // makes every printed score look much higher than the real score
        // and makes the "X/Y" target display (size/2) inconsistent.
        int score = size;
        int turns = 0;
        Scanner scanner = new Scanner(System.in);
        System.out.println("Memory game (size " + size + "). Enter two indices per turn, 0-" + (size - 1) + ".");
        System.out.println("Type 'q' to quit.");
        while (!board.isComplete()) {
            System.out.println(board.render());
            int first = readIndex(scanner, "First card: ");
            if (first < 0) {
                break;
            }
            int second = readIndex(scanner, "Second card: ");
            if (second < 0) {
                break;
            }
            turns++;
            if (board.flip(first, second)) {
                score++;
                System.out.println("Match! Score: " + score + "/" + (size / 2));
            } else {
                System.out.println("No match. Score: " + score + "/" + (size / 2));
            }
        }
        if (board.isComplete()) {
            System.out.println("You finished in " + turns + " turns with a score of " + score + ".");
        } else {
            System.out.println("Game abandoned after " + turns + " turns.");
        }
    }

    private static int readIndex(Scanner scanner, String prompt) {
        System.out.print(prompt);
        String line = scanner.nextLine().trim();
        if (line.equalsIgnoreCase("q")) {
            return -1;
        }
        try {
            return Integer.parseInt(line);
        } catch (NumberFormatException e) {
            System.err.println("Not a number, please try again.");
            return readIndex(scanner, prompt);
        }
    }
}
