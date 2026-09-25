"""Цветовые темы: какие цвета можно менять и готовые наборы."""

from __future__ import annotations

import re

# (ключ, подпись в окне настроек), сгруппировано по разделам.
COLOR_GROUPS = [
    ("Стол", [
        ("table", "Сукно стола"),
        ("slot", "Пустые места"),
        ("slot_mark", "Рамка и буквы пустых мест"),
        ("status_bg", "Нижняя строка: фон"),
        ("status_fg", "Нижняя строка: текст"),
        ("highlight", "Подсказка"),
    ]),
    ("Лицевая сторона", [
        ("card_face", "Фон карты"),
        ("card_edge", "Край карты"),
        ("spades", "Пики ♠"),
        ("hearts", "Черви ♥"),
        ("diamonds", "Бубны ♦"),
        ("clubs", "Трефы ♣"),
    ]),
    ("Рубашка", [
        ("back", "Основной цвет"),
        ("back_inner", "Внутренняя часть"),
        ("back_pattern", "Узор и окантовка"),
    ]),
]
COLOR_KEYS = [key for _, items in COLOR_GROUPS for key, _ in items]
SUIT_KEYS = ("spades", "hearts", "diamonds", "clubs")  # в порядке SUITS

CLASSIC = {
    "table": "#0b6e35",
    "slot": "#08572a",
    "slot_mark": "#2f8f57",
    "status_bg": "#08572a",
    "status_fg": "#ffffff",
    "highlight": "#ffd84d",
    "card_face": "#fdfdf8",
    "card_edge": "#6b6b6b",
    "spades": "#1a1a1a",
    "hearts": "#c8102e",
    "diamonds": "#c8102e",
    "clubs": "#1a1a1a",
    "back": "#1f4fa8",
    "back_inner": "#3a6fd1",
    "back_pattern": "#dfe8ff",
}

PRESETS = {
    "Классика": CLASSIC,
    "Синее сукно": {
        **CLASSIC,
        "table": "#1b4f8a", "slot": "#153f6e", "slot_mark": "#4b7fb8",
        "status_bg": "#123658",
        "back": "#a31d2b", "back_inner": "#c8404d", "back_pattern": "#ffe3e6",
    },
    "Бордо": {
        **CLASSIC,
        "table": "#6d1a2a", "slot": "#561420", "slot_mark": "#9a4455",
        "status_bg": "#4a111c",
        "back": "#2e5e3e", "back_inner": "#4c8a5f", "back_pattern": "#e2f5e8",
    },
    "Ночь": {
        "table": "#1e1f24", "slot": "#16171b", "slot_mark": "#44464f",
        "status_bg": "#141519", "status_fg": "#c9c9c9", "highlight": "#4fc3f7",
        "card_face": "#d9d9d2", "card_edge": "#3a3a3a",
        "spades": "#111111", "hearts": "#b3122a", "diamonds": "#b3122a", "clubs": "#111111",
        "back": "#3b3f4a", "back_inner": "#555b69", "back_pattern": "#aab0bf",
    },
    "Четыре масти": {
        **CLASSIC,
        "diamonds": "#1f5fd1", "clubs": "#1f8a3a",
    },
}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def merge_colors(saved: object) -> dict:
    """Классическая тема, поверх которой наложены сохранённые цвета (только корректные)."""
    colors = dict(CLASSIC)
    if isinstance(saved, dict):
        for key in COLOR_KEYS:
            value = saved.get(key)
            if isinstance(value, str) and _HEX.match(value):
                colors[key] = value.lower()
    return colors


def preset_name(colors: dict) -> str | None:
    for name, preset in PRESETS.items():
        if all(colors[k] == preset[k] for k in COLOR_KEYS):
            return name
    return None
