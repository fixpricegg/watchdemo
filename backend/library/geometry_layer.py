
import numpy as np

from .physics_mesh import load_physics_mesh
from .collision_groups import classify_collision_group
from .line_of_sight import trace_segment


class GeometryLayer:
    def __init__(
        self,
        groups,
        *,
        allow_experimental_clear=False,
    ):
        self.allow_experimental_clear = allow_experimental_clear
        self.groups = []

        for group in groups:
            triangles = np.asarray(
                group["triangles_local"],
                dtype=np.float64,
            )

            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
                raise ValueError("Invalid triangle shape")

            if not np.isfinite(triangles).all():
                raise ValueError("Non-finite geometry")

            self.groups.append({
                "name": group.get("name"),
                "surface": group.get("surface_property"),
                "category": classify_collision_group(group),
                "triangles": triangles,
            })

        self.triangle_count = sum(
            len(group["triangles"])
            for group in self.groups
        )

    @classmethod
    def from_gltf(
        cls,
        path,
        *,
        allow_experimental_clear=False,
    ):
        groups = load_physics_mesh(path)

        return cls(
            groups,
            allow_experimental_clear=allow_experimental_clear,
        )

    def trace_line(self, start, end):
        start = np.asarray(start, dtype=np.float64)
        end = np.asarray(end, dtype=np.float64)

        if start.shape != (3,) or end.shape != (3,):
            raise ValueError("Positions must be 3D")

        if not (
            np.isfinite(start).all()
            and np.isfinite(end).all()
        ):
            raise ValueError("Positions must be finite")

        distance = float(np.linalg.norm(end - start))

        result = {
            "status": "unknown",
            "reason": None,
            "distance": round(distance, 4),
            "hit": None,
            "model": "static_collision_candidates",
            "validation": "experimental",
            "dynamic_obstacles_checked": False,
            "game_bullet_trace": False,
        }

        if distance < 1e-9:
            result["reason"] = "degenerate_segment"
            return result

        if self.triangle_count == 0:
            result["reason"] = "empty_geometry"
            return result

        solid_hits = []
        uncertain_hits = []

        for group in self.groups:
            category = group["category"]

            if category == "special_collision":
                continue

            triangles = group["triangles"]

            if len(triangles) == 0:
                continue

            trace = trace_segment(
                start, end, triangles
            )

            if trace["status"] != "intersection":
                continue

            hit = {
                "group": group["name"],
                "surface": group["surface"],
                "category": category,
                **trace["hit"],
            }

            if category in (
                "solid_candidate",
                "explicit_los_blocker",
            ):
                solid_hits.append(hit)
            else:
                uncertain_hits.append(hit)

        solid_hits.sort(key=lambda hit: hit["distance"])
        uncertain_hits.sort(key=lambda hit: hit["distance"])


        if uncertain_hits and (
            not solid_hits
            or uncertain_hits[0]["distance"] < solid_hits[0]["distance"]
        ):
            result["reason"] = "uncertain_surface_intersection"
            result["hit"] = uncertain_hits[0]
            return result


        if solid_hits:
            nearest = solid_hits[0]

            result["status"] = "blocked"
            result["reason"] = "candidate_solid_intersection"
            result["hit"] = nearest

            if uncertain_hits:
                result["nearest_uncertain_hit"] = uncertain_hits[0]

            return result

        if uncertain_hits:
            result["reason"] = "uncertain_surface_intersection"
            result["hit"] = uncertain_hits[0]
            return result

        if self.allow_experimental_clear:
            result["status"] = "clear"
            result["reason"] = "no_intersection_in_selected_mesh"
        else:
            result["reason"] = "no_intersection_unvalidated_geometry"

        return result
