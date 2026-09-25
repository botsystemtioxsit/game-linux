import unittest

from solitaire.theme import CLASSIC, COLOR_KEYS, PRESETS, merge_colors, preset_name


class ThemeTest(unittest.TestCase):
    def test_presets_are_complete(self):
        for name, preset in PRESETS.items():
            self.assertEqual(set(preset), set(COLOR_KEYS), name)
            self.assertEqual(preset_name(preset), name)

    def test_merge_ignores_bad_values(self):
        colors = merge_colors({"table": "#ABCDEF", "hearts": "red", "back": 5, "junk": "#000000"})
        self.assertEqual(colors["table"], "#abcdef")
        self.assertEqual(colors["hearts"], CLASSIC["hearts"])
        self.assertEqual(colors["back"], CLASSIC["back"])
        self.assertNotIn("junk", colors)
        self.assertEqual(merge_colors(None), CLASSIC)
        self.assertIsNone(preset_name(colors))


if __name__ == "__main__":
    unittest.main()
