
import sys
from collections import defaultdict

from library.physics_mesh import load_physics_mesh
from library.collision_groups import classify_collision_group


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.check_collision_groups <gltf>")
        return

    groups = load_physics_mesh(sys.argv[1])
    summary = defaultdict(lambda: {"groups": 0, "triangles": 0})

    for group in groups:
        category = classify_collision_group(group)
        count = len(group["triangles_local"])

        summary[category]["groups"] += 1
        summary[category]["triangles"] += count

        print(
            group["name"],
            "=>",
            category,
            f"({count} triangles)"
        )

    print("\nSUMMARY")

    for category, values in sorted(summary.items()):
        print(category, values)

    print(
        "TOTAL TRIANGLES:",
        sum(v["triangles"] for v in summary.values())
    )


if __name__ == "__main__":
    main()
