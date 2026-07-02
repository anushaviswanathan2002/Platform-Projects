"""
A simple Python drawing app using tkinter and Pillow.

ISSUE #1: When the window is resized the drawn content is wiped out
          (canvas state is recreated from scratch on every <Configure>).
ISSUE #2: The "Save" button writes the file but always uses a hard-coded
          filename "drawing.png" and never asks the user for a location
          (also the image is saved in RGB mode even though we draw RGBA).
ISSUE #3: The Clear button does not actually clear the canvas because the
          handler is bound to the wrong event (Button-1 instead of Button-3,
          so right-clicking does nothing, and left-click is also being
          captured by the draw handler).
ISSUE #4: The "color" variable used in the Brush size is a string, so the
          tk.Scale value is treated as a string and causes a TypeError when
          drawing a line wider than 1 px.
ISSUE #5: Closing the window with the X button does not prompt to save
          unsaved work, and sometimes raises an exception on quit.
ISSUE #6: Undo button is wired to a function that does not exist
          (AttributeError when clicked).
ISSUE #7: Loading an image that is larger than the canvas silently does
          nothing and returns None, which later crashes the app.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw


CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
DEFAULT_BG = "white"


class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Drawing App")

        # Drawing state
        self.color = "black"          # ISSUE #4: shadowed as a string below
        self.brush_size = 3
        self.last_x = None
        self.last_y = None

        # Backend PIL image that mirrors what's on the canvas
        self.image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), DEFAULT_BG)
        self.draw = ImageDraw.Draw(self.image)

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Color buttons
        for c in ("black", "red", "blue", "green", "orange", "purple"):
            b = tk.Button(toolbar, bg=c, width=3, command=lambda col=c: self.set_color(col))
            b.pack(side=tk.LEFT, padx=2, pady=2)

        # Brush size — ISSUE #4: the `from_`/`to` are strings, not ints
        tk.Label(toolbar, text="Brush:").pack(side=tk.LEFT, padx=(10, 0))
        self.size_var = tk.IntVar(value=self.brush_size)
        size_scale = tk.Scale(
            toolbar, from_="1", to="20", orient=tk.HORIZONTAL,        # BUG
            variable=self.size_var, command=self.on_size_change,
        )
        size_scale.pack(side=tk.LEFT)

        # Action buttons
        tk.Button(toolbar, text="Clear", command=self.clear_canvas).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Save", command=self.save_image).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Load", command=self.load_image).pack(side=tk.LEFT, padx=4)

        # Canvas
        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
                                bg=DEFAULT_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ISSUE #1: resizing the window wipes the drawing
        self.canvas.bind("<Configure>", self._on_configure)

        # Drawing events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

        # ISSUE #3: Clear is bound to a mouse click that never fires the
        # actual clear handler correctly
        self.canvas.bind("<Button-3>", self.clear_canvas)

        # ISSUE #5: window close is not handled cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    # ------------------------------------------------------------- Actions
    def set_color(self, color):
        self.color = color

    def on_size_change(self, value):
        # ISSUE #4: value is a str; the int() call here will raise on
        # some platforms and brush size is otherwise mis-applied
        try:
            self.brush_size = int(value)
        except ValueError:
            self.brush_size = 1

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

    def end_draw(self, event):
        self.last_x, self.last_y = None, None

    def clear_canvas(self, event=None):
        self.canvas.delete("all")
        self.image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), DEFAULT_BG)
        self.draw = ImageDraw.Draw(self.image)

    def undo(self):
        # ISSUE #6: this function does not exist
        self.undo_last_stroke()

    def save_image(self):
        # ISSUE #2: hard-coded path and no file dialog
        path = "drawing.png"
        # ISSUE #2: saving an RGBA image to a .png works, but if the
        # user changes the filter to JPEG this will crash because of
        # the RGBA mode
        self.image.save(path)
        messagebox.showinfo("Saved", f"Image saved to {path}")

    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if not path:
            return
        try:
            img = Image.open(path)
            # ISSUE #7: if the image is larger than the canvas we silently
            # return None which later raises AttributeError
            if img.size > (CANVAS_WIDTH, CANVAS_HEIGHT):
                messagebox.showwarning("Too big", "Image is larger than the canvas.")
                return None
            self.image = img.convert("RGBA")
            self.draw = ImageDraw.Draw(self.image)
            self._refresh_canvas()
        except Exception as exc:
            messagebox.showerror("Load error", str(exc))
            return None

    # ------------------------------------------------------------- Helpers
    def _refresh_canvas(self):
        # ISSUE #1: re-creates a fresh PhotoImage and forgets the old one,
        # contributing to the resize bug
        from PIL import ImageTk
        self._photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

    def _on_configure(self, event):
        # ISSUE #1: this fires on every resize, but it actually clears
        # the canvas by repainting nothing over the old content. Worse,
        # the PIL image and the canvas get out of sync.
        self.canvas.delete("all")


def main():
    root = tk.Tk()
    DrawingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
