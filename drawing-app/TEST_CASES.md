# Test Cases — Drawing App

This document catalogs the high-level test cases that verify the seven bug
fixes applied to `drawing_app.py`, along with a set of general happy-path
cases. The test catalog is intentionally implementation-agnostic so the same
cases can be executed manually, against a recorded interaction script, or via
a pytest harness that drives the `DrawingApp` class directly.

> Source under test: `drawing_app.py` (`DrawingApp` class, ~310 LOC)
>
> Constants: `CANVAS_WIDTH=800`, `CANVAS_HEIGHT=600`, `DEFAULT_BG="white"`,
> `UNDO_LIMIT=20`.

---

## Test Strategy

`DrawingApp` is a `tkinter` GUI; the standard guidance for unit-testing tkinter
is to run inside a headless display server (e.g. `xvfb-run -a pytest …`) so
that `tk.Tk()` can construct a real root window without an attached display.
A pytest harness is expected to:

1. Build a real `tk.Tk()` root inside the fixture.
2. `monkeypatch` `tkinter.filedialog` and `tkinter.messagebox` so dialogs do
   not block and the test can simulate user choices.
3. Drive the `DrawingApp` instance by invoking its public methods directly
   (`start_draw`, `draw_line`, `end_draw`, `clear_canvas`, `undo`, etc.) with
   synthetic `Event`-like objects (any object exposing `x` and `y` works, or
   `types.SimpleNamespace(x=…, y=…)`).
4. Inspect observable state: the backend `self.image` (a `PIL.Image`),
   `self._dirty`, `self._undo_stack`, the canvas item list, and the cached
   `self._photo`.

Manual execution of the same cases is supported by following the "Steps"
column verbatim against the running application. Where a test case is
automatable but not manually meaningful, it is marked **regression** or
**negative** in the matrix below.

---

## Test Matrix

| Test ID     | Category      | Description                                                            | Steps (summary)                                                          | Expected Result                                                     |
| ----------- | ------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| TC-DRAW-01  | Happy Path    | A single drag stroke updates both canvas and PIL image                 | Press, drag, release                                                     | Canvas has a line item; `self.image` is non-blank; `self._dirty` set |
| TC-DRAW-02  | Edge          | Drawing with brush sizes 1, 5, 20 produces no exceptions               | Change size to 1/5/20, draw short lines                                  | `self.brush_size` updates; no exception; pixels painted             |
| TC-RESIZE-01| Regression #1 | Resizing the window preserves drawn content                            | Draw a stroke, shrink + grow the window                                  | Canvas still shows the stroke; PIL image unchanged                  |
| TC-RESIZE-02| Edge          | Several rapid resizes do not corrupt or blank the canvas               | Draw, resize 5 times in quick succession                                 | Canvas still shows the original stroke                              |
| TC-SAVE-01  | Happy Path    | Save as PNG via file dialog                                             | Draw, click Save, choose `out.png`                                       | File exists on disk; `self._dirty` becomes `False`                  |
| TC-SAVE-02  | Edge / Regr.  | Save as JPEG does not crash on the RGBA image                          | Draw, click Save, choose `out.jpg`                                       | File exists; PIL saved an RGB image (no alpha)                      |
| TC-SAVE-03  | Edge          | Cancelling the save dialog writes nothing                               | Click Save, dismiss dialog                                               | No file created; `self._dirty` unchanged                            |
| TC-SAVE-04  | Regression #2 | No hard-coded `drawing.png` is written in the working directory        | Save with a different name; check `cwd`                                  | No `drawing.png` appears in `os.getcwd()`                           |
| TC-CLEAR-01 | Happy Path    | Toolbar "Clear" button clears the canvas                                | Draw, click Clear                                                        | Canvas is blank; PIL image reset to white; `self._dirty` set         |
| TC-CLEAR-02 | Regression #3 | Left-click and drag still draws (Clear did not hijack Button-1)        | Press and drag Button-1 across the canvas                                | A line is drawn (Clear was never called)                            |
| TC-BRUSH-01 | Happy Path    | Setting brush size to 10 then drawing uses width 10                    | Drag the brush slider to 10, draw a line                                 | Line is visibly thicker; `self.brush_size == 10`                    |
| TC-BRUSH-02 | Regression #4 | Changing brush size does not raise `TypeError`                         | Move slider through 1, 5, 10, 15, 20                                     | `on_size_change` returns; no exception; type is `int`               |
| TC-CLOSE-01 | Happy Path    | Closing the window with no unsaved changes exits immediately           | Open, draw nothing, close                                                | `askyesnocancel` not invoked; window destroyed                      |
| TC-CLOSE-02 | Edge          | Close with unsaved changes, user picks Save                             | Draw, close, answer Yes, supply path                                     | File written; window destroyed                                      |
| TC-CLOSE-03 | Edge          | Close with unsaved changes, user picks Don't Save                      | Draw, close, answer No                                                   | No file written; window destroyed                                   |
| TC-CLOSE-04 | Edge          | Close with unsaved changes, user picks Cancel                          | Draw, close, answer Cancel                                               | Window still alive; `_dirty` still `True`                           |
| TC-UNDO-01  | Happy Path    | Draw a stroke, then Undo restores the previous state                    | Draw stroke A, draw stroke B, click Undo                                 | Stroke B disappears, stroke A remains                               |
| TC-UNDO-02  | Edge          | Undo with no history does not raise                                    | Fresh app, click Undo repeatedly                                         | No exception; canvas untouched; `len(_undo_stack) >= 1`             |
| TC-LOAD-01  | Happy Path    | Loading a small image replaces the canvas content                       | Create 100×100 PNG, click Load, select it                                | Canvas now shows that image; `self.image.size == (100,100)`         |
| TC-LOAD-02  | Regression #7 | Loading an image larger than the canvas warns and returns `False`      | Create 1200×900 PNG, click Load                                          | `messagebox.showwarning` called; returns `False`; canvas unchanged  |
| TC-LOAD-03  | Edge          | Cancelling the open dialog returns `False`                              | Click Load, dismiss dialog                                               | No dialog after warning; returns `False`; no state change            |
| TC-LOAD-04  | Negative      | Loading a corrupted file shows an error and returns `False`             | Click Load, choose a non-image file                                      | `messagebox.showerror` called; returns `False`; canvas unchanged    |

---

## Detailed Test Cases

### TC-DRAW-01 — Single drag stroke updates both canvas and PIL image

- **Category:** Happy Path
- **Preconditions:** Fresh `DrawingApp` instance bound to a real `tk.Tk()`
  root, headless display OK.
- **Steps:**
  1. Call `app.start_draw(Event(x=10, y=10))`.
  2. Call `app.draw_line(Event(x=60, y=40))`.
  3. Call `app.end_draw(Event(x=60, y=40))`.
- **Expected Result:**
  - `app.canvas` contains at least one line item.
  - `app.image.getpixel((30, 25))` is not pure white (a pixel was painted on
    the backend).
  - `app._dirty` is `True`.
  - `len(app._undo_stack) >= 2` (baseline + new snapshot).
- **Notes:** A `types.SimpleNamespace(x=..., y=...)` is sufficient for the
  synthetic event; only `x`/`y` are read by `start_draw`/`draw_line`/
  `end_draw`.

### TC-DRAW-02 — Drawing with brush sizes 1, 5, 20 produces no exceptions

- **Category:** Edge
- **Preconditions:** Same as TC-DRAW-01.
- **Steps:**
  1. For each `n` in `[1, 5, 20]`:
     a. `app.size_var.set(n)` (or call `app.on_size_change(str(n))`).
     b. Drag from `(100, 100)` to `(200, 100 + n)`.
     c. Release.
- **Expected Result:**
  - `app.brush_size == n` after the slider change.
  - No `TypeError`, `TclError`, or PIL exception is raised.
  - The painted line is visibly thicker as `n` increases (verifiable by
    counting non-white pixels in a vertical slice through the line).
- **Notes:** This is the primary regression sentinel for **#4** even though
  TC-BRUSH-02 is the canonical one — drawing with the new brush size is the
  user-visible behavior.

### TC-RESIZE-01 — Resize preserves drawn content (Regression #1)

- **Category:** Regression
- **Preconditions:** DrawingApp created, headless display.
- **Steps:**
  1. Draw a short diagonal stroke from `(50, 50)` to `(150, 150)`.
  2. Resize the root window: shrink to `400×300` (`root.geometry("400x300")`).
  3. Resize again: grow to `1000×800` (`root.geometry("1000x800")`).
  4. Call `root.update_idletasks()` after each resize to flush events.
- **Expected Result:**
  - The diagonal stroke is still visible on the canvas after both resizes.
  - `app.image` is unchanged (same pixel data; only the cached
    `ImageTk.PhotoImage` is rebuilt).
  - `app._photo is not None`.
- **Notes:** The pre-fix behavior was `canvas.delete("all")` on
  `<Configure>`, which blanked the canvas. The fix reuses the persistent
  PIL `Image` as the source of truth and only refreshes the `PhotoImage`.

### TC-RESIZE-02 — Rapid multiple resizes do not blank or corrupt the canvas

- **Category:** Edge
- **Preconditions:** DrawingApp created.
- **Steps:**
  1. Draw a recognizable shape (e.g. a cross at canvas center).
  2. Loop five times alternating `root.geometry("500x400")` and
     `root.geometry("900x700")`, calling `root.update_idletasks()` between.
- **Expected Result:**
  - The cross is still visible at the end.
  - No exception is raised in any iteration.
- **Notes:** Exercises the `_on_configure` skip-first-event guard, which
  must continue to be honored across many `<Configure>` events.

### TC-SAVE-01 — Save as PNG via file dialog (Happy Path)

- **Category:** Happy Path
- **Preconditions:** `monkeypatch` `tkinter.filedialog.asksaveasfilename` to
  return a temp path with `.png` extension; drawing made.
- **Steps:**
  1. `app.start_draw(Event(50,50))`, `app.draw_line(Event(120,80))`,
     `app.end_draw(Event(120,80))`.
  2. Call `app.save_image()`.
- **Expected Result:**
  - `Path(tmp_path / "out.png").exists()` is `True`.
  - `app._dirty` is `False`.
  - `messagebox.showinfo` is called (monkeypatched to a no-op or a spy).
- **Notes:** `monkeypatch.setattr(filedialog, "asksaveasfilename",
  lambda **kw: str(tmp_path/"out.png"))` is the standard pattern.

### TC-SAVE-02 — Save as JPEG does not crash on the RGBA image (Regression #2)

- **Category:** Edge / Regression
- **Preconditions:** As TC-SAVE-01, but the mocked path ends in `.jpg`.
- **Steps:**
  1. Draw a stroke (so the RGBA image has non-white pixels).
  2. `monkeypatch` `asksaveasfilename` to return `str(tmp_path/"out.jpg")`.
  3. Call `app.save_image()`.
- **Expected Result:**
  - No exception (the pre-fix crash was `OSError: cannot write mode RGBA as
    JPEG`).
  - The output file exists and is loadable with `Image.open(…)`; `image.mode
    == "RGB"`.
- **Notes:** Internally the code does
  `out = self.image.convert("RGB")` for `ext in ("jpg","jpeg","bmp")`.

### TC-SAVE-03 — Save dialog cancelled writes nothing

- **Category:** Edge
- **Preconditions:** As TC-SAVE-01, but `asksaveasfilename` returns `""`
  (i.e. the user clicked Cancel).
- **Steps:**
  1. Mark the app dirty by drawing.
  2. Call `app.save_image()`.
- **Expected Result:**
  - No file is written to `tmp_path`.
  - `app._dirty` remains `True`.
  - No `messagebox.showinfo` is invoked.

### TC-SAVE-04 — No hard-coded `drawing.png` in the working directory (Regression #2)

- **Category:** Regression
- **Preconditions:** `os.chdir(tmp_path)`; `monkeypatch` `asksaveasfilename`
  to return `str(tmp_path/"my_drawing.png")`.
- **Steps:**
  1. Call `app.save_image()`.
  2. `list(tmp_path.iterdir())`.
- **Expected Result:**
  - The directory contains only `my_drawing.png`, **not** a `drawing.png`
    file.
- **Notes:** This pins the user-visible behavior: saves go where the user
  picks, not to a hard-coded relative path.

### TC-CLEAR-01 — Toolbar "Clear" button clears the canvas

- **Category:** Happy Path
- **Preconditions:** DrawingApp created, some content drawn.
- **Steps:**
  1. Draw a stroke so the canvas is not blank.
  2. Invoke the `Clear` toolbar button's `command` (or call
     `app.clear_canvas()` directly).
- **Expected Result:**
  - The canvas has no non-image items (the only item should be the
     background image).
  - The PIL image is reset to white at every sampled coordinate.
  - `app._dirty` is `True` and a new undo snapshot was pushed.
- **Notes:** In a harness, find the button by widget class and invoke
  `button.invoke()`. Pre-fix, the canvas was bound to `<Button-3>` to
  "clear" and the button did nothing because both bound the same handler.

### TC-CLEAR-02 — Left-click and drag still draws (Regression #3)

- **Category:** Regression
- **Preconditions:** DrawingApp created, canvas empty.
- **Steps:**
  1. Synthesize a press-move-release sequence on the canvas at
     `Button-1`: `app.canvas.event_generate("<Button-1>", x=10, y=10)`,
     `<B1-Motion>` at `(40, 40)`, `<ButtonRelease-1>` at `(40, 40)`.
  2. Alternatively: `app.start_draw(SimpleNamespace(x=10,y=10))`,
     `app.draw_line(SimpleNamespace(x=40,y=40))`,
     `app.end_draw(SimpleNamespace(x=40,y=40))`.
- **Expected Result:**
  - A line item is added to the canvas.
  - `app.image.getpixel((20, 20))` is not pure white.
- **Notes:** Pre-fix, the canvas was bound to `<Button-3>` to "clear" but
  the binding shadowed the toolbar button; in either case the regression
  contract is: **left-click drawing is never broken by Clear**.

### TC-BRUSH-01 — Brush size 10 then drawing uses width 10

- **Category:** Happy Path
- **Preconditions:** DrawingApp created.
- **Steps:**
  1. `app.size_var.set(10)`; call `app.on_size_change("10")` to simulate the
     callback the slider invokes.
  2. Draw a short horizontal line.
- **Expected Result:**
  - `app.brush_size == 10`.
  - The line's pixel footprint is roughly 10 pixels tall in a vertical
    slice through the line.
  - No exception.
- **Notes:** The harness can also measure via
  `numpy`/`sum(p != WHITE for p in image.crop((…)).getdata())`, or simply
  verify the canvas line item's `width` config.

### TC-BRUSH-02 — Changing brush size does not raise `TypeError` (Regression #4)

- **Category:** Regression
- **Preconditions:** DrawingApp created.
- **Steps:**
  1. For each `n` in `[1, 2, 5, 10, 15, 20]`:
     a. `app.size_var.set(n)`.
     b. `app.on_size_change(str(n))` (this is what tk actually delivers).
- **Expected Result:**
  - No `TypeError` (pre-fix, `from_="1", to="20"` produced a float range
    and comparisons broke).
  - `app.brush_size` is an `int` equal to `n` at every step.
  - `isinstance(app.brush_size, int)` is `True`.

### TC-CLOSE-01 — Close with no unsaved changes exits immediately

- **Category:** Happy Path
- **Preconditions:** Fresh `DrawingApp` (`self._dirty == False`).
- **Steps:**
  1. Call `app.on_close()`.
- **Expected Result:**
  - `messagebox.askyesnocancel` is **not** called (spy asserts not called).
  - `app.root.destroy()` was called (use a `monkeypatch` on
    `tk.Tk.destroy`).
- **Notes:** The harness should patch `app.root.destroy` because the real
  one would tear down the root mid-test.

### TC-CLOSE-02 — Close with unsaved changes, user picks Save

- **Category:** Edge
- **Preconditions:** `DrawingApp` with `_dirty == True`.
- **Steps:**
  1. `monkeypatch` `messagebox.askyesnocancel` to return `True`.
  2. `monkeypatch` `filedialog.asksaveasfilename` to return
     `str(tmp_path/"close.png")`.
  3. `monkeypatch` `app.root.destroy` to a sentinel.
  4. Call `app.on_close()`.
- **Expected Result:**
  - The file is written.
  - `app._dirty` is `False`.
  - `destroy` was called.
- **Notes:** Verifies the "Yes" branch of `askyesnocancel`.

### TC-CLOSE-03 — Close with unsaved changes, user picks Don't Save

- **Category:** Edge
- **Preconditions:** `_dirty == True`.
- **Steps:**
  1. `monkeypatch` `messagebox.askyesnocancel` to return `False`.
  2. `monkeypatch` `app.root.destroy` to a sentinel.
  3. Call `app.on_close()`.
- **Expected Result:**
  - `asksaveasfilename` is **not** called.
  - No file is written.
  - `destroy` was called.
  - `app._dirty` remains `True` (irrelevant once destroyed, but documents
    intent).

### TC-CLOSE-04 — Close with unsaved changes, user picks Cancel

- **Category:** Edge
- **Preconditions:** `_dirty == True`.
- **Steps:**
  1. `monkeypatch` `messagebox.askyesnocancel` to return `None` (Cancel).
  2. `monkeypatch` `app.root.destroy` to a sentinel that raises
     `AssertionError` if called.
  3. Call `app.on_close()`.
- **Expected Result:**
  - `destroy` is **not** called.
  - The window remains usable (a follow-up `app.canvas` call works).
  - `app._dirty` is still `True`.

### TC-UNDO-01 — Undo restores the previous state (Regression #6)

- **Category:** Happy Path / Regression
- **Preconditions:** DrawingApp created.
- **Steps:**
  1. `start_draw((100,100))`, `draw_line((200,100))`, `end_draw((200,100))`
     → stroke A.
  2. `start_draw((100,200))`, `draw_line((200,200))`, `end_draw((200,200))`
     → stroke B.
  3. `app.undo()`.
- **Expected Result:**
  - Canvas no longer contains stroke B's pixels (e.g.
     `app.image.getpixel((150,200))` is pure white).
  - Canvas still contains stroke A (e.g. `app.image.getpixel((150,100))`
     is not white).
  - Pre-fix this raised `AttributeError: 'DrawingApp' object has no
     attribute 'undo_last_stroke'`.
- **Notes:** The implementation keeps a snapshot stack capped at
  `UNDO_LIMIT=20`; the baseline snapshot is pushed in `__init__` so the
  first stroke is undoable.

### TC-UNDO-02 — Undo with no history does not raise

- **Category:** Edge
- **Preconditions:** Fresh `DrawingApp` (only the baseline snapshot is
  present).
- **Steps:**
  1. Call `app.undo()`.
  2. Call `app.undo()` again.
- **Expected Result:**
  - No exception.
  - `len(app._undo_stack) >= 1` (the baseline is preserved).
  - Canvas unchanged.
- **Notes:** The implementation guards with
  `if len(self._undo_stack) <= 1: return`.

### TC-LOAD-01 — Loading a small image replaces the canvas content

- **Category:** Happy Path
- **Preconditions:** A real 100×100 PNG exists at
  `tmp_path/"small.png"`. `monkeypatch` `askopenfilename` to return that
  path.
- **Steps:**
  1. Optionally draw a stroke first to make the replacement visible.
  2. Call `app.load_image()`.
- **Expected Result:**
  - Return value is truthy (in fact `True`).
  - `app.image.size == (100, 100)`.
  - `app._dirty` is `True`.
  - A new undo snapshot is pushed.

### TC-LOAD-02 — Oversize image warns and returns `False` (Regression #7)

- **Category:** Regression
- **Preconditions:** A 1200×900 PNG exists at `tmp_path/"big.png"`.
- **Steps:**
  1. `monkeypatch` `askopenfilename` to return that path.
  2. `monkeypatch` `messagebox.showwarning` to a spy.
  3. Record `app.image` identity.
  4. Call `app.load_image()`.
- **Expected Result:**
  - Return value is `False` (pre-fix, `load_image` returned `None` for
    this path, causing `AttributeError` later in callers).
  - `messagebox.showwarning` was called once with a message mentioning the
    offending dimensions.
  - `app.image` is the **same object** as before (no half-loaded state).

### TC-LOAD-03 — Open dialog cancelled returns `False`

- **Category:** Edge
- **Preconditions:** `monkeypatch` `askopenfilename` to return `""`.
- **Steps:**
  1. Record `app.image` identity.
  2. Call `app.load_image()`.
- **Expected Result:**
  - Return value is `False`.
  - No `messagebox.showwarning` or `messagebox.showerror` is called.
  - `app.image` is unchanged.

### TC-LOAD-04 — Loading a corrupted file shows an error and returns `False`

- **Category:** Negative
- **Preconditions:** A non-image file (e.g. plain text) exists at
  `tmp_path/"broken.png"`. `monkeypatch` `askopenfilename` to return it.
- **Steps:**
  1. Record `app.image` identity.
  2. `monkeypatch` `messagebox.showerror` to a spy.
  3. Call `app.load_image()`.
- **Expected Result:**
  - Return value is `False`.
  - `messagebox.showerror` was called.
  - `app.image` is unchanged.
- **Notes:** The `try/except Exception` around `Image.open(...)` swallows
  PIL's `UnidentifiedImageError` and surfaces a friendly error dialog.

---

## Automated Test Harness

This section sketches a pytest fixture pattern that drives `DrawingApp`
directly. It is illustrative; the production test suite should follow the
same shape.

```python
# conftest.py
import os
import tkinter as tk
import pytest

# Force a software renderer / headless backend before tkinter is imported.
os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

@pytest.fixture
def app(monkeypatch, tmp_path):
    """Build a real DrawingApp under Xvfb with dialogs stubbed out."""
    root = tk.Tk()
    from drawing_app import DrawingApp
    a = DrawingApp(root)

    # --- dialog stubs (override per-test as needed) -----------------------
    monkeypatch.setattr(
        "tkinter.filedialog.asksaveasfilename",
        lambda **kw: "",          # default: cancel
    )
    monkeypatch.setattr(
        "tkinter.filedialog.askopenfilename",
        lambda **kw: "",          # default: cancel
    )
    monkeypatch.setattr("tkinter.messagebox.showinfo",  lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.askyesnocancel",
                        lambda *a, **kw: False)

    # Don't actually destroy the root during tests.
    monkeypatch.setattr(root, "destroy", lambda: None)

    yield a

    try:
        root.destroy()
    except tk.TclError:
        pass
```

```python
# test_drawing_app.py
from types import SimpleNamespace as E
from PIL import Image


def make_image(path, w, h, color="red"):
    Image.new("RGB", (w, h), color).save(path)


def test_resize_preserves_content(app, monkeypatch):
    app.start_draw(E(x=50, y=50))
    app.draw_line(E(x=150, y=150))
    app.end_draw(E(x=150, y=150))

    app.root.geometry("400x300"); app.root.update_idletasks()
    app.root.geometry("1000x800"); app.root.update_idletasks()

    assert app.image.getpixel((100, 100)) != (255, 255, 255, 255)


def test_save_jpeg_does_not_crash(app, monkeypatch, tmp_path):
    out = tmp_path / "out.jpg"
    monkeypatch.setattr(
        "tkinter.filedialog.asksaveasfilename",
        lambda **kw: str(out),
    )
    app.start_draw(E(x=10, y=10))
    app.draw_line(E(x=80, y=80))
    app.end_draw(E(x=80, y=80))

    app.save_image()  # must not raise
    assert out.exists()
    assert Image.open(out).mode == "RGB"


def test_load_oversize_returns_false(app, monkeypatch, tmp_path):
    big = tmp_path / "big.png"
    make_image(big, 1200, 900)
    monkeypatch.setattr(
        "tkinter.filedialog.askopenfilename",
        lambda **kw: str(big),
    )
    before = app.image
    assert app.load_image() is False
    assert app.image is before  # no partial swap


def test_undo_restores_previous_state(app):
    app.start_draw(E(x=100, y=100))
    app.draw_line(E(x=200, y=100))
    app.end_draw(E(x=200, y=100))

    app.start_draw(E(x=100, y=200))
    app.draw_line(E(x=200, y=200))
    app.end_draw(E(x=200, y=200))

    app.undo()
    assert app.image.getpixel((150, 200)) == (255, 255, 255, 255)
    assert app.image.getpixel((150, 100)) != (255, 255, 255, 255)


def test_close_with_cancel_keeps_window_alive(app, monkeypatch):
    app._dirty = True
    monkeypatch.setattr("tkinter.messagebox.askyesnocancel",
                        lambda *a, **kw: None)
    destroyed = []
    monkeypatch.setattr(app.root, "destroy", lambda: destroyed.append(True))
    app.on_close()
    assert destroyed == []      # Cancel must NOT destroy
    assert app._dirty is True
```

### Harness notes

- Run inside `xvfb-run -a pytest` to give tkinter a real display.
- For tests that generate actual mouse events, prefer
  `app.start_draw/draw_line/end_draw` with a `SimpleNamespace` — they are
  the public, easily verifiable seams.
- For `<Configure>` coverage, use `root.geometry(...)` plus
  `root.update_idletasks()`; the app's `_on_configure` runs synchronously
  in response to the layout event.
- For the `#1 resize` regression specifically, the harness should also
  assert `app._photo is not None` after the resize, since the pre-fix
  behavior left the canvas blank with a missing `PhotoImage`.
- For `#5 close`, prefer patching `app.root.destroy` so multiple
  scenarios in the same session can be observed.

---

### Mapping of bug fixes to test cases

| Bug   | Description                                | Covered by                                |
| ----- | ------------------------------------------ | ----------------------------------------- |
| #1    | Resize wipes the canvas                    | TC-RESIZE-01, TC-RESIZE-02                |
| #2    | Hard-coded `drawing.png`, JPEG crash       | TC-SAVE-01, TC-SAVE-02, TC-SAVE-03, TC-SAVE-04 |
| #3    | Clear button bound to Button-3             | TC-CLEAR-01, TC-CLEAR-02                  |
| #4    | Brush scale `from_/to` are strings         | TC-BRUSH-01, TC-BRUSH-02                  |
| #5    | Closing window has no save prompt          | TC-CLOSE-01, TC-CLOSE-02, TC-CLOSE-03, TC-CLOSE-04 |
| #6    | Undo calls non-existent method             | TC-UNDO-01, TC-UNDO-02                    |
| #7    | `load_image` returns `None` on oversize    | TC-LOAD-02                                |
