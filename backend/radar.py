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

def normalize_inventory(value):
    if value is None:
        return []

    if hasattr(value, "tolist"):
        value = value.tolist()

    if not isinstance(value, (list, tuple)):
        if pd.isna(value):
            return []

        value = [value]

    result = []

    for item in value:
        if item is None:
            continue

        if isinstance(item, float) and pd.isna(item):
            continue

        result.append(str(item))

    return sorted(result)


def normalize_optional_int(value):
    if value is None or pd.isna(value):
        return None

    return int(value)

def normalize_optional_bool(value):
    if value is None or pd.isna(value):
        return None

    return bool(value)


def normalize_optional_string(value):
    if value is None or pd.isna(value):
        return None

    return str(value)


def create_player_state(row):
    return {
        "tick": int(row["tick"]),
        "health": normalize_optional_int(row.get("health")),
        "armor": normalize_optional_int(row.get("armor")),
        "has_helmet": normalize_optional_bool(
            row.get("has_helmet")
        ),
        "active_weapon": normalize_optional_string(
            row.get("active_weapon_name")
        ),
        "inventory": normalize_inventory(
            row.get("inventory")
        ),
    }

def player_state_changed(previous_state, current_state):
    if previous_state is None:
        return True

    fields = [
        "health",
        "armor",
        "has_helmet",
        "active_weapon",
        "inventory",
    ]

    return any(
        previous_state.get(field) != current_state.get(field)
        for field in fields
    )

def create_player_position(
    tick,
    x,
    y,
    z,
    is_alive,
    team=None,
    yaw=None,
    include_z=False,
):
    position = {
        "tick": int(tick),
        "x": round(x),
        "y": round(y),
        "is_alive": bool(is_alive),
        "team": team,
        "yaw": (
            round(float(yaw), 1)
            if yaw is not None and not pd.isna(yaw)
            else None
        ),
    }

    if include_z:
        position["z"] = round(z)

    return position


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
        "grenades": [],
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

def _find_event_player_position(
    sampled_position_df,
    event_tick,
    player_steamid=None,
    player_name=None,
):
    rows = sampled_position_df

    if player_steamid is not None and "steamid" in rows.columns:
        rows = rows[
            rows["steamid"].apply(_safe_int)
            == int(player_steamid)
        ]
    elif player_name is not None and "name" in rows.columns:
        rows = rows[
            rows["name"] == player_name
        ]
    else:
        return None

    if rows.empty:
        return None

    rows = rows.copy()
    rows["tick_distance"] = (
        rows["tick"].astype(int) - int(event_tick)
    ).abs()

    rows = rows.sort_values(
        ["tick_distance", "tick"]
    )

    closest_row = rows.iloc[0]

    # У нас radar sample каждые 8 тиков.
    # Больше 16 тиков уже подозрительно далеко от события.
    if int(closest_row["tick_distance"]) > RADAR_TICK_STEP * 2:
        return None

    return closest_row


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
        "x": None,
        "y": None,
        "z": None,
        "position_accuracy": "unknown",
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

            event_player_row = _find_event_player_position(
                sampled_position_df,
                event_tick=event_tick,
                player_steamid=event.get("player_steamid"),
                player_name=event.get("player_name"),
            )

            event_x = None
            event_y = None
            event_z = None

            if event_player_row is not None:
                event_x = _safe_float(event_player_row.get("X"))
                event_y = _safe_float(event_player_row.get("Y"))
                event_z = _safe_float(event_player_row.get("Z"))

            if event_name == "round_reset":
                current = {
                    "state": "unavailable",
                    "state_since_tick": event_tick,
                    "carrier_steamid": None,
                    "carrier_name": None,
                    "site": None,
                    "x": None,
                    "y": None,
                    "z": None,
                    "position_accuracy": "unknown",
                    "source": "round_reset",
                }


            elif (
                    event_name == "bomb_dropped"
                    and current["state"] not in LOCKED_BOMB_STATES

            ):

                current.update({

                    "state": "dropped",

                    "state_since_tick": event_tick,

                    "carrier_steamid": None,

                    "carrier_name": None,

                    "x": event_x,

                    "y": event_y,

                    "z": event_z,

                    "position_accuracy": (

                        "event_player_position"

                        if event_x is not None and event_y is not None

                        else "unknown"

                    ),

                    "source": "bomb_dropped",

                })


            elif (

                    event_name == "bomb_pickup"

                    and current["state"] not in LOCKED_BOMB_STATES

            ):

                current.update({

                    "state": "carried",

                    "state_since_tick": event_tick,

                    "carrier_steamid": event.get("player_steamid"),

                    "carrier_name": event.get("player_name"),

                    "site": None,

                    "x": None,

                    "y": None,

                    "z": None,

                    "position_accuracy": "unknown",

                    "source": "bomb_pickup",

                })


            elif event_name == "bomb_planted":

                current.update({

                    "state": "planted",

                    "state_since_tick": event_tick,

                    "carrier_steamid": None,

                    "carrier_name": None,

                    "site": event.get("site"),

                    "x": event_x,

                    "y": event_y,

                    "z": event_z,

                    "position_accuracy": (

                        "event_player_position"

                        if event_x is not None and event_y is not None

                        else "unknown"

                    ),

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

        x = current.get("x")
        y = current.get("y")
        z = current.get("z")
        position_accuracy = current.get(
            "position_accuracy",
            "unknown",
        )

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
                current["x"] = x
                current["y"] = y
                current["z"] = z
                current["position_accuracy"] = "carrier_position"

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


GRENADE_TYPE_MAP = {
    "CSmokeGrenadeProjectile": "smoke",
    "CFlashbangProjectile": "flash",
    "CHEGrenadeProjectile": "he",
    "CMolotovProjectile": "molotov",
    "CDecoyProjectile": "decoy",
}

GRENADE_EVENT_CONFIG = {
    "flash": {
        "detonate": "flashbang_detonate",
    },
    "he": {
        "detonate": "hegrenade_detonate",
    },
    "smoke": {
        "detonate": "smokegrenade_detonate",
        "expire": "smokegrenade_expired",
    },
    "molotov": {
        "detonate": "inferno_startburn",
        "expire": "inferno_expire",
    },
    "decoy": {
        "detonate": "decoy_started",
        "expire": "decoy_detonate",
    },
}


def _find_matching_grenade_event(
    event_df,
    thrower_steamid,
    target_tick,
    min_tick=None,
    max_tick_gap=512,
    target_x=None,
    target_y=None,
    target_z=None,
    entity_id=None,
    max_position_gap=128,
):
    if (
        event_df is None
        or not isinstance(event_df, pd.DataFrame)
        or event_df.empty
        or "tick" not in event_df.columns
    ):
        return None

    candidates = event_df.copy()

    if entity_id is not None and "entityid" in candidates.columns:
        entity_candidates = candidates[
            candidates["entityid"].apply(_safe_int)
            == int(entity_id)
            ]

        if not entity_candidates.empty:
            candidates = entity_candidates

    if thrower_steamid is not None and "user_steamid" in candidates.columns:
        candidates = candidates[
            candidates["user_steamid"].apply(_safe_int)
            == int(thrower_steamid)
        ]

    if min_tick is not None:
        candidates = candidates[
            candidates["tick"].astype(int) >= int(min_tick)
        ]

    if candidates.empty:
        return None

    candidates = candidates.copy()

    candidates["tick_distance"] = (
        candidates["tick"].astype(int) - int(target_tick)
    ).abs()

    has_target_position = (
        target_x is not None
        and target_y is not None
        and "x" in candidates.columns
        and "y" in candidates.columns
    )

    if has_target_position:
        candidates["position_distance"] = (
            (candidates["x"].astype(float) - float(target_x)) ** 2
            + (candidates["y"].astype(float) - float(target_y)) ** 2
        ) ** 0.5

        candidates = candidates.sort_values(
            ["position_distance", "tick_distance", "tick"]
        )
    else:
        candidates = candidates.sort_values(
            ["tick_distance", "tick"]
        )

    closest = candidates.iloc[0]

    if int(closest["tick_distance"]) > max_tick_gap:
        return None

    # Expire должен происходить примерно в той же точке, где возник эффект.
    if has_target_position:
        if (
                float(closest["position_distance"])
                > max_position_gap
        ):
            return None

    return closest


def build_grenade_tracks(
    grenade_df,
    grenade_event_frames=None,
):
    if grenade_df is None or grenade_df.empty:
        return []

    required_columns = {
        "grenade_type",
        "grenade_entity_id",
        "x",
        "y",
        "z",
        "tick",
    }

    if not required_columns.issubset(grenade_df.columns):
        return []

    valid = grenade_df.dropna(
        subset=[
            "grenade_entity_id",
            "grenade_type",
            "x",
            "y",
            "z",
            "tick",
        ]
    ).copy()

    if valid.empty:
        return []

    valid["tick"] = valid["tick"].astype(int)
    valid["grenade_entity_id"] = valid["grenade_entity_id"].astype(int)

    tracks = []

    group_columns = [
        "grenade_entity_id",
        "grenade_type",
    ]

    grenade_event_frames = grenade_event_frames or {}

    for group_key, entity_group in valid.groupby(
            group_columns,
            sort=False,
    ):
        entity_id, raw_type = group_key

        entity_group = (
            entity_group
            .sort_values("tick")
            .reset_index(drop=True)
        )

        entity_group["tick_gap"] = (
            entity_group["tick"]
            .diff()
            .fillna(1)
        )

        entity_group["track_segment"] = (
                entity_group["tick_gap"] > 2
        ).cumsum()

        for _, group in entity_group.groupby(
                "track_segment",
                sort=False,
        ):
            grenade_type = GRENADE_TYPE_MAP.get(str(raw_type))

            if grenade_type is None:
                continue

            group = group.sort_values("tick").reset_index(drop=True)

            sampled = group.iloc[::RADAR_TICK_STEP].copy()

            if (
                    sampled.empty
                    or sampled.iloc[-1]["tick"] != group.iloc[-1]["tick"]
            ):
                sampled = pd.concat(
                    [sampled, group.iloc[[-1]]],
                    ignore_index=True,
                )

            first_row = group.iloc[0]
            last_row = group.iloc[-1]

            steamid = _safe_int(first_row.get("steamid"))
            thrower_name = _python_value(first_row.get("name"))

            positions = []

            for _, row in sampled.iterrows():
                positions.append({
                    "tick": int(row["tick"]),
                    "x": round(float(row["x"])),
                    "y": round(float(row["y"])),
                    "z": round(float(row["z"])),
                })

            start_tick = int(first_row["tick"])
            end_tick = int(last_row["tick"])

            event_config = GRENADE_EVENT_CONFIG.get(
                grenade_type,
                {},
            )

            detonate_event_name = event_config.get("detonate")
            expire_event_name = event_config.get("expire")

            detonate_row = None
            expire_row = None
            has_effect = True

            if detonate_event_name:
                if grenade_type == "molotov":
                    # У летящего молика и возникшего огня
                    # разные entityid.
                    # Ищем реальное начало огня рядом
                    # с последней точкой полёта молика.
                    detonate_row = _find_matching_grenade_event(
                        grenade_event_frames.get(
                            detonate_event_name
                        ),
                        thrower_steamid=None,
                        target_tick=end_tick,
                        min_tick=max(
                            start_tick,
                            end_tick - 64,
                        ),
                        max_tick_gap=2 * 64,
                        target_x=_safe_float(
                            last_row.get("x")
                        ),
                        target_y=_safe_float(
                            last_row.get("y")
                        ),
                        target_z=_safe_float(
                            last_row.get("z")
                        ),
                        entity_id=None,
                        max_position_gap=256,
                    )
                else:
                    detonate_row = _find_matching_grenade_event(
                        grenade_event_frames.get(
                            detonate_event_name
                        ),
                        thrower_steamid=steamid,
                        target_tick=start_tick,
                        min_tick=start_tick,
                        max_tick_gap=64 * 30,
                        entity_id=entity_id,
                    )
            # Если inferno_startburn не возник,
            # значит реального огня не было.
            # Например, молик сразу упал в дым.
            if (
                    grenade_type == "molotov"
                    and detonate_row is None
            ):
                has_effect = False

            detonate_tick = (
                int(detonate_row["tick"])
                if detonate_row is not None
                else end_tick
            )

            if expire_event_name and has_effect:
                expire_entity_id = entity_id
                expire_thrower_steamid = steamid
                expected_lifetime_ticks = 18 * 64
                expire_max_tick_gap = 30 * 64
                expire_position_gap = 128

                if grenade_type == "molotov":
                    # inferno_startburn и inferno_expire
                    # используют entityid самого огня.
                    expire_entity_id = _safe_int(
                        detonate_row.get("entityid")
                    )
                    expire_thrower_steamid = None
                    expected_lifetime_ticks = 7 * 64
                    expire_max_tick_gap = 10 * 64
                    expire_position_gap = 256

                expire_row = _find_matching_grenade_event(
                    grenade_event_frames.get(
                        expire_event_name
                    ),
                    thrower_steamid=
                    expire_thrower_steamid,
                    target_tick=(
                            detonate_tick
                            + expected_lifetime_ticks
                    ),
                    min_tick=detonate_tick + 1,
                    max_tick_gap=expire_max_tick_gap,
                    target_x=(
                        _safe_float(
                            detonate_row.get("x")
                        )
                        if detonate_row is not None
                        else None
                    ),
                    target_y=(
                        _safe_float(
                            detonate_row.get("y")
                        )
                        if detonate_row is not None
                        else None
                    ),
                    target_z=(
                        _safe_float(
                            detonate_row.get("z")
                        )
                        if detonate_row is not None
                        else None
                    ),
                    entity_id=expire_entity_id,
                    max_position_gap=expire_position_gap,
                )

            if not has_effect:
                effect_end_tick = detonate_tick
            elif expire_row is not None:
                effect_end_tick = int(
                    expire_row["tick"]
                )
            elif grenade_type == "smoke":
                effect_end_tick = (
                        detonate_tick + 18 * 64
                )
            elif grenade_type == "molotov":
                effect_end_tick = (
                        detonate_tick + 7 * 64
                )
            else:
                effect_end_tick = detonate_tick

            effect_x = None
            effect_y = None
            effect_z = None

            if detonate_row is not None:
                effect_x = _safe_float(detonate_row.get("x"))
                effect_y = _safe_float(detonate_row.get("y"))
                effect_z = _safe_float(detonate_row.get("z"))

            tracks.append({
                "track_id": f"{int(entity_id)}-{start_tick}",
                "entity_id": int(entity_id),
                "type": grenade_type,
                "has_effect": has_effect,
                "raw_type": str(raw_type),
                "thrower_steamid": steamid,
                "thrower_name": thrower_name,

                "start_tick": start_tick,
                "projectile_end_tick": detonate_tick,

                "effect_start_tick": detonate_tick,
                "effect_end_tick": effect_end_tick,

                "effect_x": (
                    round(effect_x)
                    if effect_x is not None
                    else positions[-1]["x"]
                ),
                "effect_y": (
                    round(effect_y)
                    if effect_y is not None
                    else positions[-1]["y"]
                ),
                "effect_z": (
                    round(effect_z)
                    if effect_z is not None
                    else positions[-1]["z"]
                ),

                "positions": positions,
            })

    return tracks

def build_radar_match(
    position_df,
    map_name,
    player_info,
    bomb_event_frames=None,
    round_reset_ticks=None,
    grenade_df=None,
    grenade_event_frames=None,
):
    radar_match = create_radar_match(map_name)
    radar_match["grenades"] = build_grenade_tracks(
        grenade_df,
        grenade_event_frames=grenade_event_frames,
    )

    team_by_steamid = {
        int(row["steamid"]): int(row["team_number"])
        for _, row in player_info.iterrows()
    }

    valid_position_df = position_df[
        position_df["tick"].notna()
    ].copy()

    valid_position_df["tick"] = (
        valid_position_df["tick"].astype(int)
    )

    sampled_position_df = valid_position_df[
        valid_position_df["tick"] % RADAR_TICK_STEP == 0
        ].copy()

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
                "states": [],
            }

        radar_match["players"][steamid]["positions"].append(
            create_player_position(
                row["tick"],
                row["X"],
                row["Y"],
                row["Z"],
                row["is_alive"],
                current_team,
                row.get("yaw"),
                include_z=(map_name == "de_nuke"),
            )
        )

    for steamid, player in radar_match["players"].items():
        player_rows = valid_position_df[
            valid_position_df["steamid"].astype(int) == int(steamid)
            ].sort_values("tick")

        previous_state = None

        for _, row in player_rows.iterrows():
            current_state = create_player_state(row)

            if not player_state_changed(
                    previous_state,
                    current_state,
            ):
                continue

            player["states"].append(current_state)
            previous_state = current_state

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
        pos = get_player_position(
            radar_match,
            steamid,
            tick,
        )

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
