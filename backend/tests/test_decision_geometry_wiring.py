
import unittest
from unittest.mock import Mock

from library.builder import MatchLibrary


class FakeGeometry:
    def __init__(self):
        self.areas = {
            1: {
                "id": 1,
                "center": {"x": 0, "y": 0, "z": 0},
            },
            2: {
                "id": 2,
                "center": {"x": 100, "y": 0, "z": 0},
            },
        }

    def find_area(self, x, y, z):
        if x == 0:
            return self.areas[1]
        if x == 100:
            return self.areas[2]
        return None

    def shortest_path(self, start_id, end_id):
        if start_id == end_id:
            return [start_id]
        return [start_id, end_id]

    def area_distance(self, a, b):
        return abs(
            a["center"]["x"] - b["center"]["x"]
        )


class TestDecisionGeometryWiring(unittest.TestCase):
    def make_library(self, geometry):
        library = Mock()
        library.geometry = geometry
        library.max_state_age_ticks = 16
        library.player_streams = {}

        actor = {
            "steamid": "123",
            "sample_tick": 150,
            "position": {"x": 0, "y": 0, "z": 0},
            "status": {"is_alive": True},
        }

        teammate = {
            "steamid": "456",
            "sample_tick": 149,
            "position": {"x": 100, "y": 0, "z": 0},
            "status": {"is_alive": True},
        }

        library.get_game_state.return_value = {
            "tick": 150,
            "map": "de_nuke",
            "round": {
                "number": 1,
                "live_start_tick": 100,
            },
            "perspective": {
                "steamid": "123",
                "name": "Player",
                "team": 2,
            },
        }

        library.get_decision_input.return_value = {
            "round": {"number": 1},
            "team_players": [actor, teammate],
            "known_enemies": [],
            "round_state": {},
        }

        library.get_visual_contact_history.return_value = []
        library.get_player_utility_state.return_value = {
            "status": "unavailable",
        }

        return library

    def get_navigation(self, geometry):
        library = self.make_library(geometry)

        result = MatchLibrary.get_decision_context(
            library, 150, "123"
        )

        regroup = next(
            action
            for action in result["candidate_actions"]
            if action["type"] == "regroup"
        )

        self.assertEqual(
            result["evaluation_status"],
            "not_evaluated",
        )
        self.assertEqual(
            regroup["feasibility"],
            "requires_validation",
        )

        return regroup["parameters"]["navigation"]

    def test_geometry_is_used(self):
        nav = self.get_navigation(FakeGeometry())

        self.assertEqual(nav["status"], "nav_connected")
        self.assertEqual(nav["area_path"], [1, 2])
        self.assertEqual(nav["distance_estimate"], 100.0)

    def test_no_geometry_preserves_fallback(self):
        nav = self.get_navigation(None)

        self.assertEqual(nav["status"], "not_checked")
        self.assertIsNone(nav["area_path"])


if __name__ == "__main__":
    unittest.main()
