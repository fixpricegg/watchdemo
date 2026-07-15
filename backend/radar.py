import json
from typing import Any

import pandas as pd

RADAR_TICK_STEP = 8

MAP_INFO = {
    "de_inferno": {
        "pos_x": -2087,
        "pos_y": 3870,
        "scale": 4.9,
    }
}

# Events that change the persistent bomb state.
BOMB_STATE_EVENTS = {
    "bomb_dropped": {"state": "dropped", "priority": 10},
    "bomb_pickup": {"state": "carried", "priority": 20},
    "bomb_planted": {"state": "planted", "priority": 30},
    "bomb_defused": {"state": "defused", "priority": 40},
    "bomb_exploded": {"state": "exploded", "priority": 40},
}

# Useful for Timeline/debug, but these do not change the persistent state.
BOMB_AUXILIARY_EVENTS = {
    "bomb_beginplant": 25,
    "bomb_abortplant": 26,
    "bomb_begindefuse": 35,
    "bomb_abortdefuse": 36,
}

LOCKED_BOMB_STATES = {"planted", "defused", "exploded"}


def normalize_coordinates(x, y, map_name):
    map_info = MAP_INFO[map_name]

    image_x = (x - map_info["pos_x"]) / map_info["scale"]
    image_y = (map_info["pos_y"] - y) / map_info["scale"]

    return round(image_x), round(image_y)


def get_map_name(parser):
    header = parser.parse_header()
    return header["map_name"]


def create_position(role, x, y, z):
    return {
        "role": role,
        "x": round(x),
        "y": round(y),
        "z": round(z),
    }


def create_radar_event(event_type, tick, positions):
    return {
        "type": event_type,
        "tick": tick,
        "positions": positions,
    }


def create_player_position(tick, x, y, z, is_alive, team=None):
    return {
        "tick": int(tick),
        "x": round(x),
        "y": round(y),
        "is_alive": bool(is_alive),
        "team": team,
    }


def get_player_position(radar_match, steamid, tick):
    if steamid not in radar_match["players"]:
        return None

    positions = radar_match["players"][steamid]["positions"]
    closest_position = None

    for pos in positions:
        if pos["tick"] <= tick:
            closest_position = pos
        else:
            break

    return closest_position


def get_all_players_positions(radar_match, tick):
    positions = {}

    for steamid in radar_match["players"]:
        pos = get_player_position(radar_match, steamid, tick)

        if pos is not None:
            positions[steamid] = pos

    return positions


def create_radar_match(map_name):
    return {
        "map": map_name,
        "players": {},
        "bomb": {
            "states": [],
            "events": [],
        },
    }


def _python_value(value: Any):
    """Convert pandas/numpy scalars to JSON-friendly Python values."""
    if value is None or pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value


def _safe_int(value):
    value = _python_value(value)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value):
    value = _python_value(value)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def has_c4(inventory):
    if not isinstance(inventory, list):
        return False

    return any("c4" in str(item).lower() for item in inventory)


def create_bomb_state(
    tick,
    state,
    state_since_tick,
    carrier_steamid=None,
    carrier_name=None,
    x=None,
    y=None,
    z=None,
    site=None,
    position_accuracy="unknown",
    source=None,
):
    return {
        "tick": int(tick),
        "state": state,
        "state_since_tick": (
            int(state_since_tick) if state_since_tick is not None else None
        ),
        "carrier_steamid": _safe_int(carrier_steamid),
        "carrier_name": _python_value(carrier_name),
        "x": round(float(x)) if x is not None and not pd.isna(x) else None,
        "y": round(float(y)) if y is not None and not pd.isna(y) else None,
        "z": round(float(z)) if z is not None and not pd.isna(z) else None,
        "site": _python_value(site),
        "position_accuracy": position_accuracy,
        "source": source,
    }


def normalize_bomb_events(bomb_event_frames=None, round_reset_ticks=None):
    """
    Merge separate demoparser2 event DataFrames into one chronological stream.

    Same-tick priority matters:
    round reset -> drop -> pickup -> plant -> defuse/explode.
    This makes a same-tick handoff end in `carried`, and terminal events win.
    """
    normalized = []

    for reset_tick in round_reset_ticks or []:
        if reset_tick is None or pd.isna(reset_tick):
            continue

        normalized.append({
            "event": "round_reset",
            "tick": int(reset_tick),
            "priority": 0,
            "player_name": None,
            "player_steamid": None,
            "site": None,
            "entity_id": None,
        })

    for event_name, frame in (bomb_event_frames or {}).items():
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue

        if "tick" not in frame.columns:
            continue

        if event_name in BOMB_STATE_EVENTS:
            priority = BOMB_STATE_EVENTS[event_name]["priority"]
        elif event_name in BOMB_AUXILIARY_EVENTS:
            priority = BOMB_AUXILIARY_EVENTS[event_name]
        else:
            continue

        for _, row in frame.iterrows():
            tick = _safe_int(row.get("tick"))

            if tick is None:
                continue

            normalized.append({
                "event": event_name,
                "tick": tick,
                "priority": priority,
                "player_name": _python_value(row.get("user_name")),
                "player_steamid": _safe_int(row.get("user_steamid")),
                "site": _python_value(row.get("site")),
                "entity_id": _safe_int(row.get("entityid")),
                "has_kit": _python_value(row.get("haskit")),
            })

    normalized.sort(key=lambda event: (event["tick"], event["priority"]))
    return normalized


def _first_true(rows, column_name):
    if column_name not in rows.columns:
        return False

    values = rows[column_name].fillna(False)
    return bool(values.astype(bool).any())


def _find_carrier_row(tick_rows, preferred_steamid=None):
    if "inventory" not in tick_rows.columns:
        return None

    carrier_rows = tick_rows[tick_rows["inventory"].apply(has_c4)]

    if carrier_rows.empty:
        return None

    if preferred_steamid is not None and "steamid" in carrier_rows.columns:
        preferred = carrier_rows[
            carrier_rows["steamid"].apply(_safe_int) == int(preferred_steamid)
        ]

        if not preferred.empty:
            return preferred.iloc[0]

    return carrier_rows.iloc[0]


def build_bomb_timeline(
    sampled_position_df,
    bomb_event_frames=None,
    round_reset_ticks=None,
):
    """
    Build an event-driven bomb state machine sampled at RADAR_TICK_STEP.

    Truth sources:
    - events determine persistent transitions;
    - inventory identifies the current carrier and its coordinates;
    - game-state flags recover a missed event, but cannot undo planted/terminal states.

    Exact world coordinates for dropped/planted C4 entities are not exposed by the
    current high-level demoparser2 Python API, so those coordinates remain null.
    """
    if sampled_position_df.empty:
        return [], normalize_bomb_events(bomb_event_frames, round_reset_ticks)

    events = normalize_bomb_events(bomb_event_frames, round_reset_ticks)
    event_index = 0

    current = {
        "state": "unavailable",
        "state_since_tick": None,
        "carrier_steamid": None,
        "carrier_name": None,
        "site": None,
        "source": "initial",
    }

    states = []

    for tick, tick_rows in sampled_position_df.groupby("tick", sort=True):
        tick = int(tick)

        # Apply every event that happened since the previous radar sample.
        while event_index < len(events) and events[event_index]["tick"] <= tick:
            event = events[event_index]
            event_name = event["event"]
            event_tick = int(event["tick"])

            if event_name == "round_reset":
                current = {
                    "state": "unavailable",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "site": None,
                    "source": "round_reset",
                }

            elif event_name == "bomb_dropped" and current["state"] not in LOCKED_BOMB_STATES:
                current.update({
                    "state": "dropped",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "source": "bomb_dropped",
                })

            elif event_name == "bomb_pickup" and current["state"] not in LOCKED_BOMB_STATES:
                current.update({
                    "state": "carried",
                    "state_since_tick": event_tick,
                    "carrier_steamid": event.get("player_steamid"),
                    "carrier_name": event.get("player_name"),
                    "site": None,
                    "source": "bomb_pickup",
                })

            elif event_name == "bomb_planted":
                current.update({
                    "state": "planted",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "site": event.get("site"),
                    "source": "bomb_planted",
                })

            elif event_name == "bomb_defused":
                current.update({
                    "state": "defused",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "site": event.get("site") if event.get("site") is not None else current.get("site"),
                    "source": "bomb_defused",
                })

            elif event_name == "bomb_exploded":
                current.update({
                    "state": "exploded",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "site": event.get("site") if event.get("site") is not None else current.get("site"),
                    "source": "bomb_exploded",
                })

            event_index += 1

        carrier_row = _find_carrier_row(
            tick_rows,
            preferred_steamid=current.get("carrier_steamid"),
        )
        planted_flag = _first_true(tick_rows, "is_bomb_planted")
        dropped_flag = _first_true(tick_rows, "is_bomb_dropped")

        # Events own planted/terminal states until the next round reset.
        if current["state"] not in LOCKED_BOMB_STATES:
            if planted_flag:
                if current["state"] != "planted":
                    current["state_since_tick"] = tick
                    current["source"] = "is_bomb_planted_fallback"

                current.update({
                    "state": "planted",
                    "carrier_steamid": None,
                    "carrier_name": None,
                })

            elif carrier_row is not None:
                carrier_steamid = _safe_int(carrier_row.get("steamid"))
                carrier_name = _python_value(carrier_row.get("name"))

                if current["state"] != "carried":
                    current["state_since_tick"] = tick
                    current["source"] = "inventory"

                current.update({
                    "state": "carried",
                    "carrier_steamid": carrier_steamid,
                    "carrier_name": carrier_name,
                    "site": None,
                })

            elif dropped_flag:
                if current["state"] != "dropped":
                    current["state_since_tick"] = tick
                    current["source"] = "is_bomb_dropped_fallback"

                current.update({
                    "state": "dropped",
                    "carrier_steamid": None,
                    "carrier_name": None,
                })

        x = y = z = None
        position_accuracy = "unknown"

        if current["state"] == "carried":
            # Re-check inventory first; if unavailable, use the event carrier row.
            if carrier_row is None and current.get("carrier_steamid") is not None:
                matching_rows = tick_rows[
                    tick_rows["steamid"].apply(_safe_int)
                    == int(current["carrier_steamid"])
                ]
                if not matching_rows.empty:
                    carrier_row = matching_rows.iloc[0]

            if carrier_row is not None:
                current["carrier_steamid"] = _safe_int(carrier_row.get("steamid"))
                current["carrier_name"] = _python_value(carrier_row.get("name"))
                x = _safe_float(carrier_row.get("X"))
                y = _safe_float(carrier_row.get("Y"))
                z = _safe_float(carrier_row.get("Z"))
                position_accuracy = "carrier_position"

        states.append(
            create_bomb_state(
                tick=tick,
                state=current["state"],
                state_since_tick=current["state_since_tick"],
                carrier_steamid=current.get("carrier_steamid"),
                carrier_name=current.get("carrier_name"),
                x=x,
                y=y,
                z=z,
                site=current.get("site"),
                position_accuracy=position_accuracy,
                source=current.get("source"),
            )
        )

    return states, events


def build_radar_match(
    position_df,
    map_name,
    player_info,
    bomb_event_frames=None,
    round_reset_ticks=None,
):
    radar_match = create_radar_match(map_name)

    team_by_steamid = {
        int(row["steamid"]): int(row["team_number"])
        for _, row in player_info.iterrows()
    }

    sampled_position_df = position_df[
        position_df["tick"].notna()
    ].copy()
    sampled_position_df["tick"] = sampled_position_df["tick"].astype(int)
    sampled_position_df = sampled_position_df[
        sampled_position_df["tick"] % RADAR_TICK_STEP == 0
    ]

    bomb_states, bomb_events = build_bomb_timeline(
        sampled_position_df,
        bomb_event_frames=bomb_event_frames,
        round_reset_ticks=round_reset_ticks,
    )
    radar_match["bomb"]["states"] = bomb_states
    radar_match["bomb"]["events"] = bomb_events

    for _, row in sampled_position_df.iterrows():
        if pd.isna(row["X"]) or pd.isna(row["Y"]) or pd.isna(row["Z"]):
            continue

        steamid = int(row["steamid"])

        fallback_team = get_team_name(team_by_steamid.get(steamid))
        current_team = get_team_from_row(row, fallback_team)

        if steamid not in radar_match["players"]:
            radar_match["players"][steamid] = {
                "name": row["name"],
                "team": fallback_team,
                "positions": [],
            }

        radar_match["players"][steamid]["positions"].append(
            create_player_position(
                row["tick"],
                row["X"],
                row["Y"],
                row["Z"],
                row["is_alive"],
                current_team,
            )
        )

    return radar_match


def get_team_name(team_number):
    if team_number == 2:
        return "T"

    if team_number == 3:
        return "CT"

    return "UNKNOWN"


def get_team_from_row(row, fallback_team=None):
    if "team_num" in row and not pd.isna(row["team_num"]):
        return get_team_name(int(row["team_num"]))

    if "team_number" in row and not pd.isna(row["team_number"]):
        return get_team_name(int(row["team_number"]))

    if "team_name" in row and not pd.isna(row["team_name"]):
        team_name = str(row["team_name"]).upper()

        if team_name in ["T", "TERRORIST", "TERRORISTS"]:
            return "T"

        if team_name in ["CT", "COUNTERTERRORIST", "COUNTERTERRORISTS"]:
            return "CT"

    return fallback_team


def get_players_at_tick(radar_match, tick):
    result = []

    for steamid, player in radar_match["players"].items():
        pos = get_player_position(radar_match, steamid, tick)

        if pos is None:
            continue

        result.append({
            "name": player["name"],
            "team": pos.get("team") or player["team"],
            "x": pos["x"],
            "y": pos["y"],
            "is_alive": pos["is_alive"],
        })

    return result


def export_radar_json(
    radar_match,
    timeline_rounds,
    events,
    output_path="radar.json",
):
    radar_match["rounds"] = timeline_rounds
    radar_match["events"] = events

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(radar_match, f, ensure_ascii=False)
