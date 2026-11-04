
import unittest

from library.builder import MatchLibrary


class FakeGeometry:
    def __init__(self, connected=True):
        self.connected = connected
        self.areas = {
            1: {"id": 1, "center": {"x": 0, "y": 0, "z": 0}},
            2: {"id": 2, "center": {"x": 100, "y": 0, "z": 0}},
        }

    def find_area(self, x, y, z):
        return self.areas[2] if x >= 50 else self.areas[1]

    def shortest_path(self, start, end):
        if start == end:
            return [start]
        if not self.connected:
            return None
        return [start, end]

    def area_distance(self, first, second):
        return abs(
            first["center"]["x"] - second["center"]["x"]
        )


class FakeLibrary:
    get_support_geometry_at_tick = (
        MatchLibrary.get_support_geometry_at_tick
    )

    def __init__(self):
        self.geometry = FakeGeometry()
        self.max_state_age_ticks = 16
        self.trace_calls = []

        self.players = [
            self.player("123", 2, 0),
            self.player("456", 2, 20),
            self.player("900", 3, 100),
        ]

    def player(self, steamid, team, x):
        return {
            "steamid": steamid,
            "team": team,
            "sample_tick": 120,
            "position": {"x": x, "y": 0, "z": 0},
            "status": {"is_alive": True},
        }

    def get_game_state(self, tick, player):
        return {
            "perspective": {"steamid": "123"},
            "ground_truth": {"players": self.players},
        }

    def trace_static_line(self, start, end):
        self.trace_calls.append((start, end))
        return {
            "status": "unknown",
            "reason": "experimental_test",
            "hit": None,
        }


class TestSupportGeometry(unittest.TestCase):
    def setUp(self):
        self.library = FakeLibrary()

    def assess(self, tick=120, **options):
        return self.library.get_support_geometry_at_tick(
            tick, "123", "456", "900", **options
        )

    def test_distances_and_navigation(self):
        result = self.assess()
        geometry = result["geometry"]

        self.assertEqual(result["status"], "positions_observed")
        self.assertEqual(
            geometry["distances_2d"]["actor_to_killer"], 100
        )
        self.assertEqual(
            geometry["distances_2d"]["actor_to_teammate"], 20
        )
        self.assertEqual(
            geometry["navigation"]["actor_to_killer"]["status"],
            "nav_connected",
        )
        self.assertEqual(
            geometry["support_opportunity"], "not_established"
        )
        self.assertFalse(geometry["line_of_sight_verified"])

    def test_missing_position(self):
        self.library.players[2]["position"] = None

        result = self.assess()
        self.assertEqual(
            result["status"], "invalid_position"
        )

    def test_stale_sample(self):
        self.library.players[2]["sample_tick"] = 100
        self.assertEqual(
            self.assess()["status"], "stale_or_future_snapshot"
        )

    def test_future_sample(self):
        self.library.players[2]["sample_tick"] = 125
        self.assertEqual(
            self.assess()["status"], "stale_or_future_snapshot"
        )

    def test_dead_actor(self):
        self.library.players[0]["status"]["is_alive"] = False
        self.assertEqual(
            self.assess()["status"], "not_applicable_actor_dead"
        )

    def test_wrong_team(self):
        self.library.players[1]["team"] = 3
        self.assertEqual(
            self.assess()["status"], "invalid_team_context"
        )

    def test_disconnected_nav_is_not_error_verdict(self):
        self.library.geometry = FakeGeometry(False)

        result = self.assess()["geometry"]

        self.assertEqual(
            result["navigation"]["actor_to_killer"]["status"],
            "no_nav_path",
        )
        self.assertEqual(
            result["support_opportunity"], "not_established"
        )

    def test_static_trace_is_opt_in(self):
        self.assess()
        self.assertEqual(self.library.trace_calls, [])

        result = self.assess(include_static_trace=True)

        self.assertEqual(len(self.library.trace_calls), 2)
        self.assertFalse(
            result["geometry"]["line_of_sight_verified"]
        )
        self.assertEqual(
            result["geometry"]["static_collision"]
            ["actor_to_killer"]["status"],
            "unknown",
        )


if __name__ == "__main__":
    unittest.main()
