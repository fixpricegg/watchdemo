
import math


def assess_smoke_visibility(
    player_position,
    enemy_position,
    active_utility,
    *,
    radius=160.0,
):
    result = {
        "status": "unknown",
        "model": "approximate_spherical_smoke",
        "smokes_checked": 0,
        "possible_blockers": [],
        "line_of_sight_verified": False,
        "limitations": [
            "Smoke volume is approximate.",
            "Positions are player origins, not eye positions.",
            "No visibility verdict is established.",
        ],
    }

    if not isinstance(active_utility, dict):
        return result

    def point(position):
        try:
            values = [
                float(position[axis])
                for axis in ("x", "y", "z")
            ]
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

        if not all(math.isfinite(v) for v in values):
            return None

        return values

    start = point(player_position)
    end = point(enemy_position)

    if start is None or end is None:
        return result

    direction = [
        end[i] - start[i]
        for i in range(3)
    ]

    length_squared = sum(v * v for v in direction)

    if length_squared < 1e-9:
        return result

    for smoke in active_utility.get("ongoing_candidates", []):
        if smoke.get("type") != "smoke":
            continue

        center = point(smoke)

        if center is None:
            continue

        projection = sum(
            (center[i] - start[i]) * direction[i]
            for i in range(3)
        ) / length_squared

        projection = max(0.0, min(1.0, projection))

        closest = [
            start[i] + projection * direction[i]
            for i in range(3)
        ]

        distance = math.sqrt(sum(
            (center[i] - closest[i]) ** 2
            for i in range(3)
        ))

        result["smokes_checked"] += 1

        if distance <= radius:
            result["possible_blockers"].append({
                "entity_id": smoke.get("entity_id"),
                "start_tick": smoke.get("start_tick"),
                "distance_to_segment": round(distance, 2),
                "radius_assumption": radius,
            })

    if result["possible_blockers"]:
        result["status"] = "possible_smoke_occlusion"

    elif result["smokes_checked"]:
        result["status"] = "no_intersection_in_approximation"

    return result
