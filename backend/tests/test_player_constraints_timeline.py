
import unittest

import pandas as pd

from library.builder import MatchLibrary


class FakeTimelineLibrary:
    get_player_constraints_timeline = (
        MatchLibrary.get_player_constraints_timeline
    )

    def __init__(self):
        self.geometry = None
        self.max_state_age_ticks = 16

        self.player_streams = {
            "123": pd.DataFrame([
                self.row(100, 0, False, 30),
                self.row(120, 2.0, False, 30),
                self.row(140, 0, True, 30),
                self.row(160, 0, False, 0),
            ])
        }

    def row(self, tick, flash, reload, ammo):
        return {
            "tick": tick,
            "steamid": "123",
            "team_num": 2,
            "name": "Player",
            "X": 0,
            "Y": 0,
            "Z": 0,
            "is_alive": True,
            "flash_duration": flash,
            "is_in_reload": reload,
            "active_weapon_ammo": ammo,
            "active_weapon_name": "ak47",
        }

    def get_game_state(self, tick, player):
        return {
            "tick": tick,
            "perspective": {
                "steamid": "123",
            },
            "round": {
                "number": 1,
                "live_start_tick": 100,
                "end_tick": 300,
            },
        }


class TestPlayerConstraintsTimeline(unittest.TestCase):

    def setUp(self):
        self.library = FakeTimelineLibrary()

    def test_window_samples(self):
        result = self.library.get_player_constraints_timeline(
            120, 160, "123"
        )

        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(
            [item["tick"] for item in result["samples"]],
            [120, 140, 160],
        )
        self.assertFalse(
            result["continuous_state_verified"]
        )

    def test_flash_and_reload(self):
        result = self.library.get_player_constraints_timeline(
            120, 160, "123"
        )

        first = result["samples"][0]["constraints"]
        second = result["samples"][1]["constraints"]

        self.assertIn(
            "flash_effect_observed",
            first["limitations"],
        )
        self.assertIn(
            "reloading",
            second["limitations"],
        )

    def test_empty_magazine(self):
        result = self.library.get_player_constraints_timeline(
            160, 170, "123"
        )

        self.assertIn(
            "magazine_empty",
            result["samples"][0]["constraints"]["limitations"],
        )

    def test_no_future_samples(self):
        result = self.library.get_player_constraints_timeline(
            120, 130, "123"
        )

        self.assertEqual(
            [item["tick"] for item in result["samples"]],
            [120],
        )

    def test_recent_previous_sample(self):
        result = self.library.get_player_constraints_timeline(
            130, 150, "123"
        )

        self.assertEqual(
            [item["tick"] for item in result["samples"]],
            [120, 140],
        )

    def test_stale_previous_sample_rejected(self):
        result = self.library.get_player_constraints_timeline(
            180, 190, "123"
        )

        self.assertEqual(result["sample_count"], 0)
        self.assertEqual(result["status"], "unavailable")

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            self.library.get_player_constraints_timeline(
                160, 120, "123"
            )

    def test_cross_round_rejected(self):
        with self.assertRaises(ValueError):
            self.library.get_player_constraints_timeline(
                160, 300, "123"
            )


if __name__ == "__main__":
    unittest.main()
