
import unittest
from unittest.mock import Mock

from library.builder import MatchLibrary


class TestLibraryUtility(unittest.TestCase):

    def setUp(self):
        self.library = MatchLibrary.__new__(MatchLibrary)

        players = [
            {
                "steamid": "1",
                "team": 2,
                "inventory": [
                    "AK-47",
                    "Smoke Grenade",
                    "Flashbang",
                ],
            },
            {
                "steamid": "2",
                "team": 2,
                "inventory": ["Molotov"],
            },
        ]

        self.state = {
            "perspective": {
                "steamid": "1",
                "team": 2,
            },
            "round": {"number": 1},
            "ground_truth": {"players": players},
        }

        self.library.get_game_state = Mock(
            return_value=self.state
        )

    def test_player_utility(self):
        result = self.library.get_player_utility_state(
            100, "1"
        )

        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["counts"]["smoke"], 1)
        self.assertEqual(result["counts"]["flash"], 1)
        self.assertEqual(result["total"], 2)

    def test_own_team_only(self):
        self.state["ground_truth"]["players"].append({
            "steamid": "3",
            "team": 3,
            "inventory": ["Smoke Grenade", "Flashbang"],
        })

        result = self.library.get_team_utility_state(
            100, "1"
        )

        self.assertEqual(result["observed_total"], 3)
        self.assertEqual(result["status"], "partial")

    def test_missing_inventory_not_zero(self):
        self.state["ground_truth"]["players"][0][
            "inventory"
        ] = None

        result = self.library.get_player_utility_state(
            100, "1"
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["counts"])

    def test_event_history_is_not_automatically_used(self):
        self.library.get_event_history = Mock(
            side_effect=AssertionError(
                "Ground truth events must not enter utility snapshots"
            )
        )

        self.library.get_player_utility_state(100, "1")
        self.library.get_team_utility_state(100, "1")

        self.library.get_event_history.assert_not_called()


if __name__ == "__main__":
    unittest.main()
