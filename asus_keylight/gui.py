from __future__ import annotations

import colorsys

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
]

THEMES = {
    "dark": {
        "window_bg": "#111214",
        "card_bg": "#1c1c1e",
        "card_border": "#2f3033",
        "text": "#f5f5f7",
        "muted": "#a1a1a6",
        "field_bg": "#2c2c2e",
        "field_border": "#3a3a3c",
        "primary": "#0a84ff",
        "primary_active": "#0066cc",
        "secondary": "#2c2c2e",
        "secondary_active": "#3a3a3c",
        "success": "#30d158",
        "error": "#ff453a",
        "track": "#3a3a3c",
        "preview_bg": "#242426",
        "picker_bg": "#1c1c1e",
    },
    "light": {
        "window_bg": "#f3f3f5",
        "card_bg": "#fbfbfc",
        "card_border": "#dddddf",
        "text": "#111111",
        "muted": "#6e6e73",
        "field_bg": "#ffffff",
        "field_border": "#d2d2d7",
        "primary": "#0071e3",
        "primary_active": "#0058b0",
        "secondary": "#f5f5f7",
        "secondary_active": "#e9e9ed",
        "success": "#34c759",
        "error": "#ff453a",
        "track": "#d9d9de",
        "preview_bg": "#f0f0f2",
        "picker_bg": "#fbfbfc",
    },
}

SPECTRUM_SIZE = 320
HUE_BAR_WIDTH = 28


class AsusKeylightApp:
    def __init__(self, root, tk_module, ttk_module):
        self.tk = tk_module
        self.ttk = ttk_module
        self.root = root
        self.root.title("ASUS Keylight")
        self.root.resizable(False, False)
        self.theme_mode = self.tk.StringVar(value="dark")
        self.colors = THEMES[self.theme_mode.get()]
        self.root.configure(bg=self.colors["window_bg"])

        self.selected_colour = self.tk.StringVar(value="0ea5e9")
        self.red_value = self.tk.StringVar(value="14")
        self.green_value = self.tk.StringVar(value="165")
        self.blue_value = self.tk.StringVar(value="233")
        self.brightness = self.tk.IntVar(value=1)
        self.live_mode = self.tk.BooleanVar(value=False)
        self.status = self.tk.StringVar(value="Ready")
        self.device_label = self.tk.StringVar(value="Detecting keyboard...")

        self.current_hue = 0.55
        self.current_saturation = 0.94
        self.current_value = 0.91
        self._syncing_inputs = False
        self._live_after_id = None

        self._configure_style()
        self._build_ui()
        self._render_spectrum()
        self._render_hue_bar()
        self._sync_ui_to_current_colour()
        self.refresh_device()

    def _configure_style(self) -> None:
        style = self.ttk.Style()
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass
        style.configure("Keylight.Horizontal.TScale", background=self.colors["card_bg"], troughcolor=self.colors["track"])

    def _make_label(self, parent, text: str, *, size: int = 10, bold: bool = False, fg: str | None = None, bg: str | None = None):
        return self.tk.Label(
            parent,
            text=text,
            bg=bg or self.colors["card_bg"],
            fg=fg or self.colors["text"],
            font=("Helvetica", size, "bold" if bold else "normal"),
        )

    def _make_entry(self, parent, variable, width: int) -> "tk.Entry":
        return self.tk.Entry(
            parent,
            textvariable=variable,
            bg=self.colors["field_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["field_border"],
            highlightcolor=self.colors["primary"],
            font=("Helvetica", 12),
            width=width,
            justify="center",
        )

    def _make_button(self, parent, *, text: str, command, primary: bool = False):
        bg = self.colors["primary"] if primary else self.colors["secondary"]
        active = self.colors["primary_active"] if primary else self.colors["secondary_active"]
        fg = "#ffffff" if primary else self.colors["text"]
        return self.tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            font=("Helvetica", 10, "bold"),
            highlightthickness=0,
            cursor="hand2",
        )

    def _build_ui(self) -> None:
        shell = self.tk.Frame(self.root, bg=self.colors["window_bg"])
        shell.pack(fill="both", expand=True, padx=24, pady=24)
        self.shell = shell

        header = self.tk.Frame(shell, bg=self.colors["window_bg"])
        header.pack(fill="x", pady=(0, 18))
        self.header = header
        header.grid_columnconfigure(0, weight=1)
        title_wrap = self.tk.Frame(header, bg=self.colors["window_bg"])
        title_wrap.grid(row=0, column=0, sticky="w")
        self.title_wrap = title_wrap
        self.title_label = self._make_label(title_wrap, "ASUS Keylight", size=24, bold=True, bg=self.colors["window_bg"])
        self.title_label.pack(anchor="w")
        self.subtitle_label = self._make_label(
            title_wrap,
            "A quiet control surface for ASUS keyboard lighting.",
            size=11,
            fg=self.colors["muted"],
            bg=self.colors["window_bg"],
        )
        self.subtitle_label.pack(anchor="w", pady=(4, 0))
        mode_wrap = self.tk.Frame(header, bg=self.colors["window_bg"])
        mode_wrap.grid(row=0, column=1, sticky="e")
        self.mode_wrap = mode_wrap
        self.dark_button = self._make_button(mode_wrap, text="Dark", command=lambda: self._set_theme("dark"))
        self.dark_button.pack(side="left", padx=(0, 6))
        self.light_button = self._make_button(mode_wrap, text="Light", command=lambda: self._set_theme("light"))
        self.light_button.pack(side="left")

        self.card = self.tk.Frame(
            shell,
            bg=self.colors["card_bg"],
            highlightbackground=self.colors["card_border"],
            highlightthickness=1,
            bd=0,
        )
        self.card.pack(fill="both", expand=True)

        content = self.tk.Frame(self.card, bg=self.colors["card_bg"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        self.content = content
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)

        left = self.tk.Frame(content, bg=self.colors["card_bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left = left

        picker_header = self.tk.Frame(left, bg=self.colors["card_bg"])
        picker_header.pack(fill="x", pady=(0, 12))
        self.picker_header = picker_header
        self.picker_title = self._make_label(picker_header, "Color", size=15, bold=True)
        self.picker_title.pack(anchor="w")
        self.picker_subtitle = self._make_label(picker_header, "Pick directly from the spectrum, then fine-tune below.", fg=self.colors["muted"])
        self.picker_subtitle.pack(anchor="w", pady=(3, 0))

        picker_area = self.tk.Frame(left, bg=self.colors["card_bg"])
        picker_area.pack()
        self.picker_area = picker_area

        self.spectrum_canvas = self.tk.Canvas(
            picker_area,
            width=SPECTRUM_SIZE,
            height=SPECTRUM_SIZE,
            bg=self.colors["picker_bg"],
            highlightthickness=1,
            highlightbackground=self.colors["field_border"],
            bd=0,
        )
        self.spectrum_canvas.grid(row=0, column=0, padx=(0, 10))
        self.spectrum_image = self.tk.PhotoImage(width=SPECTRUM_SIZE, height=SPECTRUM_SIZE)
        self.spectrum_canvas.create_image(0, 0, anchor="nw", image=self.spectrum_image)
        self.spectrum_marker_outer = self.spectrum_canvas.create_oval(0, 0, 0, 0, outline="#ffffff", width=4)
        self.spectrum_marker_inner = self.spectrum_canvas.create_oval(0, 0, 0, 0, outline=self.colors["text"], width=2)
        self.spectrum_canvas.bind("<Button-1>", self._on_spectrum_event)
        self.spectrum_canvas.bind("<B1-Motion>", self._on_spectrum_event)

        hue_wrap = self.tk.Frame(picker_area, bg=self.colors["card_bg"])
        hue_wrap.grid(row=0, column=1, sticky="ns")
        self.hue_wrap = hue_wrap
        self.hue_label = self._make_label(hue_wrap, "Hue", size=10, bold=True, fg=self.colors["muted"])
        self.hue_label.pack(anchor="w", pady=(0, 8))
        self.hue_canvas = self.tk.Canvas(
            hue_wrap,
            width=HUE_BAR_WIDTH,
            height=SPECTRUM_SIZE,
            bg=self.colors["picker_bg"],
            highlightthickness=1,
            highlightbackground=self.colors["field_border"],
            bd=0,
        )
        self.hue_canvas.pack()
        self.hue_image = self.tk.PhotoImage(width=HUE_BAR_WIDTH, height=SPECTRUM_SIZE)
        self.hue_canvas.create_image(0, 0, anchor="nw", image=self.hue_image)
        self.hue_marker_outer = self.hue_canvas.create_rectangle(0, 0, 0, 0, outline="#ffffff", width=3)
        self.hue_marker_inner = self.hue_canvas.create_rectangle(0, 0, 0, 0, outline=self.colors["text"], width=1)
        self.hue_canvas.bind("<Button-1>", self._on_hue_event)
        self.hue_canvas.bind("<B1-Motion>", self._on_hue_event)

        presets = self.tk.Frame(left, bg=self.colors["card_bg"])
        presets.pack(fill="x", pady=(16, 0))
        self.presets = presets
        self.presets_label = self._make_label(presets, "Presets", size=10, bold=True, fg=self.colors["muted"])
        self.presets_label.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))
        self.preset_buttons = []
        for index, (name, value) in enumerate(PRESET_COLOURS):
            button = self.tk.Button(
                presets,
                text=name,
                bg=f"#{value}",
                fg="#111111" if name in {"Sun"} else "#ffffff",
                activebackground=f"#{value}",
                activeforeground="#111111" if name in {"Sun"} else "#ffffff",
                relief="flat",
                bd=0,
                padx=10,
                pady=8,
                width=7,
                font=("Helvetica", 9, "bold"),
                highlightthickness=0,
                cursor="hand2",
                command=lambda v=value: self.set_colour(v),
            )
            button.grid(row=1, column=index, padx=(0, 8), sticky="w")
            self.preset_buttons.append(button)

        right = self.tk.Frame(content, bg=self.colors["card_bg"], width=282)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        self.right = right

        self.preview_card = self.tk.Frame(
            right,
            bg=self.colors["preview_bg"],
            highlightbackground=self.colors["field_border"],
            highlightthickness=1,
            bd=0,
        )
        self.preview_card.pack(fill="x")
        preview_inner = self.tk.Frame(self.preview_card, bg=self.colors["preview_bg"])
        preview_inner.pack(fill="both", expand=True, padx=16, pady=16)
        self.preview_inner = preview_inner

        top_row = self.tk.Frame(preview_inner, bg=self.colors["preview_bg"])
        top_row.pack(fill="x")
        self.preview_title = self._make_label(top_row, "Live Preview", size=13, bold=True, bg=self.colors["preview_bg"])
        self.preview_title.pack(anchor="w")
        self._make_label(top_row, "", bg=self.colors["preview_bg"]).pack()

        self.preview = self.tk.Canvas(preview_inner, width=248, height=150, bg=self.colors["preview_bg"], bd=0, highlightthickness=0)
        self.preview.pack(pady=(12, 10))
        self.preview_glow = self.preview.create_oval(56, 18, 192, 128, fill="#0ea5e9", outline="", stipple="gray25")
        self.preview_back = self.preview.create_oval(74, 32, 174, 122, fill=self.colors["field_bg"], outline=self.colors["field_border"], width=2)
        self.preview_rect = self.preview.create_oval(84, 42, 164, 112, fill="#0ea5e9", outline="#ffffff", width=2)
        self.hex_badge = self.preview.create_text(124, 140, text="#0EA5E9", fill=self.colors["text"], font=("Helvetica", 15, "bold"))

        self.device_title = self._make_label(preview_inner, "Device", size=10, bold=True, fg=self.colors["muted"], bg=self.colors["preview_bg"])
        self.device_title.pack(anchor="w", pady=(2, 4))
        self.device_text = self.tk.Label(
            preview_inner,
            textvariable=self.device_label,
            bg=self.colors["preview_bg"],
            fg=self.colors["muted"],
            font=("Helvetica", 10),
            justify="left",
            wraplength=236,
        )
        self.device_text.pack(anchor="w")

        controls = self.tk.Frame(right, bg=self.colors["card_bg"])
        controls.pack(fill="x", pady=(14, 0))
        self.controls = controls

        self.values_title = self._make_label(controls, "Values", size=13, bold=True)
        self.values_title.pack(anchor="w")
        fields = self.tk.Frame(controls, bg=self.colors["card_bg"])
        fields.pack(fill="x", pady=(10, 0))
        self.fields = fields

        self._build_field_row(fields, "Hex", self.selected_colour, 14, self._on_hex_changed)
        self._build_field_row(fields, "Red", self.red_value, 8, self._on_rgb_commit)
        self._build_field_row(fields, "Green", self.green_value, 8, self._on_rgb_commit)
        self._build_field_row(fields, "Blue", self.blue_value, 8, self._on_rgb_commit)

        self._make_button(controls, text="Sync From RGB", command=self._apply_rgb_inputs).pack(fill="x", pady=(12, 0))

        live_wrap = self.tk.Frame(controls, bg=self.colors["card_bg"])
        live_wrap.pack(fill="x", pady=(12, 0))
        self.live_wrap = live_wrap
        self.live_mode_card = self.tk.Frame(
            live_wrap,
            bg=self.colors["field_bg"],
            highlightbackground=self.colors["field_border"],
            highlightthickness=1,
            bd=0,
        )
        self.live_mode_card.pack(fill="x")
        live_top = self.tk.Frame(self.live_mode_card, bg=self.colors["field_bg"])
        live_top.pack(fill="x", padx=12, pady=(12, 4))
        self.live_top = live_top
        self.live_mode_title = self._make_label(
            live_top,
            "Live Mode",
            size=11,
            bold=True,
            fg=self.colors["text"],
            bg=self.colors["field_bg"],
        )
        self.live_mode_title.pack(side="left")
        self.live_mode_button = self.tk.Button(
            live_top,
            text="OFF",
            command=self._toggle_live_mode,
            bg=self.colors["secondary"],
            fg=self.colors["text"],
            activebackground=self.colors["secondary_active"],
            activeforeground=self.colors["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            font=("Helvetica", 9, "bold"),
            highlightthickness=0,
            cursor="hand2",
            width=6,
        )
        self.live_mode_button.pack(side="right")
        self.live_mode_hint = self._make_label(
            self.live_mode_card,
            "Instantly applies color changes while you drag or edit values.",
            size=10,
            fg=self.colors["muted"],
            bg=self.colors["field_bg"],
        )
        self.live_mode_hint.pack(anchor="w", padx=12, pady=(0, 12))

        brightness = self.tk.Frame(right, bg=self.colors["card_bg"])
        brightness.pack(fill="x", pady=(16, 0))
        self.brightness_wrap = brightness
        self.brightness_title = self._make_label(brightness, "Brightness", size=13, bold=True)
        self.brightness_title.pack(anchor="w")
        self.brightness_scale = self.ttk.Scale(
            brightness,
            from_=0,
            to=3,
            orient="horizontal",
            variable=self.brightness,
            command=self._on_scale_changed,
            style="Keylight.Horizontal.TScale",
        )
        self.brightness_scale.pack(fill="x", pady=(10, 0))
        self.brightness_value = self._make_label(brightness, "Level 1 · Low", fg=self.colors["muted"])
        self.brightness_value.pack(anchor="e", pady=(8, 0))

        actions = self.tk.Frame(right, bg=self.colors["card_bg"])
        actions.pack(fill="x", pady=(18, 0))
        self.actions = actions
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        self.apply_colour_button = self._make_button(actions, text="Apply Colour", command=self.apply_colour, primary=True)
        self.apply_colour_button.grid(row=0, column=0, sticky="we", padx=(0, 6))
        self.apply_both_button = self._make_button(actions, text="Apply Both", command=self.apply_both)
        self.apply_both_button.grid(row=0, column=1, sticky="we", padx=(6, 0))
        self.refresh_button = self._make_button(actions, text="Refresh", command=self.refresh_device)
        self.refresh_button.grid(row=1, column=0, columnspan=2, sticky="we", pady=(10, 0))

        status_wrap = self.tk.Frame(right, bg=self.colors["card_bg"])
        status_wrap.pack(fill="x", pady=(16, 0))
        self.status_wrap = status_wrap
        self.status_indicator = self.tk.Frame(status_wrap, bg=self.colors["success"], width=8, height=8)
        self.status_indicator.pack(side="left", padx=(0, 10), pady=2)
        self.status_indicator.pack_propagate(False)
        self.status_label = self.tk.Label(
            status_wrap,
            textvariable=self.status,
            bg=self.colors["card_bg"],
            fg=self.colors["muted"],
            font=("Helvetica", 10),
            justify="left",
            wraplength=240,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

    def _build_field_row(self, parent, label: str, variable, width: int, handler) -> None:
        row = self.tk.Frame(parent, bg=self.colors["card_bg"])
        row.pack(fill="x", pady=4)
        self._make_label(row, label, size=10, bold=True, fg=self.colors["muted"]).pack(side="left")
        entry = self._make_entry(row, variable, width)
        entry.pack(side="right")
        entry.bind("<Return>", handler)
        entry.bind("<FocusOut>", handler)

    def _rgb_to_hex(self, red: int, green: int, blue: int) -> str:
        return f"{red:02x}{green:02x}{blue:02x}"

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        normalized = self._normalize_colour(value)
        return int(normalized[0:2], 16), int(normalized[2:4], 16), int(normalized[4:6], 16)

    def _render_colour(self, value: str) -> None:
        value = value.lower().removeprefix("#")
        colour = f"#{value}"
        self.preview.itemconfigure(self.preview_glow, fill=colour)
        self.preview.itemconfigure(self.preview_rect, fill=colour)
        self.preview.itemconfigure(self.hex_badge, text=colour.upper())

    def _set_status(self, message: str, *, is_error: bool = False) -> None:
        self.status.set(message)
        self.status_indicator.configure(bg=self.colors["error"] if is_error else self.colors["success"])

    def _set_theme(self, mode: str) -> None:
        self.theme_mode.set(mode)
        self.colors = THEMES[mode]
        self._configure_style()
        self._apply_theme()

    def _apply_theme(self) -> None:
        c = self.colors
        self.root.configure(bg=c["window_bg"])
        self.shell.configure(bg=c["window_bg"])
        self.header.configure(bg=c["window_bg"])
        self.title_wrap.configure(bg=c["window_bg"])
        self.mode_wrap.configure(bg=c["window_bg"])
        self.title_label.configure(bg=c["window_bg"], fg=c["text"])
        self.subtitle_label.configure(bg=c["window_bg"], fg=c["muted"])
        self.card.configure(bg=c["card_bg"], highlightbackground=c["card_border"])
        self.content.configure(bg=c["card_bg"])
        self.left.configure(bg=c["card_bg"])
        self.right.configure(bg=c["card_bg"])
        self.picker_header.configure(bg=c["card_bg"])
        self.picker_area.configure(bg=c["card_bg"])
        self.hue_wrap.configure(bg=c["card_bg"])
        self.presets.configure(bg=c["card_bg"])
        self.controls.configure(bg=c["card_bg"])
        self.fields.configure(bg=c["card_bg"])
        self.live_wrap.configure(bg=c["card_bg"])
        self.live_mode_card.configure(bg=c["field_bg"], highlightbackground=c["field_border"])
        self.live_top.configure(bg=c["field_bg"])
        self.brightness_wrap.configure(bg=c["card_bg"])
        self.actions.configure(bg=c["card_bg"])
        self.status_wrap.configure(bg=c["card_bg"])
        self.preview_card.configure(bg=c["preview_bg"], highlightbackground=c["field_border"])
        self.preview_inner.configure(bg=c["preview_bg"])
        self.preview.configure(bg=c["preview_bg"])
        self.device_text.configure(bg=c["preview_bg"], fg=c["muted"])
        self.status_label.configure(bg=c["card_bg"], fg=c["muted"])
        self.live_mode_title.configure(bg=c["field_bg"], fg=c["text"])
        self.live_mode_hint.configure(bg=c["field_bg"], fg=c["muted"])
        self.spectrum_canvas.configure(bg=c["picker_bg"], highlightbackground=c["field_border"])
        self.hue_canvas.configure(bg=c["picker_bg"], highlightbackground=c["field_border"])
        self.preview.itemconfigure(self.preview_back, fill=c["field_bg"], outline=c["field_border"])
        self.preview.itemconfigure(self.hex_badge, fill=c["text"])

        labels = [
            self.picker_title,
            self.values_title,
            self.brightness_title,
            self.preview_title,
            self.title_label,
        ]
        muted_labels = [
            self.picker_subtitle,
            self.hue_label,
            self.presets_label,
            self.device_title,
            self.brightness_value,
            self.subtitle_label,
        ]
        for widget in labels:
            widget.configure(bg=c["card_bg"] if widget not in {self.title_label} else c["window_bg"], fg=c["text"])
        self.preview_title.configure(bg=c["preview_bg"], fg=c["text"])
        self.device_title.configure(bg=c["preview_bg"], fg=c["muted"])
        for widget in muted_labels:
            if widget in {self.device_title}:
                continue
            bg = c["window_bg"] if widget is self.subtitle_label else c["card_bg"]
            widget.configure(bg=bg, fg=c["muted"])

        self.dark_button.configure(
            bg=c["primary"] if self.theme_mode.get() == "dark" else c["secondary"],
            fg="#ffffff" if self.theme_mode.get() == "dark" else c["text"],
            activebackground=c["primary_active"] if self.theme_mode.get() == "dark" else c["secondary_active"],
            activeforeground="#ffffff" if self.theme_mode.get() == "dark" else c["text"],
        )
        self.light_button.configure(
            bg=c["primary"] if self.theme_mode.get() == "light" else c["secondary"],
            fg="#ffffff" if self.theme_mode.get() == "light" else c["text"],
            activebackground=c["primary_active"] if self.theme_mode.get() == "light" else c["secondary_active"],
            activeforeground="#ffffff" if self.theme_mode.get() == "light" else c["text"],
        )
        self.apply_colour_button.configure(bg=c["primary"], activebackground=c["primary_active"])
        for button in (self.apply_both_button, self.refresh_button):
            button.configure(bg=c["secondary"], fg=c["text"], activebackground=c["secondary_active"], activeforeground=c["text"])

        self.brightness_scale.configure(style="Keylight.Horizontal.TScale")
        self._refresh_entries(self.fields)
        self._refresh_live_mode_button()
        self._render_colour(self.selected_colour.get())
        self._set_status(self.status.get(), is_error=self.status.get().startswith("Error:"))

    def _refresh_entries(self, parent) -> None:
        for child in parent.winfo_children():
            if isinstance(child, self.tk.Frame):
                child.configure(bg=self.colors["card_bg"])
                self._refresh_entries(child)
            elif isinstance(child, self.tk.Entry):
                child.configure(
                    bg=self.colors["field_bg"],
                    fg=self.colors["text"],
                    insertbackground=self.colors["text"],
                    highlightbackground=self.colors["field_border"],
                    highlightcolor=self.colors["primary"],
                )
            elif isinstance(child, self.tk.Label):
                current_fg = child.cget("fg")
                child.configure(
                    bg=self.colors["card_bg"],
                    fg=self.colors["muted"] if current_fg.lower() == THEMES["light"]["muted"] or current_fg.lower() == THEMES["dark"]["muted"] else self.colors["text"],
                )

    def _normalize_colour(self, value: str) -> str:
        normalized = value.strip().lower().removeprefix("#")
        if len(normalized) != 6 or any(ch not in "0123456789abcdef" for ch in normalized):
            raise ValidationError("color must be a 6-digit RGB hex value")
        return normalized

    def _clamp_byte(self, value: str) -> int:
        try:
            numeric = int(value.strip())
        except ValueError as exc:
            raise ValidationError("RGB values must be integers between 0 and 255") from exc
        if numeric < 0 or numeric > 255:
            raise ValidationError("RGB values must be integers between 0 and 255")
        return numeric

    def _render_spectrum(self) -> None:
        rows: list[str] = []
        for y in range(SPECTRUM_SIZE):
            row_pixels: list[str] = []
            value = 1 - (y / (SPECTRUM_SIZE - 1))
            for x in range(SPECTRUM_SIZE):
                saturation = x / (SPECTRUM_SIZE - 1)
                red, green, blue = colorsys.hsv_to_rgb(self.current_hue, saturation, value)
                row_pixels.append(self._rgb_to_hex(round(red * 255), round(green * 255), round(blue * 255)))
            rows.append("{" + " ".join(f"#{pixel}" for pixel in row_pixels) + "}")
        self.spectrum_image.put(" ".join(rows))

    def _render_hue_bar(self) -> None:
        rows: list[str] = []
        for y in range(SPECTRUM_SIZE):
            hue = y / (SPECTRUM_SIZE - 1)
            red, green, blue = colorsys.hsv_to_rgb(hue, 1, 1)
            pixel = f"#{self._rgb_to_hex(round(red * 255), round(green * 255), round(blue * 255))}"
            rows.append("{" + " ".join([pixel] * HUE_BAR_WIDTH) + "}")
        self.hue_image.put(" ".join(rows))

    def _update_picker_markers(self) -> None:
        x = self.current_saturation * (SPECTRUM_SIZE - 1)
        y = (1 - self.current_value) * (SPECTRUM_SIZE - 1)
        outer = (x - 9, y - 9, x + 9, y + 9)
        inner = (x - 7, y - 7, x + 7, y + 7)
        self.spectrum_canvas.coords(self.spectrum_marker_outer, *outer)
        self.spectrum_canvas.coords(self.spectrum_marker_inner, *inner)

        hue_y = self.current_hue * (SPECTRUM_SIZE - 1)
        outer_bar = (1, hue_y - 6, HUE_BAR_WIDTH - 1, hue_y + 6)
        inner_bar = (3, hue_y - 4, HUE_BAR_WIDTH - 3, hue_y + 4)
        self.hue_canvas.coords(self.hue_marker_outer, *outer_bar)
        self.hue_canvas.coords(self.hue_marker_inner, *inner_bar)

    def _sync_ui_to_current_colour(self) -> None:
        red, green, blue = colorsys.hsv_to_rgb(self.current_hue, self.current_saturation, self.current_value)
        red_byte = round(red * 255)
        green_byte = round(green * 255)
        blue_byte = round(blue * 255)
        hex_value = self._rgb_to_hex(red_byte, green_byte, blue_byte)

        self._syncing_inputs = True
        self.selected_colour.set(hex_value)
        self.red_value.set(str(red_byte))
        self.green_value.set(str(green_byte))
        self.blue_value.set(str(blue_byte))
        self._syncing_inputs = False

        self._render_colour(hex_value)
        self._update_picker_markers()
        self._queue_live_apply()

    def _sync_from_hex(self, value: str) -> None:
        red, green, blue = self._hex_to_rgb(value)
        hue, saturation, brightness = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        self.current_hue = hue
        self.current_saturation = saturation
        self.current_value = brightness
        self._render_spectrum()
        self._sync_ui_to_current_colour()

    def _on_hex_changed(self, _event=None) -> None:
        if self._syncing_inputs:
            return
        value = self.selected_colour.get()
        try:
            normalized = self._normalize_colour(value)
        except ValidationError:
            return
        self._sync_from_hex(normalized)

    def _on_rgb_commit(self, _event=None) -> None:
        if self._syncing_inputs:
            return
        self._apply_rgb_inputs()

    def _apply_rgb_inputs(self) -> None:
        try:
            red = self._clamp_byte(self.red_value.get())
            green = self._clamp_byte(self.green_value.get())
            blue = self._clamp_byte(self.blue_value.get())
        except ValidationError as exc:
            self._set_status(f"Error: {exc}", is_error=True)
            return
        self._sync_from_hex(self._rgb_to_hex(red, green, blue))
        self._set_status("RGB values updated")

    def _on_spectrum_event(self, event) -> None:
        x = min(max(event.x, 0), SPECTRUM_SIZE - 1)
        y = min(max(event.y, 0), SPECTRUM_SIZE - 1)
        self.current_saturation = x / (SPECTRUM_SIZE - 1)
        self.current_value = 1 - (y / (SPECTRUM_SIZE - 1))
        self._sync_ui_to_current_colour()

    def _on_hue_event(self, event) -> None:
        y = min(max(event.y, 0), SPECTRUM_SIZE - 1)
        self.current_hue = y / (SPECTRUM_SIZE - 1)
        self._render_spectrum()
        self._sync_ui_to_current_colour()

    def _on_scale_changed(self, _value: str) -> None:
        level = round(self.brightness.get())
        self.brightness.set(level)
        names = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
        self.brightness_value.configure(text=f"Level {level} · {names[level]}")

    def _toggle_live_mode(self) -> None:
        self.live_mode.set(not self.live_mode.get())
        self._on_live_mode_toggle()

    def _refresh_live_mode_button(self) -> None:
        if self.live_mode.get():
            self.live_mode_card.configure(
                bg=self.colors["primary"],
                highlightbackground=self.colors["primary"],
            )
            self.live_top.configure(bg=self.colors["primary"])
            self.live_mode_title.configure(bg=self.colors["primary"], fg="#ffffff")
            self.live_mode_hint.configure(bg=self.colors["primary"], fg="#d6ecff")
            self.live_mode_button.configure(
                text="ON",
                bg="#ffffff",
                fg=self.colors["primary"],
                activebackground="#f2f8ff",
                activeforeground=self.colors["primary"],
            )
        else:
            self.live_mode_card.configure(
                bg=self.colors["field_bg"],
                highlightbackground=self.colors["field_border"],
            )
            self.live_top.configure(bg=self.colors["field_bg"])
            self.live_mode_title.configure(bg=self.colors["field_bg"], fg=self.colors["text"])
            self.live_mode_hint.configure(bg=self.colors["field_bg"], fg=self.colors["muted"])
            self.live_mode_button.configure(
                text="OFF",
                bg=self.colors["secondary"],
                fg=self.colors["text"],
                activebackground=self.colors["secondary_active"],
                activeforeground=self.colors["text"],
            )

    def _on_live_mode_toggle(self) -> None:
        self._refresh_live_mode_button()
        if self.live_mode.get():
            self._set_status("Live mode enabled")
            self._queue_live_apply(immediate=True)
        else:
            if self._live_after_id is not None:
                self.root.after_cancel(self._live_after_id)
                self._live_after_id = None
            self._set_status("Live mode disabled")

    def _queue_live_apply(self, *, immediate: bool = False) -> None:
        if not self.live_mode.get() or self._syncing_inputs:
            return
        if self._live_after_id is not None:
            self.root.after_cancel(self._live_after_id)
            self._live_after_id = None
        delay = 0 if immediate else 90
        self._live_after_id = self.root.after(delay, self._run_live_apply)

    def _run_live_apply(self) -> None:
        self._live_after_id = None
        if not self.live_mode.get():
            return
        try:
            colour = self._normalize_colour(self.selected_colour.get())
            run_apply(
                colour_hex=colour,
                brightness=None,
                dry_run=False,
                force=False,
            )
            self._set_status(f"Live #{colour.upper()}")
        except AsusKeylightError as exc:
            self._set_status(f"Error: {exc}", is_error=True)

    def set_colour(self, value: str) -> None:
        self._sync_from_hex(value)

    def refresh_device(self) -> None:
        try:
            target = discover_keyboard()
            ensure_supported_model(target, force=False)
            brightness = current_brightness(target)
            max_level = max_brightness(target)
            self.brightness.set(brightness)
            self._on_scale_changed(str(brightness))
            self.device_label.set(f"{target.product_name}\n{target.hidraw_path} · brightness 0..{max_level}")
            self._set_status("Device ready")
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
                self._set_status(f"Applied #{colour.upper()}")
            else:
                self._set_status(f"Applied #{colour.upper()} with brightness {brightness}")
        except AsusKeylightError as exc:
            self._set_status(f"Error: {exc}", is_error=True)


def main() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "tkinter is not installed. Install the distro package first, for example: sudo apt install python3-tk"
        ) from exc

    root = tk.Tk()
    AsusKeylightApp(root, tk, ttk)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
