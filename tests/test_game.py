import unittest

from solitaire.game import FOUNDATION, TABLEAU, WASTE, Card, Game


def empty_game(draw_count=1):
    g = Game(draw_count, seed=1)
    g.tableau = [[] for _ in range(7)]
    g.stock, g.waste = [], []
    g.foundations = [[] for _ in range(4)]
    return g


class DealTest(unittest.TestCase):
    def test_initial_deal(self):
        g = Game(seed=42)
        self.assertEqual([len(c) for c in g.tableau], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(len(g.stock), 24)
        for column in g.tableau:
            self.assertTrue(column[-1].face_up)
            self.assertFalse(any(c.face_up for c in column[:-1]))
        cards = {(c.rank, c.suit) for c in g.stock + sum(g.tableau, [])}
        self.assertEqual(len(cards), 52)

    def test_same_seed_same_deal(self):
        a, b = Game(seed=7), Game(seed=7)
        self.assertEqual([str(c) for c in a.stock], [str(c) for c in b.stock])


class RulesTest(unittest.TestCase):
    def test_draw_and_recycle(self):
        g = Game(draw_count=3, seed=3)
        for _ in range(8):
            self.assertTrue(g.draw())
        self.assertEqual((len(g.stock), len(g.waste)), (0, 24))
        self.assertTrue(g.draw())
        self.assertEqual((len(g.stock), len(g.waste)), (24, 0))
        self.assertFalse(any(c.face_up for c in g.stock))

    def test_alternating_colors(self):
        g = empty_game()
        g.tableau[0] = [Card(8, 0, True)]  # 8♠
        g.tableau[1] = [Card(7, 1, True)]  # 7♥
        g.tableau[2] = [Card(7, 3, True)]  # 7♣
        self.assertTrue(g.can_move((TABLEAU, 1), 0, (TABLEAU, 0)))
        self.assertFalse(g.can_move((TABLEAU, 2), 0, (TABLEAU, 0)))

    def test_only_king_on_empty_column(self):
        g = empty_game()
        g.tableau[0] = [Card(12, 0, True)]
        g.tableau[1] = [Card(13, 0, True)]
        g.tableau[2] = [Card(5, 0, False), Card(13, 1, True)]
        self.assertFalse(g.can_move((TABLEAU, 0), 0, (TABLEAU, 3)))
        self.assertTrue(g.can_move((TABLEAU, 1), 0, (TABLEAU, 3)))
        self.assertEqual(g.best_target((TABLEAU, 1), 0), None)
        self.assertEqual(g.best_target((TABLEAU, 2), 1), (TABLEAU, 3))

    def test_foundation_and_turn_over(self):
        g = empty_game()
        g.tableau[0] = [Card(5, 0, False), Card(1, 2, True)]
        self.assertTrue(g.auto_to_foundation((TABLEAU, 0)))
        self.assertEqual(len(g.foundations[0]), 1)
        self.assertTrue(g.tableau[0][-1].face_up)
        self.assertEqual(g.score, 15)
        g.tableau[1] = [Card(3, 2, True)]
        self.assertFalse(g.auto_to_foundation((TABLEAU, 1)))

    def test_move_run(self):
        g = empty_game()
        g.tableau[0] = [Card(9, 1, True), Card(8, 0, True), Card(7, 2, True)]
        g.tableau[1] = [Card(10, 3, True)]
        self.assertFalse(g.movable_from((TABLEAU, 0), 0) and g.can_move((TABLEAU, 0), 0, (TABLEAU, 0)))
        self.assertTrue(g.move((TABLEAU, 0), 0, (TABLEAU, 1)))
        self.assertEqual(len(g.tableau[1]), 4)
        g.tableau[2] = [Card(6, 0, True), Card(6, 1, True)]
        self.assertFalse(g.movable_from((TABLEAU, 2), 0))

    def test_waste_top_only(self):
        g = empty_game()
        g.waste = [Card(1, 0, True), Card(2, 0, True)]
        self.assertFalse(g.movable_from((WASTE, 0), 0))
        self.assertTrue(g.movable_from((WASTE, 0), 1))

    def test_undo(self):
        g = Game(seed=11)
        before = [str(c) for c in g.stock]
        g.draw()
        self.assertTrue(g.undo())
        self.assertEqual([str(c) for c in g.stock], before)
        self.assertEqual(g.waste, [])
        self.assertFalse(g.undo())

    def test_autocomplete_to_win(self):
        g = empty_game()
        for suit in range(4):
            g.tableau[suit] = [Card(r, suit, True) for r in range(13, 0, -1)]
        self.assertTrue(g.can_autocomplete())
        self.assertEqual(g.collect_all(), 52)
        self.assertTrue(g.is_won())
        self.assertTrue(all(len(f) == 13 for f in g.foundations))
        self.assertEqual({f[0].suit for f in g.foundations}, {0, 1, 2, 3})


if __name__ == "__main__":
    unittest.main()
