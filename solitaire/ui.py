"""Графический интерфейс пасьянса на Tkinter."""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:  # pragma: no cover - зависит от системы
    sys.stderr.write(
        "Не найден модуль tkinter.\n"
        "Установите его: sudo apt install python3-tk  (Debian/Ubuntu/Mint)\n"
        "                sudo dnf install python3-tkinter  (Fedora)\n"
        "                sudo pacman -S tk  (Arch/Manjaro)\n"
    )
    raise SystemExit(1)

from solitaire import __version__
from solitaire.appearance import AppearanceDialog
from solitaire.theme import SUIT_KEYS, merge_colors
from solitaire.game import (
    FOUNDATION,
    RANKS,
    STOCK,
    SUITS,
    TABLEAU,
    WASTE,
    DRAW_HINT,
    Card,
    Game,
    Pile,
)

FONT = "DejaVu Sans"

MARGIN = 16
DRAG_THRESHOLD = 4

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "solitaire-linux"
CONFIG_FILE = CONFIG_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "draw_count": 1,
    "auto_finish": True,
    "played": 0,
    "won": 0,
    "best_time": None,
    "best_score": 0,
}


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        settings.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    if settings["draw_count"] not in (1, 3):
        settings["draw_count"] = 1
    return settings


def save_settings(settings: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def format_time(seconds: float | int | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class SolitaireApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self.colors = merge_colors(self.settings.get("colors"))
        root.title("Косынка")
        root.geometry("980x720")
        root.minsize(560, 420)
        self._set_icon()

        self.canvas = tk.Canvas(root, bg=self.colors["table"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status = tk.Label(
            root, anchor="w", padx=10, pady=3, bg=self.colors["status_bg"],
            fg=self.colors["status_fg"], font=(FONT, 10)
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

        self.draw_var = tk.IntVar(value=self.settings["draw_count"])
        self.auto_var = tk.BooleanVar(value=self.settings["auto_finish"])
        self._build_menu()

        self.card_w = 90
        self.card_h = 126
        self.hitboxes: list[tuple[Pile, int, float, float, float, float]] = []
        self.pile_rects: dict[Pile, tuple[float, float, float, float]] = {}
        self.drag: dict | None = None
        self.celebrating = False
        self.anim_job: str | None = None
        self.hint_job: str | None = None
        self.started_at: float | None = None
        self.elapsed = 0.0

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Button-3>", lambda e: self.collect())
        root.bind("<F2>", lambda e: self.new_game())
        root.bind("<Control-n>", lambda e: self.new_game())
        root.bind("<Control-r>", lambda e: self.restart())
        root.bind("<Control-z>", lambda e: self.undo())
        root.bind("<BackSpace>", lambda e: self.undo())
        root.bind("<KeyPress>", self.on_letter_key)
        root.bind("<space>", lambda e: self.show_hint())
        root.bind("<Control-q>", lambda e: self.quit())
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self.game = Game(self.settings["draw_count"])
        self.counted = False
        self.tick()

    # ------------------------------------------------------------------ окно
    def _set_icon(self) -> None:
        path = Path(__file__).resolve().parent.parent / "data" / "solitaire-linux.png"
        try:
            self._icon = tk.PhotoImage(file=str(path))
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        game_menu = tk.Menu(menubar, tearoff=False)
        game_menu.add_command(label="Новая игра", accelerator="F2", command=self.new_game)
        game_menu.add_command(label="Начать эту раздачу заново", accelerator="Ctrl+R", command=self.restart)
        game_menu.add_separator()
        game_menu.add_command(label="Отменить ход", accelerator="M", command=self.undo)
        game_menu.add_command(label="Открыть карту из колоды", accelerator="N", command=self.deal_from_stock)
        game_menu.add_command(label="Положить карту из сброса", accelerator="B", command=self.place_waste_card)
        game_menu.add_command(label="Подсказка", accelerator="Пробел", command=self.show_hint)
        game_menu.add_command(label="Собрать карты в дом", accelerator="ПКМ", command=self.collect)
        game_menu.add_separator()
        game_menu.add_command(label="Статистика", command=self.show_stats)
        game_menu.add_separator()
        game_menu.add_command(label="Выход", accelerator="Ctrl+Q", command=self.quit)
        menubar.add_cascade(label="Игра", menu=game_menu)

        opts = tk.Menu(menubar, tearoff=False)
        opts.add_radiobutton(label="Сдавать по 1 карте", variable=self.draw_var, value=1, command=self.change_draw)
        opts.add_radiobutton(label="Сдавать по 3 карты", variable=self.draw_var, value=3, command=self.change_draw)
        opts.add_separator()
        opts.add_command(label="Оформление…", command=self.open_appearance)
        opts.add_separator()
        opts.add_checkbutton(
            label="Автоматически доигрывать", variable=self.auto_var, command=self.change_auto
        )
        menubar.add_cascade(label="Настройки", menu=opts)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Как играть", command=self.show_help)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)
        self.root.config(menu=menubar)

    # ------------------------------------------------------------------ команды
    def new_game(self, seed: int | None = None) -> None:
        self.stop_animation()
        self.game = Game(self.draw_var.get(), seed)
        self.counted = False
        self.started_at = None
        self.elapsed = 0.0
        self.redraw()

    def restart(self) -> None:
        self.new_game(self.game.seed)

    def change_draw(self) -> None:
        self.settings["draw_count"] = self.draw_var.get()
        save_settings(self.settings)
        if self.game.moves == 0 or messagebox.askyesno(
            "Косынка", "Начать новую игру с новыми правилами сдачи?", parent=self.root
        ):
            self.new_game()

    def open_appearance(self) -> None:
        if not self.celebrating:
            AppearanceDialog(self.root, self.colors, self.set_colors)

    def set_colors(self, colors: dict) -> None:
        self.colors = colors
        self.settings["colors"] = colors
        save_settings(self.settings)
        self.canvas.config(bg=colors["table"])
        self.status.config(bg=colors["status_bg"], fg=colors["status_fg"])
        self.redraw()

    def change_auto(self) -> None:
        self.settings["auto_finish"] = self.auto_var.get()
        save_settings(self.settings)
        self.after_move()

    def undo(self) -> None:
        if self.celebrating or self.anim_job or self.game.is_won():
            return
        if self.game.undo():
            self.redraw()

    def deal_from_stock(self) -> None:
        if self.celebrating or self.anim_job:
            return
        if self.game.draw():
            self.after_move()

    def on_letter_key(self, event) -> None:
        """N, B и M работают в любой раскладке (в русской это Т, И и Ь)."""
        if event.state & 0x4:  # с Ctrl — это другие сочетания
            return
        keysym = event.keysym.lower()
        actions = {"n": self.deal_from_stock, "b": self.place_waste_card, "m": self.undo}
        if keysym not in actions:
            if len(keysym) == 1 and keysym.isascii():
                return  # другая латинская буква
            # Нелатинская раскладка: узнаём клавишу по её положению (коды X11).
            keysym = {57: "n", 56: "b", 58: "m"}.get(event.keycode, "")
        if keysym in actions:
            actions[keysym]()

    def place_waste_card(self) -> None:
        """Положить открытую карту из сброса туда, куда она подходит."""
        if self.celebrating or self.anim_job or not self.game.waste:
            return
        src, index = (WASTE, 0), len(self.game.waste) - 1
        dest = self.game.best_target(src, index)
        if dest and self.game.move(src, index, dest):
            self.after_move()
        else:
            self.root.bell()

    def show_hint(self) -> None:
        if self.celebrating or self.anim_job or self.game.is_won():
            return
        self.canvas.delete("hint")
        if self.hint_job:
            self.root.after_cancel(self.hint_job)
        hint = self.game.hint()
        if hint is None:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            self.canvas.create_rectangle(w / 2 - 170, h / 2 - 34, w / 2 + 170, h / 2 + 34,
                                         fill=self.colors["slot"], outline=self.colors["highlight"],
                                         width=2, tags="hint")
            self.canvas.create_text(w / 2, h / 2, text="Ходов больше нет", fill=self.colors["status_fg"],
                                    font=(FONT, -24, "bold"), tags="hint")
        elif hint == DRAW_HINT:
            self.highlight(self.pile_rects[(STOCK, 0)])
        else:
            src, index, dest = hint
            boxes = [b for b in self.hitboxes if b[0] == src and b[1] >= index]
            self.highlight((boxes[0][2], boxes[0][3], boxes[-1][4], boxes[-1][5]))
            dest_boxes = [b for b in self.hitboxes if b[0] == dest]
            if dest_boxes:
                self.highlight(dest_boxes[-1][2:])
            else:
                x1, y1, x2, _ = self.pile_rects[dest]
                self.highlight((x1, y1, x2, y1 + self.card_h))
        self.hint_job = self.root.after(1500, self.clear_hint)

    def clear_hint(self) -> None:
        self.hint_job = None
        self.canvas.delete("hint")

    def highlight(self, rect) -> None:
        x1, y1, x2, y2 = rect
        self.canvas.create_rectangle(x1 - 3, y1 - 3, x2 + 3, y2 + 3, outline=self.colors["highlight"],
                                     width=4, tags="hint")

    def collect(self) -> None:
        if self.celebrating or self.anim_job:
            return
        if self.game.collect_all():
            self.after_move()

    def quit(self) -> None:
        save_settings(self.settings)
        self.root.destroy()

    # ------------------------------------------------------------------ после хода
    def after_move(self) -> None:
        if self.game.moves > 0 and not self.counted:
            self.counted = True
            self.started_at = time.monotonic()
            self.settings["played"] += 1
            save_settings(self.settings)
        self.redraw()
        if self.game.is_won():
            self.on_win()
        elif self.auto_var.get() and self.game.can_autocomplete() and not self.anim_job:
            self.anim_job = self.root.after(120, self.autocomplete_step)

    def autocomplete_step(self) -> None:
        self.anim_job = None
        for src in [(TABLEAU, i) for i in range(7)]:
            if self.game.auto_to_foundation(src):
                break
        else:
            return
        self.redraw()
        if self.game.is_won():
            self.on_win()
        else:
            self.anim_job = self.root.after(90, self.autocomplete_step)

    def current_time(self) -> float:
        if self.started_at is None:
            return self.elapsed
        return self.elapsed + time.monotonic() - self.started_at

    def tick(self) -> None:
        g = self.game
        mode = "по 1" if g.draw_count == 1 else "по 3"
        self.status.config(
            text=f"Очки: {g.score}     Ходы: {g.moves}     Время: {format_time(self.current_time())}"
            f"     Раздача №{g.seed} ({mode})"
        )
        self.root.after(500, self.tick)

    def on_win(self) -> None:
        self.elapsed = self.current_time()
        self.started_at = None
        s = self.settings
        s["won"] += 1
        best_note = ""
        if s["best_time"] is None or self.elapsed < s["best_time"]:
            s["best_time"] = int(self.elapsed)
            best_note = "\nНовый рекорд времени!"
        if self.game.score > s["best_score"]:
            s["best_score"] = self.game.score
            best_note += "\nНовый рекорд очков!"
        save_settings(s)
        self.win_text = (
            f"Поздравляем, вы выиграли!\n\nОчки: {self.game.score}\n"
            f"Время: {format_time(self.elapsed)}\nХоды: {self.game.moves}{best_note}"
        )
        self.celebrate()

    # ------------------------------------------------------------------ геометрия
    def layout(self) -> None:
        w = max(self.canvas.winfo_width(), 200)
        gap = max(8, w * 0.015)
        self.gap = gap
        self.card_w = min(120, (w - 2 * MARGIN - 6 * gap) / 7)
        self.card_h = self.card_w * 1.4

    def col_x(self, col: int) -> float:
        total = 7 * self.card_w + 6 * self.gap
        left = (max(self.canvas.winfo_width(), 200) - total) / 2
        return left + col * (self.card_w + self.gap)

    def tableau_offsets(self, column: list[Card]) -> tuple[float, float]:
        down, up = self.card_h * 0.12, self.card_h * 0.26
        top = MARGIN + self.card_h + self.gap * 1.5
        avail = max(self.canvas.winfo_height(), 200) - top - self.card_h - MARGIN
        n_down = sum(1 for c in column[:-1] if not c.face_up)
        n_up = max(0, len(column) - 1 - n_down)
        need = n_down * down + n_up * up
        if need > avail > 0:
            k = avail / need
            down, up = down * k, up * k
        return down, up

    # ------------------------------------------------------------------ отрисовка
    def redraw(self) -> None:
        if self.celebrating:
            return
        c = self.canvas
        c.delete("all")
        self.layout()
        self.hitboxes = []
        self.pile_rects = {}
        g = self.game
        cw, ch = self.card_w, self.card_h
        top = MARGIN

        # Колода
        x = self.col_x(0)
        self.pile_rects[(STOCK, 0)] = (x, top, x + cw, top + ch)
        if g.stock:
            layers = min(3, (len(g.stock) + 9) // 10)
            for i in range(layers):
                self.draw_card(None, x - i * 2, top - i * 2, face_up=False)
            self.hitboxes.append(((STOCK, 0), len(g.stock) - 1, x, top, x + cw, top + ch))
        else:
            self.draw_slot(x, top, "↻" if g.waste else "")
            self.hitboxes.append(((STOCK, 0), -1, x, top, x + cw, top + ch))

        # Сброс
        x = self.col_x(1)
        self.pile_rects[(WASTE, 0)] = (x, top, x + cw * 1.6, top + ch)
        shown = g.waste[-g.draw_count:] if g.draw_count == 3 else g.waste[-2:-1] + g.waste[-1:]
        start = len(g.waste) - len(shown)
        fan = cw * 0.24 if g.draw_count == 3 else 0
        for i, card in enumerate(shown):
            cx = x + i * fan
            self.draw_card(card, cx, top, tag=self.card_tag((WASTE, 0), start + i))
            if start + i == len(g.waste) - 1:
                self.hitboxes.append(((WASTE, 0), start + i, cx, top, cx + cw, top + ch))

        # Дом
        for i, pile in enumerate(g.foundations):
            x = self.col_x(3 + i)
            self.pile_rects[(FOUNDATION, i)] = (x, top, x + cw, top + ch)
            if len(pile) > 1:
                self.draw_card(pile[-2], x, top)
            if pile:
                self.draw_card(pile[-1], x, top, tag=self.card_tag((FOUNDATION, i), len(pile) - 1))
                self.hitboxes.append(((FOUNDATION, i), len(pile) - 1, x, top, x + cw, top + ch))
            else:
                self.draw_slot(x, top, "A")

        # Раскладка
        y0 = top + ch + self.gap * 1.5
        bottom = max(self.canvas.winfo_height(), 200)
        for col, column in enumerate(g.tableau):
            x = self.col_x(col)
            self.pile_rects[(TABLEAU, col)] = (x, y0, x + cw, bottom)
            if not column:
                self.draw_slot(x, y0, "K")
                continue
            down, up = self.tableau_offsets(column)
            y = y0
            for idx, card in enumerate(column):
                self.draw_card(card, x, y, tag=self.card_tag((TABLEAU, col), idx))
                self.hitboxes.append(((TABLEAU, col), idx, x, y, x + cw, y + ch))
                y += up if card.face_up else down

    @staticmethod
    def card_tag(pile: Pile, index: int) -> str:
        return f"c_{pile[0]}_{pile[1]}_{index}"

    def rounded_rect(self, x1, y1, x2, y2, r, **kw) -> int:
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw_slot(self, x: float, y: float, label: str) -> None:
        cw, ch = self.card_w, self.card_h
        self.rounded_rect(x, y, x + cw, y + ch, cw * 0.08, fill=self.colors["slot"],
                         outline=self.colors["slot_mark"], width=2)
        if label:
            self.canvas.create_text(
                x + cw / 2, y + ch / 2, text=label, fill=self.colors["slot_mark"], font=(FONT, -int(cw * 0.45), "bold")
            )

    def draw_card(self, card: Card | None, x: float, y: float, face_up: bool | None = None,
                  tag: str | None = None, canvas_tags: tuple = ()) -> None:
        c = self.canvas
        cw, ch = self.card_w, self.card_h
        tags = canvas_tags + ((tag,) if tag else ())
        up = card.face_up if face_up is None and card else bool(face_up)
        r = cw * 0.08
        if not up:
            self.rounded_rect(x, y, x + cw, y + ch, r, fill=self.colors["back"],
                             outline=self.colors["card_edge"], tags=tags)
            p = cw * 0.09
            self.rounded_rect(x + p, y + p, x + cw - p, y + ch - p, r * 0.6, fill=self.colors["back_inner"],
                              outline=self.colors["back_pattern"], width=1, tags=tags)
            c.create_text(x + cw / 2, y + ch / 2, text="❖", fill=self.colors["back_pattern"],
                          font=(FONT, -int(cw * 0.5)), tags=tags)
            return
        color = self.colors[SUIT_KEYS[card.suit]]
        rank, suit = RANKS[card.rank], SUITS[card.suit]
        self.rounded_rect(x, y, x + cw, y + ch, r, fill=self.colors["card_face"],
                         outline=self.colors["card_edge"], tags=tags)
        small = -max(10, int(cw * 0.22))
        c.create_text(x + cw * 0.06, y + ch * 0.02, text=rank, anchor="nw", fill=color,
                      font=(FONT, small, "bold"), tags=tags)
        c.create_text(x + cw * 0.94, y + ch * 0.02, text=suit, anchor="ne", fill=color,
                      font=(FONT, small), tags=tags)
        center = rank if card.rank > 10 else suit
        big = -int(cw * (0.5 if card.rank > 10 else 0.6))
        c.create_text(x + cw / 2, y + ch * 0.58, text=center, fill=color,
                      font=(FONT, big, "bold"), tags=tags)
        if card.rank > 10:
            c.create_text(x + cw / 2, y + ch * 0.86, text=suit, fill=color,
                          font=(FONT, -int(cw * 0.24)), tags=tags)

    # ------------------------------------------------------------------ мышь
    def hit(self, x: float, y: float) -> tuple[Pile, int] | None:
        for pile, idx, x1, y1, x2, y2 in reversed(self.hitboxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return pile, idx
        return None

    def on_press(self, event) -> None:
        if self.celebrating:
            self.finish_celebration()
            return
        if self.anim_job:
            return
        target = self.hit(event.x, event.y)
        self.drag = None
        if not target:
            return
        pile, idx = target
        if pile[0] == STOCK:
            self.deal_from_stock()
            return
        if not self.game.movable_from(pile, idx):
            return
        self.drag = {"pile": pile, "index": idx, "x": event.x, "y": event.y, "moved": False}

    def on_motion(self, event) -> None:
        d = self.drag
        if not d:
            return
        if not d["moved"]:
            if abs(event.x - d["x"]) + abs(event.y - d["y"]) < DRAG_THRESHOLD:
                return
            d["moved"] = True
            d["ox"], d["oy"] = d["x"], d["y"]
            n = len(self.game.pile(d["pile"]))
            for i in range(d["index"], n):
                self.canvas.addtag_withtag("drag", self.card_tag(d["pile"], i))
            self.canvas.tag_raise("drag")
            bbox = self.canvas.bbox(self.card_tag(d["pile"], d["index"]))
            d["card_x"], d["card_y"] = (bbox[0], bbox[1]) if bbox else (event.x, event.y)
        dx, dy = event.x - d["x"], event.y - d["y"]
        self.canvas.move("drag", dx, dy)
        d["x"], d["y"] = event.x, event.y

    def on_release(self, event) -> None:
        d, self.drag = self.drag, None
        if not d or not d["moved"]:
            return
        left = d["card_x"] + (event.x - d["ox"])
        top = d["card_y"] + (event.y - d["oy"])
        dest = self.drop_target(left, top, d["pile"], d["index"])
        if dest and self.game.move(d["pile"], d["index"], dest):
            self.after_move()
        else:
            self.redraw()

    def drop_target(self, left: float, top: float, src: Pile, index: int) -> Pile | None:
        cw, ch = self.card_w, self.card_h
        best, best_area = None, 0.0
        for pile, (x1, y1, x2, y2) in self.pile_rects.items():
            if pile[0] not in (TABLEAU, FOUNDATION) or pile == src:
                continue
            if pile[0] == TABLEAU:
                # Для колонок считаем область последней карты (или пустого места).
                column = self.game.tableau[pile[1]]
                boxes = [h for h in self.hitboxes if h[0] == pile]
                if column and boxes:
                    _, _, x1, y1, x2, y2 = boxes[-1]
                else:
                    y2 = y1 + ch
            ox = min(left + cw, x2) - max(left, x1)
            oy = min(top + ch, y2) - max(top, y1)
            area = max(0, ox) * max(0, oy)
            if area > best_area and self.game.can_move(src, index, pile):
                best, best_area = pile, area
        return best

    def on_double(self, event) -> None:
        if self.celebrating:
            self.finish_celebration()
            return
        if self.anim_job:
            return
        target = self.hit(event.x, event.y)
        if not target:
            return
        pile, idx = target
        if pile[0] == STOCK:
            self.deal_from_stock()  # быстрые щелчки по колоде
            return
        if not self.game.movable_from(pile, idx):
            return
        dest = self.game.best_target(pile, idx)
        if dest and self.game.move(pile, idx, dest):
            self.after_move()

    # ------------------------------------------------------------------ победа
    def celebrate(self) -> None:
        """Классический «водопад» карт после победы."""
        self.celebrating = True
        self.canvas.delete("all")
        self.redraw_frozen()
        cards = [pile[-1 - k] for k in range(13) for pile in self.game.foundations]
        self.fall_queue = [(card, 3 + i % 4) for i, card in enumerate(cards)]
        self.falling = None
        self.frames = 0
        self.anim_job = self.root.after(30, self.celebrate_step)

    def redraw_frozen(self) -> None:
        for i in range(4):
            self.draw_slot(self.col_x(3 + i), MARGIN, "")

    def celebrate_step(self) -> None:
        self.anim_job = None
        if not self.celebrating:
            return
        h = self.canvas.winfo_height()
        w = self.canvas.winfo_width()
        if self.falling is None:
            if not self.fall_queue:
                self.finish_celebration()
                return
            if self.frames > 2500:  # не перегружаем холст следами карт
                self.finish_celebration()
                return
            card, col = self.fall_queue.pop(0)
            vx = random.choice((-1, 1)) * random.uniform(3, 9)
            self.falling = [card, self.col_x(col), MARGIN, vx, random.uniform(-8, 0)]
        card, x, y, vx, vy = self.falling
        vy += 1.4
        x += vx
        y += vy
        if y + self.card_h > h:
            y = h - self.card_h
            vy = -vy * 0.75
        self.draw_card(card, x, y)
        self.frames += 1
        if x + self.card_w < 0 or x > w:
            self.falling = None
        else:
            self.falling = [card, x, y, vx, vy]
        self.anim_job = self.root.after(16, self.celebrate_step)

    def finish_celebration(self) -> None:
        self.stop_animation()
        self.celebrating = False
        self.redraw()
        if messagebox.askyesno("Победа!", self.win_text + "\n\nСыграть ещё?", parent=self.root):
            self.new_game()

    def stop_animation(self) -> None:
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None
        self.celebrating = False

    # ------------------------------------------------------------------ окна
    def show_stats(self) -> None:
        s = self.settings
        rate = f"{100 * s['won'] // s['played']}%" if s["played"] else "—"
        messagebox.showinfo(
            "Статистика",
            f"Сыграно партий: {s['played']}\nПобед: {s['won']} ({rate})\n"
            f"Лучшее время: {format_time(s['best_time'])}\nЛучший счёт: {s['best_score']}",
            parent=self.root,
        )

    def show_help(self) -> None:
        messagebox.showinfo(
            "Как играть",
            "Цель — собрать все карты в четыре стопки «дома» (справа вверху) "
            "по мастям, от туза до короля.\n\n"
            "• В колонках карты кладутся по убыванию с чередованием цвета "
            "(красная на чёрную и наоборот).\n"
            "• На пустую колонку можно положить только короля.\n"
            "• Щёлкните по колоде (слева вверху), чтобы открыть карты.\n\n"
            "Управление:\n"
            "• Перетаскивайте карты мышью.\n"
            "• Двойной щелчок — отправить карту в дом или на подходящее место.\n"
            "• Правая кнопка мыши — собрать всё возможное в дом.\n"
            "• N — открыть карту из колоды.\n"
            "• B — положить карту из сброса туда, куда она подходит.\n"
            "• M, Ctrl+Z или Backspace — отменить ход.\n"
            "• Пробел — подсказка.\n"
            "• F2 — новая игра, Ctrl+R — сыграть раздачу заново.",
            parent=self.root,
        )

    def show_about(self) -> None:
        messagebox.showinfo(
            "О программе",
            f"Косынка (Klondike Solitaire) {__version__}\n\nКлассический пасьянс для Linux.\n"
            "Написан на Python и Tkinter.",
            parent=self.root,
        )


def main() -> None:
    root = tk.Tk(className="solitaire-linux")
    app = SolitaireApp(root)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        app.new_game(int(sys.argv[1]))
    root.mainloop()


if __name__ == "__main__":
    main()
