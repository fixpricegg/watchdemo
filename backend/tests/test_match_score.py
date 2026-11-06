import unittest

from library.match_score import build_perspective_score


class TestMatchScore(unittest.TestCase):

    def test_normal_score(self):
        results = [
            {"round": 1, "winner_side": "T"},
            {"round": 2, "winner_side": "CT"},
            {"round": 3, "winner_side": "T"},
        ]

        score = build_perspective_score(
            results, {1: "T", 2: "T", 3: "T"}
        )

        self.assertEqual(score["ours"], 2)
        self.assertEqual(score["theirs"], 1)

    def test_side_switch(self):
        results = [
            {"round": 1, "winner_side": "T"},
            {"round": 2, "winner_side": "CT"},
            {"round": 3, "winner_side": "CT"},
        ]

        score = build_perspective_score(
            results, {1: "T", 2: "CT", 3: "CT"}
        )

        self.assertEqual(score["ours"], 3)
        self.assertEqual(score["theirs"], 0)

    def test_missing_winner(self):
        score = build_perspective_score(
            [{"round": 1, "winner_side": None}],
            {1: "T"},
        )

        self.assertEqual(score["status"], "partial")
        self.assertEqual(score["unknown_rounds"], [1])

    def test_no_future_results(self):
        score = build_perspective_score(
            [{"round": 1, "winner_side": "T"}],
            {1: "T", 2: "CT", 3: "T"},
        )

        self.assertEqual(score["ours"], 1)
        self.assertEqual(score["theirs"], 0)


if __name__ == "__main__":
    unittest.main()
