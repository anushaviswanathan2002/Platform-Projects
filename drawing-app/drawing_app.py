"""
A simple Python drawing app using tkinter and Pillow.

Fixes applied for the seven known issues:

ISSUE #1 (FIXED): Resizing the window used to wipe the canvas because
          ``_on_configure`` deleted every item. The fix keeps a persistent
          PIL ``Image`` as the source of truth and re-renders the cached
          ``PhotoImage`` from it on resize. The PhotoImage is kept on
          ``self`` to avoid garbage collection.

ISSUE #2 (FIXED): ``save_image`` now opens a ``asksaveasfilename`` dialog
          and converts RGBA → RGB when the chosen format is JPEG (or any
          format that does not support alpha) so it no longer crashes.

ISSUE #3 (FIXED): The ``Clear`` toolbar button is no longer shadowed by
          a mouse binding — the canvas mouse binding was removed because
          the toolbar button already calls ``clear_canvas`` directly.

ISSUE #4 (FIXED): ``tk.Scale`` ``from_``/``to`` are now integers and
          ``on_size_change`` is robust to the value being delivered as a
          string (which it always is from tk).

ISSUE #5 (FIXED): ``WM_DELETE_WINDOW`` now calls a real ``on_close``
          handler that prompts the user to save unsaved work and only
          destroys the window when the user confirms or saves.

ISSUE #6 (FIXED): ``undo`` now actually undoes the last stroke. A
          snapshot stack stores PIL images so undo restores the previous
          state of the backend image and the canvas.

ISSUE #7 (FIXED): ``load_image`` compares the image's ``width``/``height``
          against the canvas dimensions (tuple comparison of images
          silently worked, but a too-small canvas would not trigger the
          warning). The function now warns the user and returns ``False``
          (a real value) so callers can handle the failure correctly.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageTk


CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
DEFAULT_BG = "white"
UNDO_LIMIT = 20


class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Drawing App")

        # Drawing state
        self.color = "black"
        self.brush_size = 3
        self.last_x = None
        self.last_y = None
        self._dirty = False
        self._undo_stack = []

        # Backend PIL image that mirrors what's on the canvas
        self.image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), DEFAULT_BG)
        self.draw = ImageDraw.Draw(self.image)

        # Cached PhotoImage — must be kept on self so Tkinter doesn't
        # garbage-collect it (otherwise the canvas appears blank).
        self._photo = None

        self._build_ui()
        self._refresh_canvas()
        self._push_undo_snapshot()  # baseline so the first stroke is undoable

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Color buttons
        for c in ("black", "red", "blue", "green", "orange", "purple"):
            b = tk.Button(
                toolbar, bg=c, width=3,
                command=lambda col=c: self.set_color(col),
            )
            b.pack(side=tk.LEFT, padx=2, pady=2)

        # Brush size — FIX #4: from_/to are integers, not strings
        tk.Label(toolbar, text="Brush:").pack(side=tk.LEFT, padx=(10, 0))
        self.size_var = tk.IntVar(value=self.brush_size)
        size_scale = tk.Scale(
            toolbar, from_=1, to=20, orient=tk.HORIZONTAL,
            variable=self.size_var, command=self.on_size_change,
        )
        size_scale.pack(side=tk.LEFT)

        # Action buttons — FIX #3: Clear is invoked directly from the
        # toolbar button; we don't bind it to a mouse button any more.
        tk.Button(toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Save", command=self.save_image).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Load", command=self.load_image).pack(side=tk.LEFT, padx=4)

        # Canvas
        self.canvas = tk.Canvas(
            self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
            bg=DEFAULT_BG, highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # FIX #1: re-render the cached PIL image on resize instead of
        # clearing the canvas. The handler is a no-op for the initial
        # size allocation, which avoids a redundant repaint.
        self.canvas.bind("<Configure>", self._on_configure)

        # Drawing events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

        # FIX #5: route the close-button through a real handler that
        # prompts to save unsaved work and tears down state cleanly.
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------- Actions
    def set_color(self, color):
        self.color = color

    def on_size_change(self, value):
        # FIX #4: tk delivers scale values as strings, but the range is
        # now integer-typed, so int() is always safe.
        self.brush_size = int(value)

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def draw_line(self, event):
        if self.last_x is None or self.last_y is None:
            return
        x, y = event.x, event.y
        self.canvas.create_line(
            self.last_x, self.last_y, x, y,
            fill=self.color, width=self.brush_size,
            capstyle=tk.ROUND, smooth=True,
        )
        self.draw.line(
            [(self.last_x, self.last_y), (x, y)],
            fill=self.color, width=self.brush_size,
        )
        self.last_x, self.last_y = x, y
        self._dirty = True

    def end_draw(self, event):
        self.last_x, self.last_y = None, None
        if self._dirty:
            self._push_undo_snapshot()

    def clear_canvas(self, event=None):
        self.canvas.delete("all")
        self.image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), DEFAULT_BG)
        self.draw = ImageDraw.Draw(self.image)
        self._refresh_canvas()
        self._dirty = True
        self._push_undo_snapshot()

    def undo(self):
        # FIX #6: implement real undo. Pop the last snapshot and restore
        # the PIL image, then repaint the canvas.
        if len(self._undo_stack) <= 1:
            return
        self._undo_stack.pop()
        previous = self._undo_stack[-1].copy()
        self.image = previous
        self.draw = ImageDraw.Draw(self.image)
        self.canvas.delete("all")
        self._refresh_canvas()
        self._dirty = True

    def save_image(self):
        # FIX #2: ask the user where to save, and convert to RGB if the
        # chosen format cannot store an alpha channel.
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("JPEG image", "*.jpg *.jpeg"),
                ("BMP image", "*.bmp"),
                ("GIF image", "*.gif"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            ext = path.rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "bmp"):
                out = self.image.convert("RGB")
            else:
                out = self.image
            out.save(path)
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))
            return
        self._dirty = False
        messagebox.showinfo("Saved", f"Image saved to {path}")

    def load_image(self):
        # FIX #7: do a correct dimension check and return a truthy value
        # on success / falsy on failure (instead of None on either path).
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if not path:
            return False
        try:
            img = Image.open(path)
            w, h = img.size
            if w > CANVAS_WIDTH or h > CANVAS_HEIGHT:
                messagebox.showwarning(
                    "Too big",
                    f"Image is {w}x{h}, larger than the {CANVAS_WIDTH}x{CANVAS_HEIGHT} canvas.",
                )
                return False
            self.image = img.convert("RGBA")
            self.draw = ImageDraw.Draw(self.image)
            self._refresh_canvas()
            self._dirty = True
            self._push_undo_snapshot()
            return True
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            return False

    def on_close(self):
        # FIX #5: prompt to save unsaved work before exiting.
        if self._dirty:
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                "You have unsaved changes. Save before quitting?",
            )
            if answer is None:  # cancel — keep the app open
                return
            if answer:           # yes — try to save, abort close on cancel
                saved = self._save_silently()
                if not saved:
                    return
        self._cleanup()
        self.root.destroy()

    # ------------------------------------------------------------- Helpers
    def _save_silently(self):
        """Save with the same dialog as save_image; return True on success."""
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg *.jpeg"),
                       ("BMP image", "*.bmp"), ("All files", "*.*")],
        )
        if not path:
            return False
        try:
            ext = path.rsplit(".", 1)[-1].lower()
            out = self.image.convert("RGB") if ext in ("jpg", "jpeg", "bmp") else self.image
            out.save(path)
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))
            return False
        self._dirty = False
        return True

    def _push_undo_snapshot(self):
        self._undo_stack.append(self.image.copy())
        if len(self._undo_stack) > UNDO_LIMIT:
            self._undo_stack.pop(0)

    def _refresh_canvas(self):
        # FIX #1: keep a long-lived PhotoImage attribute and reuse the
        # canvas image item. Re-creating the PhotoImage on every repaint
        # is fine; we just must not let it get garbage-collected.
        self._photo = ImageTk.PhotoImage(self.image)
        image_id = getattr(self, "_canvas_image_id", None)
        if image_id is None:
            self._canvas_image_id = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=self._photo
            )
        else:
            self.canvas.itemconfigure(image_id, image=self._photo)

    def _on_configure(self, event):
        # FIX #1: do NOT clear the canvas on resize. Tk fires <Configure>
        # on the bound widget (the canvas) every time the layout changes.
        # The first event is the initial layout — skip it because we
        # already rendered the canvas in __init__. Subsequent events are
        # real resizes, and we simply re-display the cached PIL image.
        if not getattr(self, "_initial_configure_done", False):
            self._initial_configure_done = True
            return
        self._refresh_canvas()

    def _cleanup(self):
        # FIX #5: release PIL resources explicitly on close to avoid
        # sporadic "image is wrong size" warnings on quit.
        try:
            self._photo = None
            self.image = None
            self.draw = None
        except Exception:
            pass


def main():
    root = tk.Tk()
    DrawingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
