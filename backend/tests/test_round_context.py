
import unittest

from library.builder import MatchLibrary


class TestRoundContext(unittest.TestCase):

    def setUp(self):
        self.library = MatchLibrary.__new__(MatchLibrary)
        self.library.attach_radar_round_context(
            {
                "coordinate_source": "CC4/CPlantedC4",
                "states": [
                    {"tick": 100, "state": "carried"},
                    {"tick": 150, "state": "dropped"},
                    {"tick": 200, "state": "planted"},
                ],
            },
            tickrate=64,
            round_time_seconds=115,
        )

    def test_no_future_bomb_state(self):
        state = self.library.get_bomb_ground_truth_at_tick(
            175, {"live_start_tick": 100}
        )
        self.assertEqual(state["state"], "dropped")

    def test_exact_plant_tick(self):
        state = self.library.get_bomb_ground_truth_at_tick(
            200, {"live_start_tick": 100}
        )
        self.assertEqual(state["state"], "planted")

    def test_no_previous_round_state(self):
        state = self.library.get_bomb_ground_truth_at_tick(
            310, {"live_start_tick": 300}
        )
        self.assertIsNone(state)

    def test_missing_entity_source_rejected(self):
        with self.assertRaises(ValueError):
            self.library.attach_radar_round_context(
                {"states": []},
                tickrate=64,
                round_time_seconds=115,
            )


if __name__ == "__main__":
    unittest.main()
