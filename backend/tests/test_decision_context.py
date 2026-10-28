
import unittest
from unittest.mock import Mock

import pandas as pd

from library.builder import MatchLibrary


class TestDecisionContext(unittest.TestCase):

    def setUp(self):
        self.lib = MatchLibrary.__new__(MatchLibrary)
        self.lib.max_state_age_ticks = 16

        self.lib.player_streams = {
            "123": pd.DataFrame([
                {"tick": 100, "X": 1, "Y": 2, "Z": 3},
                {"tick": 150, "X": 5, "Y": 6, "Z": 7},
                {"tick": 250, "X": 900, "Y": 900, "Z": 0},
            ])
        }

        self.state = {
            "tick": 150,
            "map": "de_nuke",
            "round": {
                "number": 1,
                "live_start_tick": 90,
                "end_tick": 300,
            },
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
        }

        self.lib.get_game_state = Mock(return_value=self.state)

        self.lib.get_decision_input = Mock(return_value={
            "round": {"number": 1, "live_start_tick": 90},
            "team_players": [
                {
                    "steamid": "123",
                    "position": {"x": 5, "y": 6, "z": 7},
                    "status": {"is_alive": True},
                    "sample_tick": 150,
                },
            ],
            "known_enemies": [],
            "round_state": {"alive": {"T": 5, "CT": 5}},
        })

        self.lib.get_visual_contact_history = Mock(
            return_value=[]
        )
        self.lib.get_player_utility_state = Mock(
            return_value={"status": "observed", "items": []}
        )

    def test_no_future_path(self):
        result = self.lib.get_decision_context(150, "123")

        ticks = [p["tick"] for p in result["player_path"]]
        self.assertEqual(ticks, [100, 150])
        self.assertNotIn(250, ticks)

    def test_no_future_round_end(self):
        result = self.lib.get_decision_context(150, "123")
        self.assertNotIn("end_tick", result["round"])

    def test_no_hidden_enemy_truth(self):
        result = self.lib.get_decision_context(150, "123")
        self.assertNotIn("ground_truth", result)
        self.assertEqual(result["known_enemies"], [])


    def test_not_evaluated_yet(self):
        result = self.lib.get_decision_context(150, "123")

        self.assertEqual(
            result["evaluation_status"],
            "not_evaluated",
        )

        actions = result["candidate_actions"]

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["id"], "hold_position")
        self.assertEqual(actions[0]["type"], "hold_position")
        self.assertEqual(actions[0]["feasibility"], "available")
        self.assertIsNone(actions[0]["score"])
        self.assertIsNone(actions[0]["rank"])
        self.assertEqual(
            actions[0]["evaluation_status"],
            "not_evaluated",
        )



if __name__ == "__main__":
    unittest.main()
