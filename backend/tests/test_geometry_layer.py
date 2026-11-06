
import unittest

import numpy as np

from library.geometry_layer import GeometryLayer


def make_wall(x=5, material="concrete", flags=None):
    triangles = np.array([
        [[x, -5, -5], [x, 5, -5], [x, 5, 5]],
        [[x, -5, -5], [x, 5, 5], [x, -5, 5]],
    ], dtype=float)

    return {
        "name": "test_wall",
        "surface_property": material,
        "interact_as": flags or [],
        "triangles_local": triangles,
    }


class TestGeometryLayer(unittest.TestCase):

    def test_blocked(self):
        layer = GeometryLayer([make_wall()])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["hit"]["surface"], "concrete"
        )
        self.assertAlmostEqual(
            result["hit"]["distance"], 5
        )

    def test_open_is_unknown_by_default(self):
        layer = GeometryLayer([make_wall()])

        result = layer.trace_line(
            [0, 10, 0], [10, 10, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"],
            "no_intersection_unvalidated_geometry",
        )

    def test_experimental_clear(self):
        layer = GeometryLayer(
            [make_wall()],
            allow_experimental_clear=True,
        )

        result = layer.trace_line(
            [0, 10, 0], [10, 10, 0]
        )

        self.assertEqual(result["status"], "clear")
        self.assertEqual(
            result["validation"], "experimental"
        )

    def test_glass_is_uncertain(self):
        layer = GeometryLayer([
            make_wall(material="glass")
        ])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"],
            "uncertain_surface_intersection",
        )

    def test_playerclip_not_a_solid_wall(self):
        layer = GeometryLayer([
            make_wall(flags=["playerclip"])
        ])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")

    def test_passbullets_is_uncertain(self):
        layer = GeometryLayer([
            make_wall(
                material="chainlink",
                flags=["passbullets"],
            )
        ], allow_experimental_clear=True)

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")

    def test_nearest_blocker(self):
        layer = GeometryLayer([
            make_wall(x=8),
            make_wall(x=3),
        ])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "blocked")
        self.assertAlmostEqual(
            result["hit"]["distance"], 3
        )

    def test_empty_geometry_is_unknown(self):
        layer = GeometryLayer([])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"], "empty_geometry"
        )

    def test_invalid_coordinates(self):
        layer = GeometryLayer([make_wall()])

        with self.assertRaises(ValueError):
            layer.trace_line(
                [float("nan"), 0, 0],
                [10, 0, 0],
            )


    def test_uncertain_surface_before_solid(self):
        layer = GeometryLayer([
            make_wall(x=3, material="glass"),
            make_wall(x=7, material="concrete"),
        ])

        result = layer.trace_line(
            [0, 0, 0], [10, 0, 0]
        )

        self.assertEqual(result["status"], "unknown")
        self.assertEqual(
            result["reason"],
            "uncertain_surface_intersection",
        )
        self.assertAlmostEqual(result["hit"]["distance"], 3)



if __name__ == "__main__":
    unittest.main()
