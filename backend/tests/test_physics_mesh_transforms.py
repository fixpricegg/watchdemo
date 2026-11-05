
import json
import unittest
import tempfile

from pathlib import Path

import numpy as np

from library.physics_mesh import (
    _local_matrix,
    _transform_positions,
    load_physics_mesh,
)
from library.geometry_layer import GeometryLayer


class TestPhysicsMeshTransforms(unittest.TestCase):

    def make_gltf(self, folder, nodes):
        vertices = np.array([
            [0, -1, -1],
            [0, 1, -1],
            [0, 0, 1],
        ], dtype="<f4")

        raw = vertices.tobytes()

        data = {
            "buffers": [
                {"uri": "mesh.bin", "byteLength": len(raw)}
            ],
            "bufferViews": [{
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": len(raw),
            }],
            "accessors": [{
                "bufferView": 0,
                "componentType": 5126,
                "count": 3,
                "type": "VEC3",
            }],
            "meshes": [{
                "primitives": [{
                    "attributes": {"POSITION": 0},
                    "mode": 4,
                }]
            }],
            "nodes": nodes,
        }

        path = Path(folder)

        (path / "mesh.bin").write_bytes(raw)
        (path / "mesh.gltf").write_text(
            json.dumps(data), encoding="utf-8"
        )

        return path / "mesh.gltf"

    def test_parent_child_transforms(self):
        nodes = [
            {
                "translation": [10, 0, 0],
                "children": [1],
            },
            {
                "mesh": 0,
                "translation": [5, 0, 0],
                "extras": {"SurfaceProperty": "concrete"},
            },
        ]

        with tempfile.TemporaryDirectory() as folder:
            path = self.make_gltf(folder, nodes)
            layer = GeometryLayer.from_gltf(path)

            trace = layer.trace_line(
                [0, 0, 0], [20, 0, 0]
            )

        self.assertEqual(trace["status"], "blocked")
        self.assertAlmostEqual(
            trace["hit"]["distance"], 15
        )

    def test_column_major_matrix(self):
        matrix = [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            8, 0, 0, 1,
        ]

        with tempfile.TemporaryDirectory() as folder:
            path = self.make_gltf(folder, [
                {
                    "mesh": 0,
                    "matrix": matrix,
                    "extras": {"SurfaceProperty": "concrete"},
                }
            ])

            trace = GeometryLayer.from_gltf(path).trace_line(
                [0, 0, 0], [20, 0, 0]
            )

        self.assertEqual(trace["status"], "blocked")
        self.assertAlmostEqual(
            trace["hit"]["distance"], 8
        )

    def test_rotation_and_scale(self):
        node = {
            "rotation": [0, 0, 0.70710678, 0.70710678],
            "scale": [2, 2, 2],
        }

        matrix = _local_matrix(node)

        result = _transform_positions(
            [[1, 0, 0]], matrix
        )

        np.testing.assert_allclose(
            result[0], [0, 2, 0], atol=1e-6
        )

    def test_invalid_matrix(self):
        with self.assertRaises(ValueError):
            _local_matrix({"matrix": [1, 2, 3]})

    def test_cycle_rejected(self):
        nodes = [
            {"children": [1]},
            {"mesh": 0, "children": [0]},
        ]

        with tempfile.TemporaryDirectory() as folder:
            path = self.make_gltf(folder, nodes)

            with self.assertRaises(ValueError):
                load_physics_mesh(path)

    def test_source2_raw_preserves_game_coordinates(self):
        matrix = [
            0.0254, 0, 0, 0,
            0, 0.0254, 0, 0,
            0, 0, 0.0254, 0,
            8, 0, 0, 1,
        ]

        nodes = [{
            "mesh": 0,
            "matrix": matrix,
            "extras": {"SurfaceProperty": "concrete"},
        }]

        with tempfile.TemporaryDirectory() as folder:
            path = self.make_gltf(folder, nodes)

            raw = GeometryLayer.from_gltf(
                path,
                coordinate_space="source2_raw",
            )

            transformed = GeometryLayer.from_gltf(
                path,
                coordinate_space="gltf",
            )

            raw_trace = raw.trace_line(
                [-5, 0, 0], [5, 0, 0]
            )
            transformed_trace = transformed.trace_line(
                [-5, 0, 0], [5, 0, 0]
            )

        self.assertEqual(raw_trace["status"], "blocked")
        self.assertAlmostEqual(
            raw_trace["hit"]["distance"], 5
        )
        self.assertEqual(
            transformed_trace["status"], "unknown"
        )

    def test_invalid_coordinate_space(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_gltf(folder, [{"mesh": 0}])

            with self.assertRaises(ValueError):
                GeometryLayer.from_gltf(
                    path,
                    coordinate_space="invalid",
                )



if __name__ == "__main__":
    unittest.main()
