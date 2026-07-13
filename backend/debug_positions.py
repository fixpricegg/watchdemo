from demoparser2 import DemoParser
from demo_script import deaths_clean, player_info
import pandas as pd
import math

demo_path = "demos/match10.dem"

parser = DemoParser(demo_path)
pd.set_option("display.max_columns", None)



def distance_2d(pos1, pos2):
    if pos1 is None or pos2 is None:
        return None

    return math.sqrt(
        (pos1["x"] - pos2["x"]) ** 2 +
        (pos1["y"] - pos2["y"]) ** 2
    )

try:
    position_df = parser.parse_ticks([
        "tick",
        "name",
        "steamid",
        "X",
        "Y",
        "Z",
        "is_alive"
    ])



except Exception as e:
    print("POSITION PARSE ERROR:", e)

def get_position_at_tick(position_df, steamid, tick):
    player_positions = position_df[
        (position_df["steamid"] == steamid) &
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

print("\n== TEAMMATE DEATH DISTANCES ==")

player_name = "k1tagawaaa"

player_row = player_info[player_info["name"] == player_name]
player_steamid = int(player_row.iloc[0]["steamid"])

player_team = int(player_row.iloc[0]["team_number"])
print("\nPLAYER:")
print(player_name)
print("team:", player_team)

teammate_deaths = deaths_clean[
    (deaths_clean["user_name"] != player_name)
]

missed_trades = 0

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
        print(
            "NOT FOUND:",
            dead_steamid,
            death["user_name"]
        )
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
        int(death["user_steamid"]),
        death_tick
    )

    distance = distance_2d(dead_pos, player_pos)

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


    if not killer_death.empty:

        killer_death_tick = int(
            killer_death.iloc[0]["tick"]
        )

        killer_alive_ticks = (
                killer_death_tick - death_tick
        )

    else:

        killer_alive_ticks = None

    killer_pos = get_position_at_tick(
        position_df,
        int(killer_steamid),
        death_tick
    )


    distance_to_killer = distance_2d(
        player_pos,
        killer_pos
    )

    if (
            distance is not None
            and distance_to_killer is not None
            and killer_alive_ticks is not None
    ):

        if (
                distance <= 700
                and distance_to_killer <= 800
                and killer_alive_ticks >= 128
        ):
            missed_trades += 1

            print(
                f"MISSED TRADE | "
                f"Round {death['round']} | "
                f"Dead: {death['user_name']} died | "
                f"Killer: {death['attacker_name']} | "
                f"Teammate distance = {distance:.0f} | "
                f"Killer distance = {distance_to_killer:.0f} | "
                f"Killer Alive ticks = {killer_alive_ticks}"
            )

print()
print("MISSED TRADES:", missed_trades)