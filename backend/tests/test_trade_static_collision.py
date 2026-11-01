
import unittest

from library.trade_geometry import assess_trade_static_collision


class FakeLibrary:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def trace_static_line(self, start, end):
        self.calls.append((start, end))

        return {
            "status": self.status,
            "reason": "test_result",
            "hit": None,
            "validation": "experimental",
        }


class TestTradeStaticCollision(unittest.TestCase):
    def setUp(self):
        self.player = {"x": 0, "y": 0, "z": 10}
        self.killer = {"x": 100, "y": 0, "z": 10}

    def test_blocked_remains_diagnostic(self):
        library = FakeLibrary("blocked")

        result = assess_trade_static_collision(
            library, self.player, self.killer
        )

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["line_of_sight_verified"])
        self.assertEqual(
            library.calls[0],
            ([0.0, 0.0, 10.0], [100.0, 0.0, 10.0]),
        )

    def test_clear_does_not_prove_visibility(self):
        library = FakeLibrary("clear")

        result = assess_trade_static_collision(
            library, self.player, self.killer
        )

        self.assertEqual(result["status"], "clear")
        self.assertFalse(result["line_of_sight_verified"])

    def test_unknown(self):
        library = FakeLibrary("unknown")

        result = assess_trade_static_collision(
            library, self.player, self.killer
        )

        self.assertEqual(result["status"], "unknown")

    def test_invalid_position_does_not_trace(self):
        library = FakeLibrary("clear")

        result = assess_trade_static_collision(
            library,
            {"x": float("nan"), "y": 0, "z": 0},
            self.killer,
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["reason"], "invalid_position")
        self.assertEqual(library.calls, [])


if __name__ == "__main__":
    unittest.main()
