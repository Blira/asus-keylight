from __future__ import annotations

from asus_keylight.controller import current_brightness, ensure_supported_model, max_brightness, run_apply
from asus_keylight.discovery import discover_keyboard
from asus_keylight.errors import AsusKeylightError, ValidationError

PRESET_COLOURS = [
    ("Sun", "ffcc00"),
    ("Amber", "ff9500"),
    ("Rose", "ff375f"),
    ("Mint", "2dd4bf"),
    ("Ocean", "0ea5e9"),
    ("Violet", "8b5cf6"),
    ("Snow", "f8fafc"),
    ("Lime", "a3e635"),
]

SURFACE = "#f6f1e8"
CARD = "#fffaf0"
EDGE = "#d8cab3"
TEXT = "#2d2418"
MUTED = "#6f6250"
ACCENT = "#1f6feb"
ACCENT_ACTIVE = "#1757b8"
SUCCESS = "#1f8f55"
ERROR = "#c0392b"


class AsusKeylightApp:
    def __init__(self, root, tk_module, ttk_module, colorchooser_module):
        self.tk = tk_module
        self.ttk = ttk_module
        self.colorchooser = colorchooser_module
        self.root = root
        self.root.title("ASUS Keylight")
        self.root.resizable(False, False)
        self.root.configure(bg=SURFACE)

        self.selected_colour = self.tk.StringVar(value="0ea5e9")
        self.brightness = self.tk.IntVar(value=1)
        self.status = self.tk.StringVar(value="Ready.")
        self.device_label = self.tk.StringVar(value="Detecting keyboard...")

        self._configure_style()
        self._build_ui()
        self.refresh_device()

    def _configure_style(self) -> None:
        style = self.ttk.Style()
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass

        style.configure("App.TFrame", background=SURFACE)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=("TkDefaultFont", 18, "bold"))
        style.configure("Body.TLabel", background=SURFACE, foreground=MUTED, font=("TkDefaultFont", 10))
        style.configure("CardTitle.TLabel", background=CARD, foreground=TEXT, font=("TkDefaultFont", 11, "bold"))
        style.configure("CardBody.TLabel", background=CARD, foreground=MUTED, font=("TkDefaultFont", 10))
        style.configure("Hex.TLabel", background=CARD, foreground=TEXT, font=("TkDefaultFont", 16, "bold"))
        style.configure("Primary.TButton", font=("TkDefaultFont", 10, "bold"))
        style.map("Primary.TButton", background=[("active", ACCENT_ACTIVE), ("!disabled", ACCENT)])

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        frame = self.ttk.Frame(self.root, padding=18, style="App.TFrame")
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)

        hero = self.ttk.Frame(frame, padding=(0, 0, 0, 14), style="App.TFrame")
        hero.grid(row=0, column=0, sticky="we")
        hero.columnconfigure(0, weight=1)

        self.ttk.Label(hero, text="Keyboard Light", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.ttk.Label(hero, text="Choose a color visually and send it straight to the keyboard.", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        overview = self.tk.Frame(frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        overview.grid(row=1, column=0, sticky="we")
        overview.grid_columnconfigure(1, weight=1)

        self.preview = self.tk.Canvas(overview, width=104, height=104, bg=CARD, highlightthickness=0)
        self.preview.grid(row=0, column=0, rowspan=3, padx=14, pady=14)
        self.preview_rect = self.preview.create_rectangle(8, 8, 96, 96, fill="#0ea5e9", outline=EDGE, width=2)

        self.hex_badge = self.ttk.Label(overview, text="#0ea5e9", style="Hex.TLabel")
        self.hex_badge.grid(row=0, column=1, sticky="w", pady=(14, 2), padx=(0, 14))

        self.device = self.ttk.Label(overview, textvariable=self.device_label, style="CardBody.TLabel", wraplength=330, justify="left")
        self.device.grid(row=1, column=1, sticky="we", padx=(0, 14))

        picker_row = self.ttk.Frame(overview, style="Card.TFrame")
        picker_row.grid(row=2, column=1, sticky="we", padx=(0, 14), pady=(10, 14))
        self.hex_entry = self.ttk.Entry(picker_row, textvariable=self.selected_colour, width=14, justify="center")
        self.hex_entry.grid(row=0, column=0, sticky="w")
        self.hex_entry.bind("<KeyRelease>", self._on_hex_changed)
        self.ttk.Button(picker_row, text="Pick Colour", command=self.choose_colour).grid(row=0, column=1, padx=(10, 0))

        presets = self.tk.Frame(frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        presets.grid(row=2, column=0, sticky="we", pady=(14, 0))
        self.ttk.Label(presets, text="Presets", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(12, 4))

        for index, (name, value) in enumerate(PRESET_COLOURS):
            button = self.tk.Button(
                presets,
                text=name,
                bg=f"#{value}",
                activebackground=f"#{value}",
                fg="#111111" if name in {"Sun", "Snow", "Lime"} else "#ffffff",
                activeforeground="#111111" if name in {"Sun", "Snow", "Lime"} else "#ffffff",
                width=9,
                relief="flat",
                highlightthickness=0,
                padx=8,
                pady=8,
                command=lambda v=value: self.set_colour(v),
            )
            button.grid(row=1 + index // 4, column=index % 4, padx=10, pady=(6, 12), sticky="we")

        brightness_card = self.tk.Frame(frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        brightness_card.grid(row=3, column=0, sticky="we", pady=(14, 0))
        brightness_card.grid_columnconfigure(0, weight=1)
        self.ttk.Label(brightness_card, text="Brightness", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))

        scale = self.ttk.Scale(
            brightness_card,
            from_=0,
            to=3,
            orient="horizontal",
            variable=self.brightness,
            command=self._on_scale_changed,
        )
        scale.grid(row=1, column=0, sticky="we", padx=14, pady=(10, 0))

        scale_labels = self.ttk.Frame(brightness_card, style="Card.TFrame")
        scale_labels.grid(row=2, column=0, sticky="we", padx=14, pady=(4, 0))
        for index in range(4):
            label = self.ttk.Label(scale_labels, text=str(index), style="CardBody.TLabel")
            label.grid(row=0, column=index, sticky="w" if index == 0 else "e" if index == 3 else "n")
            scale_labels.columnconfigure(index, weight=1)

        self.brightness_value = self.ttk.Label(brightness_card, text="Level 1", style="CardBody.TLabel")
        self.brightness_value.grid(row=3, column=0, sticky="e", padx=14, pady=(8, 12))

        actions = self.ttk.Frame(frame, style="App.TFrame")
        actions.grid(row=4, column=0, sticky="we", pady=(14, 0))
        actions.columnconfigure((0, 1, 2), weight=1)
        self.ttk.Button(actions, text="Apply Colour", command=self.apply_colour, style="Primary.TButton").grid(row=0, column=0, sticky="we")
        self.ttk.Button(actions, text="Apply Both", command=self.apply_both).grid(row=0, column=1, sticky="we", padx=8)
        self.ttk.Button(actions, text="Refresh", command=self.refresh_device).grid(row=0, column=2, sticky="we")

        status_card = self.tk.Frame(frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        status_card.grid(row=5, column=0, sticky="we", pady=(14, 0))
        self.status_indicator = self.tk.Label(status_card, width=2, bg=SUCCESS)
        self.status_indicator.grid(row=0, column=0, sticky="ns", padx=(14, 10), pady=14)
        self.status_label = self.ttk.Label(status_card, textvariable=self.status, style="CardBody.TLabel", wraplength=380, justify="left")
        self.status_label.grid(row=0, column=1, sticky="we", padx=(0, 14), pady=14)
        status_card.grid_columnconfigure(1, weight=1)

        self._render_colour(self.selected_colour.get())
        self._on_scale_changed(str(self.brightness.get()))

    def _render_colour(self, value: str) -> None:
        value = value.lower().removeprefix("#")
        self.preview.itemconfigure(self.preview_rect, fill=f"#{value}")
        self.hex_badge.configure(text=f"#{value}")

    def _set_status(self, message: str, *, is_error: bool = False) -> None:
        self.status.set(message)
        self.status_indicator.configure(bg=ERROR if is_error else SUCCESS)

    def _normalize_colour(self, value: str) -> str:
        normalized = value.strip().lower().removeprefix("#")
        if len(normalized) != 6 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValidationError("color must be a 6-digit RGB hex value")
        return normalized

    def _on_hex_changed(self, _event=None) -> None:
        value = self.selected_colour.get()
        try:
            normalized = self._normalize_colour(value)
        except ValidationError:
            return
        self.selected_colour.set(normalized)
        self._render_colour(normalized)

    def _on_scale_changed(self, _value: str) -> None:
        level = round(self.brightness.get())
        self.brightness.set(level)
        names = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
        self.brightness_value.configure(text=f"Level {level} · {names[level]}")

    def set_colour(self, value: str) -> None:
        normalized = self._normalize_colour(value)
        self.selected_colour.set(normalized)
        self._render_colour(normalized)

    def choose_colour(self) -> None:
        _, hex_value = self.colorchooser.askcolor(color=f"#{self.selected_colour.get()}", parent=self.root)
        if hex_value:
            self.set_colour(hex_value)

    def refresh_device(self) -> None:
        try:
            target = discover_keyboard()
            ensure_supported_model(target, force=False)
            brightness = current_brightness(target)
            max_level = max_brightness(target)
            self.brightness.set(brightness)
            self._on_scale_changed(str(brightness))
            self.device_label.set(f"{target.product_name}\n{target.hidraw_path} · brightness 0..{max_level}")
            self._set_status("Device ready.")
        except AsusKeylightError as exc:
            self.device_label.set("Keyboard controller not ready.")
            self._set_status(f"Error: {exc}", is_error=True)

    def apply_colour(self) -> None:
        self._apply(colour_only=True)

    def apply_both(self) -> None:
        self._apply(colour_only=False)

    def _apply(self, *, colour_only: bool) -> None:
        try:
            colour = self._normalize_colour(self.selected_colour.get())
            brightness = round(self.brightness.get())
            run_apply(
                colour_hex=colour,
                brightness=None if colour_only else brightness,
                dry_run=False,
                force=False,
            )
            if colour_only:
                self._set_status(f"Applied colour #{colour}.")
            else:
                self._set_status(f"Applied colour #{colour} with brightness {brightness}.")
        except AsusKeylightError as exc:
            self._set_status(f"Error: {exc}", is_error=True)


def main() -> int:
    try:
        import tkinter as tk
        from tkinter import colorchooser, ttk
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "tkinter is not installed. Install the distro package first, for example: sudo apt install python3-tk"
        ) from exc

    root = tk.Tk()
    AsusKeylightApp(root, tk, ttk, colorchooser)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
