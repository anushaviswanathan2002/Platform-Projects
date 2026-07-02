using System;
using System.Collections.Generic;
using System.Linq;
// External dependency: Zxcvbn — Dropbox's password strength estimator.
// `using Zxcvbn;` exposes the static `Zxcvbn.Zxcvbn` class which collides
// with its namespace, so we alias the type to `ZxcvbnEstimator` to keep
// references readable.
using ZxcvbnEstimator = Zxcvbn.Zxcvbn;

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
                Console.WriteLine($"Entropy  : {result.Entropy:F2} bits (Zxcvbn)");
                if (!string.IsNullOrWhiteSpace(result.Warning))
                {
                    Console.WriteLine($"Warning  : {result.Warning}");
                }
                foreach (var suggestion in result.Suggestions)
                {
                    Console.WriteLine($"Tip      : {suggestion}");
                }

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

            // Score and strength are now derived from the Zxcvbn library
            // (external dependency) instead of the hand-rolled weighted sum.
            // Zxcvbn returns a score in 0..4 and an entropy estimate in bits.
            var zxResult = ZxcvbnEstimator.MatchPassword(password, new List<string>());
            // Scale the 0..4 library score to 0..100 so the existing UI is unchanged.
            result.Score = zxResult.Score * 25;
            result.Entropy = zxResult.Entropy;
            result.Warning = zxResult.warning == Zxcvbn.Warning.Default
                ? string.Empty
                : Zxcvbn.Utility.GetWarning(zxResult.warning, Zxcvbn.Translation.English);
            result.Suggestions = zxResult.suggestions
                .Select(s => Zxcvbn.Utility.GetSuggestion(s, Zxcvbn.Translation.English))
                .ToList();

            // BUG #8 (fixed): strength bands are now derived from the
            // library score, not the inverted hand-rolled thresholds.
            if (zxResult.Score <= 1) result.Strength = "Weak";
            else if (zxResult.Score == 2) result.Strength = "Medium";
            else if (zxResult.Score == 3) result.Strength = "Strong";
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
        // Zxcvbn-derived fields exposed by the external dependency.
        public double Entropy { get; set; }
        public string Warning { get; set; } = string.Empty;
        public System.Collections.Generic.List<string> Suggestions { get; set; }
            = new System.Collections.Generic.List<string>();
        public System.Collections.Generic.List<string> Errors { get; set; }
            = new System.Collections.Generic.List<string>();
    }
}
