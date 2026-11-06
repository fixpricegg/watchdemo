
import unittest

import numpy as np

from library.line_of_sight import trace_segment


class TestLineOfSight(unittest.TestCase):

    def setUp(self):
        self.wall = np.array([
            [
                [5, -5, -5],
                [5, 5, -5],
                [5, 5, 5],
            ],
            [
                [5, -5, -5],
                [5, 5, 5],
                [5, -5, 5],
            ],
        ], dtype=float)

    def test_wall_blocks_segment(self):
        result = trace_segment(
            [0, 0, 0], [10, 0, 0], self.wall
        )

        self.assertEqual(result["status"], "intersection")
        self.assertAlmostEqual(
            result["hit"]["distance"], 5
        )

    def test_open_segment(self):
        result = trace_segment(
            [0, 10, 0], [10, 10, 0], self.wall
        )

        self.assertEqual(result["status"], "no_intersection")

    def test_reverse_direction(self):
        result = trace_segment(
            [10, 0, 0], [0, 0, 0], self.wall
        )

        self.assertEqual(result["status"], "intersection")

    def test_different_height(self):
        result = trace_segment(
            [0, 0, 10], [10, 0, 10], self.wall
        )

        self.assertEqual(result["status"], "no_intersection")

    def test_nearest_intersection(self):
        second_wall = self.wall.copy()
        second_wall[:, :, 0] = 8

        triangles = np.concatenate([
            second_wall, self.wall
        ])

        result = trace_segment(
            [0, 0, 0], [10, 0, 0], triangles
        )

        self.assertAlmostEqual(
            result["hit"]["distance"], 5
        )

    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            trace_segment(
                [float("nan"), 0, 0],
                [10, 0, 0],
                self.wall,
            )

    def test_empty_geometry(self):
        result = trace_segment(
            [0, 0, 0],
            [10, 0, 0],
            np.empty((0, 3, 3)),
        )

        self.assertEqual(result["status"], "no_intersection")


if __name__ == "__main__":
    unittest.main()
