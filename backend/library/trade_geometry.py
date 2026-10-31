
"""Navigation evidence for a possible trade.

A nav path never proves line of sight or a valid trade.
"""

from math import isfinite, sqrt


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
