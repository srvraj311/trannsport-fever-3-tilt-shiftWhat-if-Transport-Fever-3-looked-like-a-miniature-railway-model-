"""The TF3 Tilt-Shift window: sliders for every setting, Apply / Restore / Reset buttons."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, AUTHOR, __version__, game, settings, shaders

RELOAD_HINT = "In game press Right Alt + T to reload shaders (or restart the game)."
AUTO_APPLY_DELAY_MS = 400


def _decimals(step: float) -> int:
    return 0 if step >= 1 else 2


class SettingRow:
    """One setting: label, control and value text, plus a help line underneath."""

    def __init__(self, parent: ttk.Frame, row: int, setting: settings.Setting, on_change):
        self.setting = setting
        self.on_change = on_change
        self.var = tk.DoubleVar()
        self.value_text = tk.StringVar()

        ttk.Label(parent, text=setting.label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
        if setting.kind == "check":
            self.bool_var = tk.BooleanVar()
            ttk.Checkbutton(parent, variable=self.bool_var, command=self._changed).grid(row=row, column=1, sticky="w",
                                                                                     pady=(8, 0))
        elif setting.kind == "choice":
            self.combo = ttk.Combobox(parent, state="readonly", width=16, values=[label for _, label in setting.choices])
            self.combo.bind("<<ComboboxSelected>>", lambda _e: self._changed())
            self.combo.grid(row=row, column=1, sticky="w", pady=(8, 0))
        else:
            ttk.Scale(parent, from_=setting.low, to=setting.high, variable=self.var,
                      command=lambda _v: self._changed()).grid(row=row, column=1, sticky="ew", pady=(8, 0))
            ttk.Label(parent, textvariable=self.value_text, width=9, anchor="e").grid(row=row, column=2, sticky="e",
                                                                                      pady=(8, 0))
        if setting.help:
            ttk.Label(parent, text=setting.help, style="Help.TLabel", wraplength=560).grid(
                row=row + 1, column=0, columnspan=3, sticky="w")

    def get(self) -> float:
        s = self.setting
        if s.kind == "check":
            return 1.0 if self.bool_var.get() else 0.0
        if s.kind == "choice":
            return float(s.choices[max(self.combo.current(), 0)][0])
        return round(round(self.var.get() / s.step) * s.step, 4)     # snap to the slider step

    def set(self, value: float) -> None:
        s = self.setting
        if s.kind == "check":
            self.bool_var.set(bool(value))
        elif s.kind == "choice":
            self.combo.current([v for v, _ in s.choices].index(int(value)))
        else:
            self.var.set(value)
        self._show()

    def _show(self) -> None:
        if self.setting.kind == "slider":
            text = f"{self.get():.{_decimals(self.setting.step)}f}"
            self.value_text.set(f"{text} {self.setting.unit}".strip())

    def _changed(self) -> None:
        self._show()
        self.on_change()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.rows: dict[str, SettingRow] = {}
        self.pending_apply = None
        values, saved_dir = settings.load()
        found = saved_dir if saved_dir and game.is_game_dir(Path(saved_dir)) else game.find_game()
        self.game_dir = tk.StringVar(value=str(found) if found else "")
        self.auto_apply = tk.BooleanVar(value=False)
        self.status = tk.StringVar()

        root.title(f"{APP_NAME} {__version__}")
        root.minsize(700, 640)
        self._styles()
        self._build()
        self._load_values(values)
        self._show_game_state()
        root.protocol("WM_DELETE_WINDOW", self._close)

    # ---- layout ----
    def _styles(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("Help.TLabel", foreground="#6b6b6b", font=("Segoe UI", 8))
        style.configure("Status.TLabel", foreground="#1f5f99")
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10))

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, style="Help.TLabel",
                  text=f"Cities: Skylines-style tilt-shift for Transport Fever 3  -  v{__version__} by {AUTHOR}").pack(
            anchor="w", pady=(0, 10))

        folder = ttk.Frame(outer)
        folder.pack(fill="x")
        ttk.Label(folder, text="Game folder").pack(side="left")
        ttk.Entry(folder, textvariable=self.game_dir, state="readonly").pack(side="left", fill="x", expand=True,
                                                                              padx=8)
        ttk.Button(folder, text="Browse...", command=self._browse).pack(side="left")

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True, pady=12)
        for tab in settings.TABS:
            frame = ttk.Frame(notebook, padding=12)
            frame.columnconfigure(1, weight=1)
            notebook.add(frame, text=tab)
            row = 0
            for setting in settings.SETTINGS:
                if setting.tab == tab:
                    self.rows[setting.key] = SettingRow(frame, row, setting, self._changed)
                    row += 2

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Apply to game", style="Accent.TButton", command=self.apply).pack(side="left")
        ttk.Checkbutton(buttons, text="Apply automatically", variable=self.auto_apply).pack(side="left", padx=12)
        ttk.Button(buttons, text="Reset to defaults", command=self.reset).pack(side="right")
        ttk.Button(buttons, text="Restore original shaders", command=self.restore).pack(side="right", padx=8)

        ttk.Label(outer, textvariable=self.status, style="Status.TLabel", wraplength=660).pack(anchor="w", pady=(10, 0))

    # ---- values ----
    def _load_values(self, values: dict[str, float]) -> None:
        for key, row in self.rows.items():
            row.set(values[key])

    def values(self) -> dict[str, float]:
        return {key: row.get() for key, row in self.rows.items()}

    def _changed(self) -> None:
        if self.auto_apply.get():
            if self.pending_apply:
                self.root.after_cancel(self.pending_apply)
            self.pending_apply = self.root.after(AUTO_APPLY_DELAY_MS, self.apply)

    # ---- actions ----
    def _game(self) -> Path | None:
        path = Path(self.game_dir.get()) if self.game_dir.get() else None
        if path and game.is_game_dir(path):
            return path
        self.status.set("Transport Fever 3 not found. Use Browse... to pick its install folder.")
        return None

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(title="Transport Fever 3 install folder")
        if not chosen:
            return
        if not game.is_game_dir(Path(chosen)):
            messagebox.showerror(APP_NAME, f"{chosen}\n\ndoes not look like a Transport Fever 3 install "
                                           f"(no {game.GAME_EXE} and shaders).")
            return
        self.game_dir.set(chosen)
        self._show_game_state()

    def _show_game_state(self) -> None:
        path = self._game()
        if path:
            patched = game.is_patched(path, game.COMPOSE) or game.is_patched(path, game.SSR)
            self.status.set("The game currently uses the tilt-shift shaders." if patched
                            else "The game currently uses its original shaders.")

    def apply(self) -> None:
        self.pending_apply = None
        path = self._game()
        if not path:
            return
        try:
            done = game.apply(path, self.values())
        except (shaders.PatchError, OSError) as error:
            self.status.set(f"Not applied: {error}")
            return
        settings.save(self.values(), str(path))
        self.status.set(("Applied: " + ", ".join(done) + ". " if done else "Nothing to apply. ") + RELOAD_HINT)

    def restore(self) -> None:
        path = self._game()
        if not path:
            return
        try:
            done = game.restore_all(path)
        except OSError as error:
            self.status.set(f"Not restored: {error}")
            return
        self.status.set(("Restored the original shaders. " + RELOAD_HINT) if done
                        else "The game already uses its original shaders.")

    def reset(self) -> None:
        self._load_values(settings.defaults())
        self.status.set("Settings reset to the defaults. Press Apply to game to use them.")
        self._changed()

    def _close(self) -> None:
        try:
            settings.save(self.values(), self.game_dir.get() or None)
        except OSError:
            pass
        self.root.destroy()


def main() -> None:
    try:                                   # crisp text on high-DPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
