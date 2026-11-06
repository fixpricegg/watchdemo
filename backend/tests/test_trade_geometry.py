
import unittest

from library.trade_geometry import assess_trade_geometry


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
        if x >= 100:
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
        return (
            (first["x"] - second["x"]) ** 2
            + (first["y"] - second["y"]) ** 2
            + (first["z"] - second["z"]) ** 2
        ) ** 0.5


class TestTradeGeometry(unittest.TestCase):
    def setUp(self):
        self.player = {"x": 0, "y": 0, "z": 0}
        self.killer = {"x": 100, "y": 0, "z": 0}

    def test_connected_does_not_prove_trade(self):
        result = assess_trade_geometry(
            FakeGeometry(), self.player, self.killer
        )

        self.assertEqual(result["status"], "nav_connected")
        self.assertEqual(result["nav_path"], [1, 2])
        self.assertEqual(result["nav_distance_estimate"], 100.0)
        self.assertEqual(
            result["trade_feasibility"],
            "not_established",
        )
        self.assertEqual(
            result["line_of_sight"],
            "not_checked",
        )

    def test_disconnected(self):
        result = assess_trade_geometry(
            FakeGeometry(False), self.player, self.killer
        )

        self.assertEqual(result["status"], "no_nav_path")
        self.assertIsNone(result["nav_path"])

    def test_different_floors(self):
        upper = {"x": 0, "y": 0, "z": 300}

        result = assess_trade_geometry(
            FakeGeometry(), self.player, upper
        )

        self.assertEqual(result["player_area_id"], 1)
        self.assertEqual(result["killer_area_id"], 3)
        self.assertEqual(result["vertical_separation"], 300)
        self.assertEqual(
            result["trade_feasibility"],
            "not_established",
        )

    def test_missing_geometry(self):
        result = assess_trade_geometry(
            None, self.player, self.killer
        )

        self.assertEqual(
            result["status"], "geometry_unavailable"
        )

    def test_invalid_position(self):
        result = assess_trade_geometry(
            FakeGeometry(),
            {"x": float("nan"), "y": 0, "z": 0},
            self.killer,
        )

        self.assertEqual(
            result["status"], "invalid_position"
        )


if __name__ == "__main__":
    unittest.main()
