"""Логика пасьянса «Косынка» (Klondike) без привязки к интерфейсу."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Tuple

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

STOCK = "stock"
WASTE = "waste"
FOUNDATION = "foundation"
TABLEAU = "tableau"

# Очки в стиле классического «Пасьянса» из Windows.
SCORE_WASTE_TO_TABLEAU = 5
SCORE_TO_FOUNDATION = 10
SCORE_TURN_OVER = 5
SCORE_FROM_FOUNDATION = -15
SCORE_RECYCLE_DRAW1 = -100
SCORE_RECYCLE_DRAW3 = -20


@dataclass
class Card:
    rank: int  # 1 (туз) .. 13 (король)
    suit: int  # индекс в SUITS
    face_up: bool = False

    @property
    def red(self) -> bool:
        return self.suit in (1, 2)

    def __str__(self) -> str:
        return f"{RANKS[self.rank]}{SUITS[self.suit]}"


Pile = Tuple[str, int]


class Game:
    def __init__(self, draw_count: int = 1, seed: int | None = None):
        if draw_count not in (1, 3):
            raise ValueError("draw_count должен быть 1 или 3")
        self.draw_count = draw_count
        self.seed = seed if seed is not None else random.randrange(1 << 31)
        self.deal()

    # ------------------------------------------------------------------ раздача
    def deal(self) -> None:
        deck = [Card(rank, suit) for suit in range(4) for rank in range(1, 14)]
        random.Random(self.seed).shuffle(deck)
        self.tableau: list[list[Card]] = [[] for _ in range(7)]
        for i in range(7):
            for j in range(i, 7):
                self.tableau[j].append(deck.pop())
        for column in self.tableau:
            column[-1].face_up = True
        self.stock: list[Card] = deck
        self.waste: list[Card] = []
        self.foundations: list[list[Card]] = [[] for _ in range(4)]
        self.score = 0
        self.moves = 0
        self._history: list[dict] = []

    def pile(self, pile: Pile) -> list[Card]:
        kind, index = pile
        if kind == STOCK:
            return self.stock
        if kind == WASTE:
            return self.waste
        if kind == FOUNDATION:
            return self.foundations[index]
        if kind == TABLEAU:
            return self.tableau[index]
        raise ValueError(f"неизвестная стопка: {pile}")

    # ------------------------------------------------------------------ отмена
    def _snapshot(self) -> dict:
        return copy.deepcopy(
            {
                "tableau": self.tableau,
                "stock": self.stock,
                "waste": self.waste,
                "foundations": self.foundations,
                "score": self.score,
                "moves": self.moves,
            }
        )

    def _push_history(self) -> None:
        self._history.append(self._snapshot())

    def can_undo(self) -> bool:
        return bool(self._history)

    def undo(self) -> bool:
        if not self._history:
            return False
        state = self._history.pop()
        self.tableau = state["tableau"]
        self.stock = state["stock"]
        self.waste = state["waste"]
        self.foundations = state["foundations"]
        self.score = state["score"]
        self.moves = state["moves"] + 1  # отмена тоже считается ходом
        return True

    # ------------------------------------------------------------------ колода
    def draw(self) -> bool:
        """Открыть карты из колоды или перевернуть сброс обратно в колоду."""
        if not self.stock and not self.waste:
            return False
        self._push_history()
        if self.stock:
            for _ in range(min(self.draw_count, len(self.stock))):
                card = self.stock.pop()
                card.face_up = True
                self.waste.append(card)
        else:
            self.stock = list(reversed(self.waste))
            for card in self.stock:
                card.face_up = False
            self.waste = []
            penalty = SCORE_RECYCLE_DRAW1 if self.draw_count == 1 else SCORE_RECYCLE_DRAW3
            self.score = max(0, self.score + penalty)
        self.moves += 1
        return True

    # ------------------------------------------------------------------ правила
    def movable_from(self, pile: Pile, index: int) -> bool:
        """Можно ли взять карты стопки начиная с позиции index."""
        kind, _ = pile
        cards = self.pile(pile)
        if not 0 <= index < len(cards) or not cards[index].face_up:
            return False
        if kind in (WASTE, FOUNDATION):
            return index == len(cards) - 1
        if kind == TABLEAU:
            run = cards[index:]
            return all(_stacks_on(upper, lower) for lower, upper in zip(run, run[1:]))
        return False

    def can_place(self, cards: list[Card], dest: Pile) -> bool:
        kind, _ = dest
        target = self.pile(dest)
        first = cards[0]
        if kind == FOUNDATION:
            if len(cards) != 1:
                return False
            if not target:
                return first.rank == 1
            top = target[-1]
            return top.suit == first.suit and first.rank == top.rank + 1
        if kind == TABLEAU:
            if not target:
                return first.rank == 13
            return target[-1].face_up and _stacks_on(first, target[-1])
        return False

    def can_move(self, src: Pile, index: int, dest: Pile) -> bool:
        if src == dest or not self.movable_from(src, index):
            return False
        return self.can_place(self.pile(src)[index:], dest)

    def move(self, src: Pile, index: int, dest: Pile) -> bool:
        if not self.can_move(src, index, dest):
            return False
        self._push_history()
        source = self.pile(src)
        cards = source[index:]
        del source[index:]
        self.pile(dest).extend(cards)

        if dest[0] == FOUNDATION and src[0] != FOUNDATION:
            self.score += SCORE_TO_FOUNDATION
        elif src[0] == WASTE and dest[0] == TABLEAU:
            self.score += SCORE_WASTE_TO_TABLEAU
        elif src[0] == FOUNDATION and dest[0] == TABLEAU:
            self.score += SCORE_FROM_FOUNDATION

        if src[0] == TABLEAU and source and not source[-1].face_up:
            source[-1].face_up = True
            self.score += SCORE_TURN_OVER
        self.score = max(0, self.score)
        self.moves += 1
        return True

    # ------------------------------------------------------------------ помощь
    def foundation_target(self, src: Pile) -> Pile | None:
        cards = self.pile(src)
        if not cards:
            return None
        for i in range(4):
            dest = (FOUNDATION, i)
            if self.can_move(src, len(cards) - 1, dest):
                return dest
        return None

    def auto_to_foundation(self, src: Pile) -> bool:
        dest = self.foundation_target(src)
        return dest is not None and self.move(src, len(self.pile(src)) - 1, dest)

    def best_target(self, src: Pile, index: int) -> Pile | None:
        """Куда лучше всего отправить карты по двойному щелчку."""
        if index == len(self.pile(src)) - 1 and src[0] != FOUNDATION:
            dest = self.foundation_target(src)
            if dest:
                return dest
        empty = None
        for i in range(7):
            dest = (TABLEAU, i)
            if not self.can_move(src, index, dest):
                continue
            if self.tableau[i]:
                return dest
            # Короля с самого низа колонки нет смысла двигать на пустое место.
            if empty is None and not (src[0] == TABLEAU and index == 0):
                empty = dest
        return empty

    def collect_all(self) -> int:
        """Отправить в дом все карты, которые туда сейчас можно положить."""
        moved = 0
        progress = True
        while progress:
            progress = False
            for src in [(WASTE, 0)] + [(TABLEAU, i) for i in range(7)]:
                if self.auto_to_foundation(src):
                    moved += 1
                    progress = True
        return moved

    def can_autocomplete(self) -> bool:
        return (
            not self.is_won()
            and not self.stock
            and not self.waste
            and all(card.face_up for column in self.tableau for card in column)
        )

    def is_won(self) -> bool:
        return all(len(f) == 13 for f in self.foundations)

    def hint(self) -> tuple[Pile, int, Pile] | str | None:
        """Подсказка: (откуда, с какой карты, куда), DRAW_HINT — открыть колоду,
        None — ходов нет."""
        waste = (WASTE, 0)
        columns = [(TABLEAU, i) for i in range(7)]
        foundations = [(FOUNDATION, i) for i in range(4)]

        # 1. Любая карта, которую можно отправить в дом.
        for src in [waste] + columns:
            dest = self.foundation_target(src)
            if dest:
                return src, len(self.pile(src)) - 1, dest

        # 2. Перенос в раскладке, который открывает закрытую карту
        #    (или освобождает колонку, если на неё есть король).
        for src in columns:
            cards = self.pile(src)
            first_up = next((i for i, c in enumerate(cards) if c.face_up), None)
            if first_up is None or (first_up == 0 and cards[0].rank == 13):
                continue
            for dest in columns:
                if self.can_move(src, first_up, dest):
                    return src, first_up, dest

        # 3. Карта из сброса в раскладку.
        if self.waste:
            dest = self.best_target(waste, len(self.waste) - 1)
            if dest and dest not in foundations:
                return waste, len(self.waste) - 1, dest

        # 4. Открыть новые карты из колоды.
        if self.stock or self.waste:
            return DRAW_HINT
        return None


DRAW_HINT = "draw"


def _stacks_on(card: Card, below: Card) -> bool:
    return card.face_up and card.red != below.red and card.rank == below.rank - 1
