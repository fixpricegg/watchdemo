import math
import pandas as pd


def distance_2d(pos1, pos2):
    if pos1 is None or pos2 is None:
        return None

    return math.sqrt(
        (pos1["x"] - pos2["x"]) ** 2 +
        (pos1["y"] - pos2["y"]) ** 2
    )


def get_position_at_tick(position_df, steamid, tick):
    player_positions = position_df[
        (position_df["steamid"] == steamid)
        &
        (position_df["tick"] <= tick)
    ]

    if player_positions.empty:
        return None

    pos = player_positions.sort_values("tick").iloc[-1]

    return {
        "tick": int(pos["tick"]),
        "x": float(pos["X"]),
        "y": float(pos["Y"]),
        "z": float(pos["Z"]),
        "is_alive": bool(pos["is_alive"])
    }


def get_possible_missed_trades(
        player_name,
        deaths_clean,
        player_info,
        position_df
):

    missed_trade_events = []

    player_row = player_info[player_info["name"] == player_name]

    player_steamid = int(player_row.iloc[0]["steamid"])
    player_team = int(player_row.iloc[0]["team_number"])

    teammate_deaths = deaths_clean[
        deaths_clean["user_name"] != player_name
    ]

    for _, death in teammate_deaths.iterrows():

        if (
                pd.isna(death["user_steamid"])
                or pd.isna(death["attacker_steamid"])
        ):
            continue

        dead_steamid = int(death["user_steamid"])

        dead_row = player_info[
            player_info["steamid"].astype("int64") == dead_steamid
        ]

        if dead_row.empty:
            continue

        dead_team = int(dead_row.iloc[0]["team_number"])

        if dead_team != player_team:
            continue

        death_tick = int(death["tick"])

        player_pos = get_position_at_tick(
            position_df,
            player_steamid,
            death_tick
        )

        if player_pos is None:
            continue

        if not player_pos["is_alive"]:
            continue

        dead_pos = get_position_at_tick(
            position_df,
            dead_steamid,
            death_tick
        )

        killer_steamid = death["attacker_steamid"]

        if pd.isna(killer_steamid):
            continue

        killer_steamid = str(killer_steamid)

        killer_death = deaths_clean[
            (deaths_clean["user_steamid"] == killer_steamid)
            &
            (deaths_clean["tick"] > death_tick)
            &
            (deaths_clean["round"] == death["round"])
        ]

        if killer_death.empty:
            continue

        killer_death_tick = int(
            killer_death.iloc[0]["tick"]
        )

        killer_alive_ticks = (
                killer_death_tick - death_tick
        )

        killer_pos = get_position_at_tick(
            position_df,
            int(killer_steamid),
            death_tick
        )

        distance = distance_2d(
            dead_pos,
            player_pos
        )

        distance_to_killer = distance_2d(
            player_pos,
            killer_pos
        )

        if (
                distance is not None
                and distance_to_killer is not None
        ):

            if (
                    distance <= 700
                    and distance_to_killer <= 800
                    and killer_alive_ticks >= 128
            ):

                missed_trade_events.append(
                    {
                        "round": int(death["round"]),
                        "tick": death_tick,
                        "dead_teammate": death["user_name"],
                        "killer": death["attacker_name"],
                        "teammate_distance": round(distance),
                        "killer_distance": round(distance_to_killer),
                        "killer_alive_ticks": int(killer_alive_ticks)
                    }
                )

    return missed_trade_events