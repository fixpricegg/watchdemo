
import unittest

import numpy as np

from library.builder import MatchLibrary
from library.geometry_layer import GeometryLayer


def wall():
    return {
        "name": "test_wall",
        "surface_property": "concrete",
        "interact_as": [],
        "triangles_local": np.array([
            [[5, -5, -5], [5, 5, -5], [5, 5, 5]],
            [[5, -5, -5], [5, 5, 5], [5, -5, 5]],
        ], dtype=float),
    }


class TestStaticGeometryWiring(unittest.TestCase):

    def make_library(self, collision_geometry=None):
        library = MatchLibrary.__new__(MatchLibrary)
        library.collision_geometry = collision_geometry
        return library

    def test_missing_geometry(self):
        library = self.make_library()

        result = library.trace_static_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"],
            "collision_geometry_unavailable",
        )

    def test_blocked_line(self):
        layer = GeometryLayer([wall()])
        library = self.make_library(layer)

        result = library.trace_static_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "blocked")
        self.assertAlmostEqual(result["hit"]["distance"], 5)

    def test_open_line_is_unverified(self):
        layer = GeometryLayer([wall()])
        library = self.make_library(layer)

        result = library.trace_static_line(
            [0, 10, 0], [10, 10, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"],
            "no_intersection_unvalidated_geometry",
        )

    def test_geometry_does_not_claim_game_trace(self):
        layer = GeometryLayer([wall()])
        library = self.make_library(layer)

        result = library.trace_static_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertFalse(result["game_bullet_trace"])
        self.assertFalse(result["dynamic_obstacles_checked"])


if __name__ == "__main__":
    unittest.main()
