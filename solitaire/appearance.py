"""Окно «Оформление»: выбор цветов стола, карт и рубашки."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
from typing import Callable

from solitaire.theme import COLOR_GROUPS, PRESETS, preset_name

CUSTOM = "Своя"


def _text_color(hex_color: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#000000" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


class AppearanceDialog:
    def __init__(self, parent: tk.Tk, colors: dict, apply: Callable[[dict], None]):
        self.apply = apply
        self.original = dict(colors)
        self.colors = dict(colors)
        self.swatches: dict[str, tk.Button] = {}

        win = self.win = tk.Toplevel(parent)
        win.title("Оформление")
        win.transient(parent)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.cancel)
        win.bind("<Escape>", lambda e: self.cancel())

        top = tk.Frame(win, padx=12, pady=10)
        top.pack(fill=tk.X)
        tk.Label(top, text="Готовая тема:").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value=preset_name(self.colors) or CUSTOM)
        menu = tk.OptionMenu(top, self.preset_var, *PRESETS, command=self.choose_preset)
        menu.config(width=14)
        menu.pack(side=tk.LEFT, padx=8)

        body = tk.Frame(win, padx=12)
        body.pack(fill=tk.BOTH)
        for column, (title, items) in enumerate(COLOR_GROUPS):
            frame = tk.LabelFrame(body, text=title, padx=8, pady=6)
            frame.grid(row=0, column=column, sticky="n", padx=4)
            for row, (key, label) in enumerate(items):
                tk.Label(frame, text=label, anchor="w").grid(row=row, column=0, sticky="w", pady=2)
                swatch = tk.Button(frame, width=8, relief=tk.GROOVE, bd=2,
                                   command=lambda k=key, l=label: self.pick(k, l))
                swatch.grid(row=row, column=1, padx=(8, 0), pady=2)
                self.swatches[key] = swatch
        tk.Label(win, text="Щёлкните по цвету, чтобы изменить его. Изменения сразу видны на столе.",
                 fg="#555555", padx=12, pady=6).pack(anchor="w")

        buttons = tk.Frame(win, padx=12, pady=10)
        buttons.pack(fill=tk.X)
        tk.Button(buttons, text="Сбросить к классике",
                  command=lambda: self.choose_preset("Классика")).pack(side=tk.LEFT)
        tk.Button(buttons, text="Готово", width=10, command=self.win.destroy).pack(side=tk.RIGHT)
        tk.Button(buttons, text="Отмена", width=10, command=self.cancel).pack(side=tk.RIGHT, padx=6)

        self.refresh()
        win.grab_set()
        win.focus_set()

    def refresh(self) -> None:
        for key, swatch in self.swatches.items():
            color = self.colors[key]
            swatch.config(text=color, bg=color, activebackground=color,
                          fg=_text_color(color), activeforeground=_text_color(color))
        self.preset_var.set(preset_name(self.colors) or CUSTOM)

    def update(self) -> None:
        self.refresh()
        self.apply(dict(self.colors))

    def pick(self, key: str, label: str) -> None:
        _, color = colorchooser.askcolor(self.colors[key], parent=self.win, title=label)
        if color:
            self.colors[key] = color.lower()
            self.update()

    def choose_preset(self, name: str) -> None:
        self.colors = dict(PRESETS[name])
        self.update()

    def cancel(self) -> None:
        self.apply(self.original)
        self.win.destroy()
