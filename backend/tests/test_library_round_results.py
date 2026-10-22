
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


    def test_loss_counters_in_match_library(self):
        from library.loss_bonus import (
            CT_LOSS_FIELD,
            T_LOSS_FIELD,
        )

        positions = pd.DataFrame([
            {
                "tick": 100,
                "steamid": 111,
                "name": "player",
                "team_num": 2,
            },
        ])

        counters = pd.DataFrame([
            {
                "tick": 100,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 2,
            },
            {
                "tick": 150,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 3,
            },
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 100, 200)],
            loss_counter_df=counters,
            team_observations={},
            team_spot_windows={},
        )

        before = library.get_loss_bonus_state(149)
        after = library.get_loss_bonus_state(150)

        self.assertEqual(
            before["engine_counters"]["T"], 2
        )
        self.assertEqual(
            after["engine_counters"]["T"], 3
        )

        self.assertEqual(before["source_tick"], 100)
        self.assertEqual(after["source_tick"], 150)

        self.assertIsNone(
            after["monetary_bonus"]["T"]
        )

        self.assertEqual(
            library.get_loss_bonus_state(99)["status"],
            "unavailable",
        )



if __name__ == "__main__":
    unittest.main()
