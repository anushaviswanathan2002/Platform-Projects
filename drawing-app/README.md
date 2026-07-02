# Simple Drawing App (with issues)

A tiny Python desktop drawing app built with **tkinter** and **Pillow**.
It is intentionally broken in several places so you can practice
installing dependencies, running the app, and then fixing the bugs.

## Install

```bash
cd drawing-app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python drawing_app.py
```

A window will open with a toolbar (colors, brush size, Clear / Undo /
Save / Load) and a white canvas.

## Known issues to fix

| #  | Where                          | Symptom                                                                 |
|----|--------------------------------|-------------------------------------------------------------------------|
| 1  | `_on_configure` / `_refresh_canvas` | Resizing the window erases everything you drew.                    |
| 2  | `save_image`                   | Always writes `drawing.png` to cwd, no file dialog, RGBA→JPEG would crash. |
| 3  | Clear binding                  | Bound to `<Button-3>`, so it never fires from the toolbar button.        |
| 4  | Brush `Scale` widget           | `from_`/`to` are strings → `TypeError` when changing brush size.        |
| 5  | `WM_DELETE_WINDOW`             | No "Save before quitting?" prompt; can leak PIL resources.              |
| 6  | `undo`                         | Calls `self.undo_last_stroke()` which doesn't exist.                    |
| 7  | `load_image`                   | Returns `None` on oversize images → `AttributeError` on next save.      |

Fix them, then re-run and confirm:

```bash
python drawing_app.py
```
