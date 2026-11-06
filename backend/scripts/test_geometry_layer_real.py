
import sys

from library.geometry_layer import GeometryLayer


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.test_geometry_layer_real <gltf>")
        return

    layer = GeometryLayer.from_gltf(sys.argv[1])

    cases = [
        (
            "Nuke round 11: blocked candidate",
            [272.31243896, -1276.89477539, -351.46875],
            [411.51260376, -846.59844971, -327.96875],
        ),
        (
            "Nuke round 6: open candidate",
            [373.40841675, -1257.36926270, -351.96875],
            [804.26519775, -1745.41418457, -351.96875],
        ),
    ]

    print("Loaded triangles:", layer.triangle_count)

    for name, start, end in cases:
        result = layer.trace_line(start, end)

        print("\n", name)
        print("Status:", result["status"])
        print("Reason:", result["reason"])
        print("Hit:", result["hit"])
        print("Validation:", result["validation"])


if __name__ == "__main__":
    main()
