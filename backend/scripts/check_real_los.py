
import sys
import numpy as np

from library.physics_mesh import load_physics_mesh
from library.collision_groups import classify_collision_group
from library.line_of_sight import trace_segment


ACTOR = np.array([
    272.31243896, -1276.89477539, -415.46875
])

KILLER = np.array([
    411.51260376, -846.59844971, -391.96875
])


def check_ray(groups, start, end):
    hits = []
    checked_triangles = 0

    for group in groups:
        category = classify_collision_group(group)

        # Only potentially solid geometry is used here.
        # Unknown surfaces are not silently declared clear.
        if category not in (
            "solid_candidate",
            "explicit_los_blocker",
        ):
            continue

        triangles = group["triangles_local"]
        checked_triangles += len(triangles)

        result = trace_segment(
            start, end, triangles
        )

        if result["status"] == "intersection":
            hits.append({
                "group": group["name"],
                "category": category,
                "surface": group["surface_property"],
                "distance": result["hit"]["distance"],
                "position": result["hit"]["position"],
            })

    hits.sort(key=lambda item: item["distance"])

    print("Checked triangles:", checked_triangles)
    print("Intersection groups:", len(hits))

    if hits:
        print("Nearest intersection:")
        print(" Group:", hits[0]["group"])
        print(" Surface:", hits[0]["surface"])
        print(" Distance:", hits[0]["distance"])
        print(" Position:", hits[0]["position"])
    else:
        print("No intersection in selected groups")

    return hits



def main():
    if len(sys.argv) not in (2, 8):
        print(
            "Usage: python -m scripts.check_real_los "
            "<gltf> [start_x start_y start_z end_x end_y end_z]"
        )
        return

    groups = load_physics_mesh(sys.argv[1])

    if len(sys.argv) == 8:
        try:
            start = np.array(
                [float(x) for x in sys.argv[2:5]]
            )
            end = np.array(
                [float(x) for x in sys.argv[5:8]]
            )
        except ValueError:
            print("Invalid coordinates")
            return

        if not np.isfinite(start).all() or not np.isfinite(end).all():
            print("Coordinates must be finite")
            return

        print("Start:", start)
        print("End:", end)
        check_ray(groups, start, end)
        return

    for height in (0, 48, 64):
        print("\n=== RAY HEIGHT:", height, "===")

        check_ray(
            groups,
            ACTOR + [0, 0, height],
            KILLER + [0, 0, height],
        )


if __name__ == "__main__":
    main()
