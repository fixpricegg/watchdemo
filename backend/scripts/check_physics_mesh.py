
import sys
import numpy as np

from library.physics_mesh import load_physics_mesh


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_physics_mesh.py <gltf>")
        return

    groups = load_physics_mesh(sys.argv[1])
    total = 0

    for group in groups:
        triangles = group["triangles_local"]
        total += len(triangles)

        print()
        print("Group:", group["name"])
        print("Surface:", group["surface_property"])
        print("InteractAs:", group["interact_as"])
        print("Triangles:", len(triangles))

        if len(triangles):
            points = triangles.reshape(-1, 3)

            print("Min XYZ:", np.min(points, axis=0))
            print("Max XYZ:", np.max(points, axis=0))

    print()
    print("Total groups:", len(groups))
    print("Total triangles:", total)


if __name__ == "__main__":
    main()
