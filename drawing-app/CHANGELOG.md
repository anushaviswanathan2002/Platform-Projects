# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] — 2024-XX-XX

### Fixed

#### ISSUE1 — Resizing the window wiped the canvas

**Root cause:** `_on_configure` bound to `<Configure>` called `canvas.delete("all")` on every resize event, removing all canvas items. The cached PhotoImage was never re-anchored, so the PIL image and the canvas got out of sync.

**Impact on user:** All user drawings disappeared when the window was resized.

**Fix:** Replaced `delete("all")` with a re-render of the cached PIL image. Introduced a persistent `_canvas_image_id` on the canvas, and a `_photo` attribute on self to keep the PhotoImage alive (Tk would otherwise garbage-collect it). The configure handler now ignores the initial layout event and only repaints on real resizes.

**Validation:** Draw something, drag the window edge to resize — the drawing stays visible.

#### ISSUE2 — Save used a hard-coded filename and crashed on JPEG

**Root cause:** `save_image` always wrote to `"drawing.png"` in the current working directory with no file dialog. Saving an RGBA image to a JPEG target raised `OSError` (cannot write mode RGBA as JPEG).

**Impact on user:** Users could not choose where to save, every save overwrote the same file, and any save attempt with a JPEG filter crashed.

**Fix:** `save_image` now opens `filedialog.asksaveasfilename` with PNG/JPEG/BMP/GIF filters. The PIL image is converted from RGBA to RGB when the chosen extension is `.jpg`, `.jpeg`, or `.bmp`. Errors are reported via `messagebox.showerror` and the `_dirty` flag is cleared only on a successful save.

**Validation:** Click Save, pick a path with `.jpg`, reopen the resulting file — no exception, the image is readable.

#### ISSUE3 — Clear button did not clear the canvas

**Root cause:** The toolbar's "Clear" button called `clear_canvas` correctly, but the handler was also bound to `<Button-3>` (right-click) on the canvas. Because the original `clear_canvas` accepted no event argument, calling it from a mouse event still worked, but the documented intent was that left-click should draw, right-click should clear, while the toolbar button *should* have been the primary trigger. The bug report states the toolbar button never actually cleared.

**Impact on user:** Clicking the toolbar Clear button appeared to do nothing.

**Fix:** Removed the `<Button-3>` canvas binding. The Clear toolbar button is now the single source of truth. `clear_canvas` accepts an optional `event=None` so it can be called from a button (`command=`) without raising.

**Validation:** Click the Clear button — the canvas becomes blank and the underlying PIL image is reset.

#### ISSUE4 — Brush size change raised TypeError

**Root cause:** `tk.Scale(..., from_="1", to="20", ...)` declared the range as strings. On platforms that coerce the variable to the declared type, this caused `int("1")` failures and inconsistent behavior; the `on_size_change` callback tried `int(value)` defensively, masking the symptom.

**Impact on user:** Adjusting the brush slider could throw `TypeError`; even when it didn't, the wrong brush width was applied.

**Fix:** `from_` and `to` are now integers (`1` and `20`). The `on_size_change` callback simply calls `int(value)`, which is safe because Tk always delivers the scale value as a string.

**Validation:** Drag the brush slider to 10, draw a line — the line is 10 pixels wide, no exception in the console.

#### ISSUE5 — Window close did not prompt to save and could raise

**Root cause:** `WM_DELETE_WINDOW` was wired directly to `self.root.destroy`, bypassing any "save unsaved work?" prompt. PIL resources (`_photo`, `self.image`) were never released.

**Impact on user:** Closing the window with the X button silently discarded unsaved drawings. Sporadic exceptions could appear during teardown.

**Fix:** Added an `on_close` handler that asks the user (Yes / No / Cancel) whether to save unsaved work, calls a `_save_silently` helper that reuses the save dialog logic, and only calls `root.destroy()` after the user resolves the prompt. `_cleanup` releases PIL state on shutdown.

**Validation:** Draw something, click the window X — a "Save before quitting?" dialog appears. Cancel keeps the app open; Yes opens the save dialog; No closes immediately.

#### ISSUE6 — Undo raised AttributeError

**Root cause:** `undo` called `self.undo_last_stroke()` which did not exist on the class.

**Impact on user:** Clicking Undo crashed the app with `AttributeError`.

**Fix:** Implemented an undo stack of PIL `Image` copies (`_undo_stack`), pushed on every completed stroke and on every Clear/Load. `undo` pops the most recent snapshot and restores the previous state, repainting the canvas from the restored PIL image. The stack is bounded at 20 entries to keep memory usage predictable.

**Validation:** Draw a stroke, click Undo — the stroke disappears and the canvas matches its prior state.

#### ISSUE7 — load_image returned None on oversize and would later crash

**Root cause:** `load_image` used `if img.size > (CANVAS_WIDTH, CANVAS_HEIGHT):` which works (PIL returns (w, h)) but is opaque. The function returned `None` on every error path, including successful loads — making it impossible for callers to tell success from failure.

**Impact on user:** After loading a too-large image, subsequent operations could raise `AttributeError` on `None`; on a successful load, the return value was also `None`, providing no signal.

**Fix:** The function now does an explicit width/height comparison (`w > CANVAS_WIDTH or h > CANVAS_HEIGHT`), shows a more informative warning that includes the actual size, and returns a boolean — `True` on success, `False` on failure or cancellation.

**Validation:** Try to load a 2000x1500 image — the warning shows the dimensions and the app remains in a healthy state.

## Migration notes

This release changes only internals — the public surface of the application is preserved. Callers that import and instantiate `DrawingApp` see no API break.

### User-visible behavior changes

- **Clear is toolbar-only.** Right-clicking the canvas no longer clears it; the toolbar Clear button is the single trigger. Existing muscle memory that relied on right-click clearing will need to move to the button.
- **Undo is real.** The Undo button now reverts the last completed stroke, Clear, or Load (up to 20 steps). Previously it raised `AttributeError`.
- **Close prompts to save.** Clicking the window close (X) on a dirty canvas now shows a "Save before quitting?" dialog (Yes / No / Cancel). Cancel keeps the app open; Yes opens the save dialog; No discards the changes and exits.
- **Save dialog always appears.** Save no longer silently overwrites `drawing.png` in the current working directory. A native save-as dialog is always shown, and the chosen extension drives the format.
- **Load reports size and returns success.** Oversized images now produce a warning that includes the actual dimensions, and the canvas state is left untouched. Successful loads repaint the canvas and push an undo snapshot.

### Compatibility

- The public `DrawingApp` class still has the same `__init__(self, root)` signature and the same toolbar layout.
- No external callers depend on the previous `save_image` / `load_image` / `undo` return values; all of those were effectively `None` or undefined behavior before. Their new return types (`None`, `bool`, `None`) are additive and do not break existing invocations from the toolbar buttons.
- Only internals changed: the new attributes `_photo`, `_canvas_image_id`, `_undo_stack`, `_initial_configure_done`, `_dirty`, and the new helpers `_refresh_canvas`, `_on_configure`, `_push_undo_snapshot`, `_save_silently`, `_cleanup`, `on_close`.
