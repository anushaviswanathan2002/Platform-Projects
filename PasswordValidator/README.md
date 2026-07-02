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
| [Zxcvbn](https://www.nuget.org/packages/Zxcvbn/) | 1.0.2 | Dropbox's password strength estimator. Replaces the hand-rolled weighted-sum scoring with an entropy-based model. |

### Install Dependencies & Build
```bash
cd PasswordValidator
dotnet restore   # pulls Zxcvbn 1.0.2 from NuGet
dotnet build
```

### Run
```bash
dotnet run
```

Then enter passwords to validate. Type `quit` to exit.

The console now also reports the Zxcvbn-derived **Guesses** count and any **Warning** feedback from the library.

## Intentional Issues (to be found & fixed)

The application is deliberately broken. Below is a list of known bugs a tester
should locate, diagnose, and patch:

| #  | File        | Issue                                                                                                  |
|----|-------------|--------------------------------------------------------------------------------------------------------|
| 1  | Program.cs  | Minimum password length is hard-coded to `8` (modern guidance is `12`).                                |
| 2  | Program.cs  | Uppercase check uses `c >= 'A' && c <= 'Z'` — works by accident, but should use `char.IsUpper(c)`.     |
| 3  | Program.cs  | Error message says "at least 2 digits" but the check only requires `>= 1`.                             |
| 4  | Program.cs  | `ValidatePassword` is called with empty/null input with no guard — should short-circuit.               |
| 5  | Program.cs  | Magic numbers (`8`, `12`, `20`, `15`, `40`, `60`, `80`) scattered through code — should be constants.  |
| 6  | Program.cs  | `Score` is capped at `100`, but the max sum of bonuses is `100`; the cap is redundant and confusing.   |
| 7  | Program.cs  | The "digit" bonus adds `+20` even when only one digit is present; bonus should scale with digit count. |
| 8  | Program.cs  | Strength thresholds appear inverted or misaligned: a real "Strong" password should need `>= 80`.       |
| 9  | Program.cs  | `IsValid` is only set at the end — if the validator throws, the result is never marked.                |

## Validation Rules (intended spec)
- Minimum length: **12** characters
- At least **1** uppercase letter
- At least **2** digits
- At least **1** special character
- Score is based on a weighted mix of length, variety, and character classes
- Strength bands: Weak (<40), Medium (<60), Strong (<80), Excellent (>=80)

## Project Layout
```
PasswordValidator/
├── PasswordValidator.csproj    # Declares the Zxcvbn 1.0.2 PackageReference
├── Program.cs                  # All logic lives here (for simplicity)
└── README.md
```
