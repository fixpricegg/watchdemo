import pandas as pd
import json

RADAR_TICK_STEP = 8

MAP_INFO = {
    "de_inferno": {
        "pos_x": -2087,
        "pos_y": 3870,
        "scale": 4.9
    }
}

def normalize_coordinates(
        x,
        y,
        map_name
):

    map_info = MAP_INFO[map_name]

    image_x = (x - map_info["pos_x"]) / map_info["scale"]

    image_y = (map_info["pos_y"] - y) / map_info["scale"]

    return (
        round(image_x),
        round(image_y)
    )

def get_map_name(parser):
    header = parser.parse_header()
    return header["map_name"]

def create_position(
        role,
        x,
        y,
        z
):
    return {
        "role": role,
        "x": round(x),
        "y": round(y),
        "z": round(z)
    }

def create_radar_event(
        event_type,
        tick,
        positions
):
    return {
        "type": event_type,
        "tick": tick,
        "positions": positions
    }

def create_player_position(
        tick,
        x,
        y,
        z,
        is_alive,
        team=None
):
    return {
        "tick": int(tick),
        "x": round(x),
        "y": round(y),
        "is_alive": bool(is_alive),
        "team": team
    }

def get_player_position(
        radar_match,
        steamid,
        tick
):

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

def get_all_players_positions(
        radar_match,
        tick
):
    positions = {}

    for steamid in radar_match["players"]:
        pos = get_player_position(
            radar_match,
            steamid,
            tick
        )

        if pos is not None:
            positions[steamid] = pos

    return positions

def create_radar_match(map_name):

    return {
        "map": map_name,
        "players": {}
    }

def build_radar_match(
        position_df,
        map_name,
        player_info
):

    radar_match = create_radar_match(
        map_name
    )

    team_by_steamid = {
        int(row["steamid"]): int(row["team_number"])
        for _, row in player_info.iterrows()
    }

    for _, row in position_df.iterrows():
        if (
                pd.isna(row["X"])
                or pd.isna(row["Y"])
                or pd.isna(row["Z"])
        ):
            continue

        if row["tick"] % RADAR_TICK_STEP != 0:
            continue

        steamid = int(row["steamid"])

        fallback_team = get_team_name(
            team_by_steamid.get(steamid)
        )

        current_team = get_team_from_row(
            row,
            fallback_team
        )

        if steamid not in radar_match["players"]:
            radar_match["players"][steamid] = {
                "name": row["name"],
                "team": fallback_team,
                "positions": []
            }

        radar_match["players"][steamid]["positions"].append(
            create_player_position(
                row["tick"],
                row["X"],
                row["Y"],
                row["Z"],
                row["is_alive"],
                current_team
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

        pos = get_player_position(
            radar_match,
            steamid,
            tick
        )

        if pos is None:
            continue

        result.append({
            "name": player["name"],
            "team": pos.get("team") or player["team"],
            "x": pos["x"],
            "y": pos["y"],
            "is_alive": pos["is_alive"]
        })

    return result

def export_radar_json(
        radar_match,
        timeline_rounds,
        events,
        output_path="radar.json"
):

    radar_match["rounds"] = timeline_rounds
    radar_match["events"] = events

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            radar_match,
            f,
            ensure_ascii=False
        )
