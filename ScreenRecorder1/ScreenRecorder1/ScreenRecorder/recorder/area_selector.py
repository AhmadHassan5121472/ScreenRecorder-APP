import tkinter as tk


class AreaSelector:
    """Simple full-screen rectangle selector on the primary display."""

    def __init__(self):
        self.selection = None
        self.root = None
        self.canvas = None
        self.start_x = self.start_y = 0
        self.rect = None

    def select(self):
        self.selection = None
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        try:
            self.root.attributes("-alpha", 0.35)
        except Exception:
            pass

        self.canvas = tk.Canvas(
            self.root, bg="black", highlightthickness=0, cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 35,
            text="Drag to select recording area  •  ESC to cancel",
            fill="white", font=("Arial", 16, "bold")
        )
        self.canvas.bind("<ButtonPress-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._up)
        self.root.bind("<Escape>", self.cancel)
        self.root.mainloop()
        return self.selection

    def _down(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=3
        )

    def _move(self, event):
        if self.rect:
            self.canvas.coords(
                self.rect, self.start_x, self.start_y, event.x, event.y
            )

    def _up(self, event):
        x1, x2 = sorted((self.start_x, event.x))
        y1, y2 = sorted((self.start_y, event.y))
        width, height = x2 - x1, y2 - y1
        if width < 50 or height < 50:
            self.cancel()
            return
        width -= width % 2
        height -= height % 2
        self.selection = {
            "left": x1, "top": y1,
            "width": width, "height": height
        }
        self.close()

    def cancel(self, event=None):
        self.selection = None
        self.close()

    def close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
