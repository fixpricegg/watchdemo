
import unittest

import pandas as pd

from detectors.missed_trade import get_possible_missed_trades


class FakeGeometry:
    def __init__(self, connected=True):
        self.connected = connected
        self.areas = {
            1: {
                "id": 1,
                "center": {"x": 0, "y": 0, "z": 0},
            },
            2: {
                "id": 2,
                "center": {"x": 100, "y": 0, "z": 0},
            },
            3: {
                "id": 3,
                "center": {"x": 0, "y": 0, "z": 300},
            },
        }

    def find_area(self, x, y, z):
        if z >= 200:
            return self.areas[3]
        if x >= 50:
            return self.areas[2]
        return self.areas[1]

    def shortest_path(self, start, end):
        if start == end:
            return [start]
        if not self.connected:
            return None
        return [start, end]

    def area_distance(self, a, b):
        first = a["center"]
        second = b["center"]
        return sum(
            (first[axis] - second[axis]) ** 2
            for axis in ("x", "y", "z")
        ) ** 0.5


class FakeLibrary:
    def __init__(self):
        self.geometry = FakeGeometry()
        self.max_state_age_ticks = 16
        self.death_data_complete = True

        self.players = [
            {
                "steamid": "123",
                "team": 2,
                "sample_tick": 150,
                "position": {"x": 0, "y": 0, "z": 0},
                "status": {"is_alive": True},
            },
            {
                "steamid": "456",
                "team": 2,
                "sample_tick": 149,
                "position": {"x": 10, "y": 0, "z": 0},
                "status": {"is_alive": False},
            },
            {
                "steamid": "900",
                "team": 3,
                "sample_tick": 150,
                "position": {"x": 100, "y": 0, "z": 0},
                "status": {"is_alive": True},
            },
        ]

        self.round_end = 1000

    def get_game_state(self, tick, player):
        return {
            "tick": tick,
            "round": {
                "number": 1,
                "live_start_tick": 100,
                "end_tick": self.round_end,
            },
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
            "ground_truth": {
                "players": self.players,
            },
        }


class TestMissedTradeCandidates(unittest.TestCase):
    def setUp(self):
        self.library = FakeLibrary()

        self.deaths = pd.DataFrame([
            {
                "round": 1,
                "tick": 150,
                "user_steamid": 456,
                "attacker_steamid": 900,
                "user_name": "Teammate",
                "attacker_name": "Enemy",
            }
        ])

    def detect(self):
        return get_possible_missed_trades(
            "Player",
            self.deaths,
            self.library,
        )

    def test_valid_review_candidate(self):
        result = self.detect()

        self.assertEqual(len(result), 1)

        candidate = result[0]

        self.assertEqual(
            candidate["type"],
            "trade_review_candidate",
        )
        self.assertEqual(
            candidate["status"],
            "review_required",
        )
        self.assertEqual(
            candidate["evaluation_status"],
            "not_evaluated",
        )
        self.assertEqual(
            candidate["geometry"]["status"],
            "nav_connected",
        )
        self.assertEqual(
            candidate["geometry"]["trade_feasibility"],
            "not_established",
        )

    def test_wrong_team_is_rejected(self):
        self.library.players[1]["team"] = 3
        self.assertEqual(self.detect(), [])

    def test_stale_position_is_rejected(self):
        self.library.players[0]["sample_tick"] = 100
        self.assertEqual(self.detect(), [])

    def test_dead_player_is_rejected(self):
        self.library.players[0]["status"]["is_alive"] = False
        self.assertEqual(self.detect(), [])

    def test_killer_traded_within_window(self):
        self.deaths.loc[len(self.deaths)] = {
            "round": 1,
            "tick": 250,
            "user_steamid": 900,
            "attacker_steamid": 777,
            "user_name": "Enemy",
            "attacker_name": "Other Teammate",
        }

        self.assertEqual(self.detect(), [])

    def test_disconnected_navigation(self):
        self.library.geometry = FakeGeometry(False)
        self.assertEqual(self.detect(), [])

    def test_no_geometry(self):
        self.library.geometry = None
        self.assertEqual(self.detect(), [])

    def test_incomplete_observation_window(self):
        self.library.round_end = 350
        self.assertEqual(self.detect(), [])

    def test_incomplete_death_data(self):
        self.library.death_data_complete = False
        self.assertEqual(self.detect(), [])

    def test_different_floors_not_confirmed(self):
        self.library.players[2]["position"] = {
            "x": 0, "y": 0, "z": 300,
        }

        result = self.detect()

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["geometry"]["vertical_separation"],
            300,
        )
        self.assertEqual(
            result[0]["geometry"]["line_of_sight"],
            "not_checked",
        )
        self.assertEqual(
            result[0]["geometry"]["trade_feasibility"],
            "not_established",
        )


if __name__ == "__main__":
    unittest.main()
