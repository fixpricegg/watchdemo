
import unittest
import pandas as pd

from library.builder import MatchLibrary


class TestLibraryRoundResults(unittest.TestCase):

    def setUp(self):
        positions = pd.DataFrame([
            {"tick": 100, "steamid": 111, "name": "player",
             "team_num": 2},
            {"tick": 200, "steamid": 111, "name": "player",
             "team_num": 2},
            {"tick": 300, "steamid": 111, "name": "player",
             "team_num": 2},
        ])

        round_ends = pd.DataFrame([
            {"tick": 150, "winner": "CT"},
            {"tick": 250, "winner": "T"},
        ])

        self.library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[
                (1, 1, 100, 200),
                (2, 2, 200, 300),
                (3, 3, 300, 400),
            ],
            round_ends=round_ends,
            team_observations={},
            team_spot_windows={},
        )

    def test_complete_history(self):
        results = self.library.get_round_results()

        self.assertEqual(len(results), 3)
        self.assertEqual(
            [r["winner_side"] for r in results],
            ["CT", "T", None],
        )

    def test_no_future_results(self):
        results = self.library.get_round_results_at_tick(200)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["winner_side"], "CT")

    def test_result_becomes_available_at_event(self):
        before = self.library.get_round_results_at_tick(249)
        after = self.library.get_round_results_at_tick(250)

        self.assertEqual(len(before), 1)
        self.assertEqual(len(after), 2)

    def test_unknown_result_not_invented(self):
        results = self.library.get_round_results_at_tick(400)

        self.assertEqual(results[-1]["status"], "unknown")
        self.assertIsNone(results[-1]["winner_side"])


if __name__ == "__main__":
    unittest.main()
