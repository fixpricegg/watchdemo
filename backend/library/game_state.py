"""Read-only tick snapshots for WatchDemo Library.

Ground truth is kept separate from evaluator-safe information.
This module only normalizes facts already present in parsed tick streams.
"""
import math
import pandas as pd


def scalar(value):
    if value is None:
        return None
    if isinstance(value, (list, dict, tuple, set)):
        return value
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    return value


def number(value):
    value = scalar(value)
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def integer(value):
    value = scalar(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def boolean(value):
    value = scalar(value)
    if value is None:
        return None
    return bool(value)


def player_from_row(row, geometry=None):
    """Normalize one player's measured state at one sampled tick.

    This is ground-truth state from the demo. It does NOT imply that opponents
    knew any of these values at this tick.
    """
    from information import normalize_steamid

    position = {
        axis.lower(): number(row.get(axis))
        for axis in ("X", "Y", "Z")
    }

    area_id = None
    if (
        geometry is not None
        and all(v is not None for v in position.values())
    ):
        area = geometry.find_area(
            position["x"],
            position["y"],
            position["z"],
        )
        if area is not None:
            area_id = int(area["id"])

    velocity = {
        "speed": number(row.get("velocity")),
        "x": number(row.get("velocity_X")),
        "y": number(row.get("velocity_Y")),
        "z": number(row.get("velocity_Z")),
    }

    return {
        # Identity / side
        "steamid": normalize_steamid(row.get("steamid")),
        "name": scalar(row.get("name")),
        "team": integer(row.get("team_num")),
        "sample_tick": int(row["tick"]),

        # Position / map
        "position": position,
        "nav_area_id": area_id,

        # View direction
        "view": {
            "yaw": number(row.get("yaw")),
            "pitch": number(row.get("pitch")),
        },

        # Movement
        "movement": {
            "velocity": velocity,
            "is_walking": boolean(row.get("is_walking")),
            "is_airborne": boolean(row.get("is_airborne")),
            "in_crouch": boolean(row.get("in_crouch")),
            "duck_amount": number(row.get("duck_amount")),
            "is_strafing": boolean(row.get("is_strafing")),
        },

        # Life / survivability
        "status": {
            "health": integer(row.get("health")),
            "armor": integer(row.get("armor")),
            "has_helmet": boolean(row.get("has_helmet")),
            "has_defuser": boolean(row.get("has_defuser")),
            "is_alive": boolean(row.get("is_alive")),
            "flash_duration": number(row.get("flash_duration")),
        },

        # Economy / equipment
        "economy": {
            "balance": integer(row.get("balance")),
            "start_balance": integer(row.get("start_balance")),
            "cash_spent_this_round": integer(row.get("cash_spent_this_round")),
            "current_equip_value": integer(row.get("current_equip_value")),
            "round_start_equip_value": integer(row.get("round_start_equip_value")),
        },

        # Weapon state
        "weapon": {
            "active": scalar(row.get("active_weapon_name")),
            "clip_ammo": integer(row.get("active_weapon_ammo")),
            "reserve_ammo": integer(row.get("total_ammo_left")),
            "is_reloading": boolean(row.get("is_in_reload")),
            "is_scoped": boolean(row.get("is_scoped")),
            "shots_fired": integer(row.get("shots_fired")),
        },

        # Whole carried inventory. We will normalize grenades/weapons later.
        "inventory": scalar(row.get("inventory")),
    }


def find_round(round_intervals, tick):
    for match_round, demo_round, start, end in round_intervals:
        if int(start) <= tick < int(end):
            return {
                "number": int(match_round),
                "demo_number": int(demo_round),
                "live_start_tick": int(start),
                "end_tick": int(end),
            }
    return None
