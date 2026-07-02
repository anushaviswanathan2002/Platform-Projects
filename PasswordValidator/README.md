# PasswordValidator

A simple .NET 8 console application that validates password strength.
**This project contains intentional bugs and is intended as a testing/practice exercise.**

## Getting Started

### Prerequisites
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)

### External Dependencies
This project uses the following NuGet package:

| Package | Version | Purpose |
|---------|---------|---------|
| [Zxcvbn-netstandard](https://www.nuget.org/packages/Zxcvbn-netstandard/) | 1.0.2 | .NET Standard port of Dropbox's password strength estimator. Replaces the hand-rolled weighted-sum scoring with an entropy-based model. This is the .NET Standard build of the `Zxcvbn` package — same library, different TFM. |

> **Package swap note:** The project originally referenced the
> [Zxcvbn](https://www.nuget.org/packages/Zxcvbn/) package, which is no longer
> maintained on NuGet. It was switched to `Zxcvbn-netstandard` (a community
> .NET Standard 2.0 build of the same library) without changing the
> functionality — the namespace, the `MatchPassword(...)` entry point, and the
> `Zxcvbn.Zxcvbn` static class are all identical.

### Install Dependencies & Build
```bash
cd PasswordValidator
dotnet restore   # pulls Zxcvbn-netstandard 1.0.2 from NuGet
dotnet build
```

### Run
```bash
dotnet run
```

Then enter passwords to validate. Type `quit` to exit.

The console now also reports the Zxcvbn-derived **Entropy** (in bits), any
**Warning** message, and a list of **Suggestions** from the library.

## Intentional Issues (to be found & fixed)

The application is deliberately broken. Below is a list of known bugs a tester
should locate, diagnose, and patch. Bugs **#6–#8** described the hand-rolled
weighted-sum scorer that was removed when the project was migrated to the
`Zxcvbn-netstandard` external dependency; see the *Migration history* section
below for the pre-migration wording.

| #  | File        | Issue                                                                                                  |
|----|-------------|--------------------------------------------------------------------------------------------------------|
| 1  | Program.cs  | Minimum password length is hard-coded to `8` (modern guidance is `12`).                                |
| 2  | Program.cs  | Uppercase check uses `c >= 'A' && c <= 'Z'` — works by accident, but should use `char.IsUpper(c)`.     |
| 3  | Program.cs  | Error message says "at least 2 digits" but the check only requires `>= 1`.                             |
| 4  | Program.cs  | `ValidatePassword` is called with empty/null input with no guard — should short-circuit.               |
| 5  | Program.cs  | Magic numbers (`8`) scattered through code — should be constants.                                     |
| 9  | Program.cs  | `IsValid` is only set at the end — if the validator throws, the result is never marked.                |

### Migration history (Zxcvbn → Zxcvbn-netstandard)

The original `Zxcvbn` 1.0.2 NuGet package has been replaced with
`Zxcvbn-netstandard` 1.0.2 (same library, .NET Standard 2.0 build). The
following code-level issues, all centered on the now-removed hand-rolled
scorer, are therefore **no longer applicable**:

| Old # | Original issue (pre-migration)                                                                          |
|-------|----------------------------------------------------------------------------------------------------------|
| 6     | `Score` was capped at `100`, but the max sum of bonuses is `100`; the cap is redundant and confusing.     |
| 7     | The "digit" bonus added `+20` even when only one digit was present; bonus should scale with digit count. |
| 8     | Strength thresholds were inverted/misaligned: a real "Strong" password should need `>= 80`. **(fixed)**   |

A few additional notes on the migration:

- The `Zxcvbn.Zxcvbn.Match(...)` entry point was renamed to
  `MatchPassword(password, userInputs)`. The second argument is a list of
  user-supplied inputs (e.g. username, email) that the library should treat as
  easily-guessable. We pass an empty list.
- The result object no longer exposes a `Guesses` count or a typed
  `Feedback.Warning` field. Instead it exposes:
  - `Entropy` — entropy estimate in bits (replaces the old `Guesses` count in
    the UI; entropy is the more useful number for a human reader).
  - `warning` (enum) and `suggestions` (enum list) — translated to strings via
    `Zxcvbn.Utility.GetWarning(...)` / `GetSuggestion(...)` using
    `Zxcvbn.Translation.English`. The translated `Warning` text and each
    `Suggestion` are surfaced on the console.

## Validation Rules (intended spec)
- Minimum length: **12** characters
- At least **1** uppercase letter
- At least **2** digits
- At least **1** special character
- Score and strength are derived from the **`Zxcvbn-netstandard`** external
  dependency (Dropbox's entropy-based estimator). The library's internal
  `Score` is on a `0..4` scale and is multiplied by `25` to fit the existing
  `0..100` UI.
- Strength bands (mapped from the library's `0..4` score):
  Weak (`<=1`), Medium (`2`), Strong (`3`), Excellent (`4`)

## Project Layout
```
PasswordValidator/
├── PasswordValidator.csproj    # Declares the Zxcvbn-netstandard 1.0.2 PackageReference
├── Program.cs                  # All logic lives here (for simplicity)
└── README.md
```
