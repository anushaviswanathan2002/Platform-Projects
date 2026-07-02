using System;
using System.Linq;

namespace PasswordValidator
{
    public class Program
    {
        // BUG #1: Magic number for minimum length is hard-coded inside the method
        // BUG #5: No constant class is defined - magic numbers scattered
        public static void Main(string[] args)
        {
            Console.WriteLine("=== Password Validator ===");
            Console.WriteLine("Enter a password to validate (or 'quit' to exit):");

            while (true)
            {
                Console.Write("> ");
                string? input = Console.ReadLine();

                if (input == null)
                {
                    Console.WriteLine("No input received. Exiting.");
                    break;
                }

                if (input.Trim().ToLower() == "quit")
                {
                    Console.WriteLine("Goodbye!");
                    break;
                }

                // BUG #4: No null/empty guard - empty input is passed to validator
                var result = ValidatePassword(input);

                Console.WriteLine();
                Console.WriteLine($"Password : {input}");
                Console.WriteLine($"Valid    : {result.IsValid}");
                Console.WriteLine($"Strength : {result.Strength}");
                Console.WriteLine($"Score    : {result.Score}/100");

                if (result.Errors.Count > 0)
                {
                    Console.WriteLine("Issues   :");
                    foreach (var err in result.Errors)
                    {
                        Console.WriteLine($"  - {err}");
                    }
                }
                Console.WriteLine();
            }
        }

        public static ValidationResult ValidatePassword(string password)
        {
            var result = new ValidationResult();

            // BUG #1: Hard-coded minimum length 8 — should be 12 for modern security
            if (password.Length < 8)
            {
                result.Errors.Add("Password must be at least 8 characters long.");
            }

            // BUG #2: Uppercase check uses incorrect LINQ — this works by accident
            //        but the logic is fragile. Should use char.IsUpper.
            bool hasUpper = password.Any(c => c >= 'A' && c <= 'Z');
            if (!hasUpper)
            {
                result.Errors.Add("Password must contain at least one uppercase letter.");
            }

            // BUG #3: Digit count is checked with >= 1 but the spec is >= 2 digits
            int digitCount = password.Count(c => c >= '0' && c <= '9');
            if (digitCount < 1)
            {
                result.Errors.Add("Password must contain at least 2 digits.");
            }

            // Special character check
            bool hasSpecial = password.Any(c => !char.IsLetterOrDigit(c));
            if (!hasSpecial)
            {
                result.Errors.Add("Password must contain at least one special character.");
            }

            // BUG #6: Score is calculated by summing points but caps at 100 incorrectly.
            //         When all rules pass, score is 50, not 100. The cap line is wrong.
            result.Score = 0;
            if (password.Length >= 8) result.Score += 20;
            if (password.Length >= 12) result.Score += 10;
            if (hasUpper) result.Score += 15;
            // BUG #7: digit bonus always adds 20 even if there is only 1 digit
            if (digitCount >= 1) result.Score += 20;
            if (hasSpecial) result.Score += 15;
            if (password.Distinct().Count() >= 6) result.Score += 20;

            // BUG #6 (continued): Off-by-one / wrong cap
            if (result.Score > 100) result.Score = 100;

            // BUG #8: Strength thresholds are inverted - "Strong" needs score < 60
            if (result.Score < 40) result.Strength = "Weak";
            else if (result.Score < 60) result.Strength = "Medium";
            else if (result.Score < 80) result.Strength = "Strong";
            else result.Strength = "Excellent";

            // BUG #9: IsValid is set only after score calculation, but if errors exist
            //         the validator should mark invalid. Currently IsValid is never set!
            result.IsValid = result.Errors.Count == 0;

            return result;
        }
    }

    public class ValidationResult
    {
        public bool IsValid { get; set; }
        public string Strength { get; set; } = "Unknown";
        public int Score { get; set; }
        public System.Collections.Generic.List<string> Errors { get; set; }
            = new System.Collections.Generic.List<string>();
    }
}
