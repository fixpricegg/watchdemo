
import unittest

from library.smoke_visibility import assess_smoke_visibility


class TestSmokeVisibility(unittest.TestCase):

    def setUp(self):
        self.player = {"x": 0, "y": 0, "z": 0}
        self.enemy = {"x": 300, "y": 0, "z": 0}

    def utility(self, x, y, z=0):
        return {
            "status": "observed",
            "ongoing_candidates": [{
                "type": "smoke",
                "entity_id": 10,
                "start_tick": 100,
                "x": x,
                "y": y,
                "z": z,
            }],
        }

    def test_smoke_between_players(self):
        result = assess_smoke_visibility(
            self.player, self.enemy,
            self.utility(150, 0),
        )

        self.assertEqual(
            result["status"],
            "possible_smoke_occlusion",
        )
        self.assertEqual(len(result["possible_blockers"]), 1)

    def test_smoke_far_away(self):
        result = assess_smoke_visibility(
            self.player, self.enemy,
            self.utility(150, 1000),
        )

        self.assertEqual(
            result["status"],
            "no_intersection_in_approximation",
        )
        self.assertFalse(result["line_of_sight_verified"])

    def test_missing_smoke_data(self):
        result = assess_smoke_visibility(
            self.player, self.enemy, None
        )
        self.assertEqual(result["status"], "unknown")

    def test_missing_coordinates(self):
        result = assess_smoke_visibility(
            self.player, self.enemy,
            self.utility(None, None),
        )
        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
