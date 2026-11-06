
import unittest
import pandas as pd

from library.round_results import build_round_results


class TestRoundResults(unittest.TestCase):

    def test_winners(self):
        intervals = [
            (1, 1, 100, 200),
            (2, 2, 300, 400),
            (3, 3, 500, 600),
        ]

        events = pd.DataFrame([
            {"tick": 180, "winner": "CT"},
            {"tick": 370, "winner": "T"},
            {"tick": 590, "winner": "CT"},
        ])

        results = build_round_results(
            intervals, events
        )

        self.assertEqual(
            [r["winner_side"] for r in results],
            ["CT", "T", "CT"],
        )

        self.assertEqual(
            results[1]["loser_side"], "CT"
        )

    def test_missing_result(self):
        intervals = [
            (1, 1, 100, 200),
        ]

        results = build_round_results(
            intervals,
            pd.DataFrame(),
        )

        self.assertIsNone(
            results[0]["winner_side"]
        )
        self.assertEqual(
            results[0]["status"], "unknown"
        )

    def test_round_boundaries(self):
        intervals = [
            (1, 1, 100, 200),
            (2, 2, 200, 300),
        ]

        events = pd.DataFrame([
            {"tick": 200, "winner": "T"},
        ])

        results = build_round_results(
            intervals, events
        )

        self.assertIsNone(
            results[0]["winner_side"]
        )
        self.assertEqual(
            results[1]["winner_side"], "T"
        )


if __name__ == "__main__":
    unittest.main()
