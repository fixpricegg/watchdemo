
"""Navigation evidence for a possible trade.

A nav path never proves line of sight or a valid trade.
"""

from math import isfinite, sqrt, atan2, degrees, hypot


def _valid_position(position):
    if not isinstance(position, dict):
        return False

    try:
        values = [
            float(position[axis])
            for axis in ("x", "y", "z")
        ]
    except (KeyError, TypeError, ValueError, OverflowError):
        return False

    return all(isfinite(value) for value in values)


def assess_trade_geometry(geometry, player_position, killer_position):
    result = {
        "status": "unknown",
        "player_area_id": None,
        "killer_area_id": None,
        "nav_path": None,
        "nav_distance_estimate": None,
        "vertical_separation": None,
        "line_of_sight": "not_checked",
        "trade_feasibility": "not_established",
    }

    if not (
        _valid_position(player_position)
        and _valid_position(killer_position)
    ):
        result["status"] = "invalid_position"
        return result

    result["vertical_separation"] = round(
        abs(
            float(player_position["z"])
            - float(killer_position["z"])
        ),
        2,
    )

    if geometry is None:
        result["status"] = "geometry_unavailable"
        return result

    player_area = geometry.find_area(
        player_position["x"],
        player_position["y"],
        player_position["z"],
    )

    killer_area = geometry.find_area(
        killer_position["x"],
        killer_position["y"],
        killer_position["z"],
    )

    if player_area is None or killer_area is None:
        result["status"] = "area_unknown"
        return result

    start_id = int(player_area["id"])
    end_id = int(killer_area["id"])

    result["player_area_id"] = start_id
    result["killer_area_id"] = end_id

    path = geometry.shortest_path(start_id, end_id)

    if path is None:
        result["status"] = "no_nav_path"
        return result

    distance = 0.0

    for index in range(1, len(path)):
        first = geometry.areas[path[index - 1]]
        second = geometry.areas[path[index]]

        distance += geometry.area_distance(
            first, second
        )

    result["status"] = "nav_connected"
    result["nav_path"] = list(path)
    result["nav_distance_estimate"] = round(
        distance, 2
    )

    return result


def assess_trade_static_collision(
    match_library,
    player_position,
    killer_position,
):
    result = {
        "status": "unknown",
        "reason": "not_checked",
        "trace": None,
        "endpoint_model": "sampled_player_origins",
        "line_of_sight_verified": False,
    }

    if not (
        _valid_position(player_position)
        and _valid_position(killer_position)
    ):
        result["reason"] = "invalid_position"
        return result

    start = [
        float(player_position[axis])
        for axis in ("x", "y", "z")
    ]
    end = [
        float(killer_position[axis])
        for axis in ("x", "y", "z")
    ]

    if not callable(getattr(match_library, "trace_static_line", None)):
        result["reason"] = "collision_geometry_unavailable"
        return result

    trace = match_library.trace_static_line(start, end)

    result["status"] = trace["status"]
    result["reason"] = trace["reason"]
    result["trace"] = trace

    return result

def assess_view_direction(observer_position, target_position, yaw):
    result = {
        "status": "unknown",
        "model": "horizontal_direction_only",
        "target_bearing_deg": None,
        "horizontal_yaw_offset_deg": None,
        "line_of_sight_verified": False,
    }

    if not (
        _valid_position(observer_position)
        and _valid_position(target_position)
    ):
        return result

    if isinstance(yaw, bool):
        return result

    try:
        yaw = float(yaw)
    except (TypeError, ValueError, OverflowError):
        return result

    if not isfinite(yaw):
        return result

    dx = (
        float(target_position["x"])
        - float(observer_position["x"])
    )
    dy = (
        float(target_position["y"])
        - float(observer_position["y"])
    )

    if hypot(dx, dy) < 1e-9:
        result["status"] = "coincident_xy"
        return result

    bearing = degrees(atan2(dy, dx)) % 360
    difference = (bearing - yaw + 180) % 360 - 180

    result["status"] = "observed"
    result["target_bearing_deg"] = round(bearing, 2)
    result["horizontal_yaw_offset_deg"] = round(
        abs(difference), 2
    )

    return result


def assess_support_geometry(
    match_library,
    actor_position,
    teammate_position,
    killer_position,
    *,
    include_static_trace=False,
    actor_yaw=None,
    teammate_yaw=None,
):
    result = {
        "status": "unknown",
        "scope": "post_match_ground_truth",
        "support_opportunity": "not_established",
        "line_of_sight_verified": False,
        "distances_2d": None,
        "vertical_separations": None,
        "navigation": None,
        "static_collision": None,
    }

    positions = (
        actor_position,
        teammate_position,
        killer_position,
    )

    if not all(_valid_position(p) for p in positions):
        result["status"] = "invalid_position"
        return result

    def distance_2d(first, second):
        return round(sqrt(
            (float(first["x"]) - float(second["x"])) ** 2
            + (float(first["y"]) - float(second["y"])) ** 2
        ), 2)

    def height_difference(first, second):
        return round(abs(
            float(first["z"]) - float(second["z"])
        ), 2)

    result["distances_2d"] = {
        "actor_to_teammate": distance_2d(
            actor_position, teammate_position
        ),
        "actor_to_killer": distance_2d(
            actor_position, killer_position
        ),
        "teammate_to_killer": distance_2d(
            teammate_position, killer_position
        ),
    }

    result["vertical_separations"] = {
        "actor_to_killer": height_difference(
            actor_position, killer_position
        ),
        "teammate_to_killer": height_difference(
            teammate_position, killer_position
        ),
    }

    geometry = getattr(match_library, "geometry", None)

    result["navigation"] = {
        "actor_to_killer": assess_trade_geometry(
            geometry, actor_position, killer_position
        ),
        "teammate_to_killer": assess_trade_geometry(
            geometry, teammate_position, killer_position
        ),
    }

    if include_static_trace:
        result["static_collision"] = {
            "actor_to_killer": assess_trade_static_collision(
                match_library, actor_position, killer_position
            ),
            "teammate_to_killer": assess_trade_static_collision(
                match_library, teammate_position, killer_position
            ),
        }

    result["view_direction"] = {
        "actor_to_killer": assess_view_direction(
            actor_position,
            killer_position,
            actor_yaw,
        ),
        "teammate_to_killer": assess_view_direction(
            teammate_position,
            killer_position,
            teammate_yaw,
        ),
    }


    result["status"] = "positions_observed"

    return result

