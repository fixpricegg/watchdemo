import math

import pandas as pd


DEFAULT_STEP_TICKS = 8

START_MOVE_DISTANCE = 20.0

# Короткая остановка для чека угла/стрельбы
# не заканчивает маршрут.
STOP_AFTER_TICKS = 96

MIN_EPISODE_TICKS = 48
MIN_EPISODE_DISTANCE = 180.0


def normalize_number(value):
    if value is None or pd.isna(value):
        return None

    return float(value)


def normalize_weapon(value):
    if value is None or pd.isna(value):
        return None

    return str(value)


def distance_3d(a, b):
    dx = b["x"] - a["x"]
    dy = b["y"] - a["y"]
    dz = b["z"] - a["z"]

    return math.sqrt(
        dx * dx
        + dy * dy
        + dz * dz
    )


def make_point(row):
    return {
        "tick": int(row["tick"]),

        "position": {
            "x": float(row["X"]),
            "y": float(row["Y"]),
            "z": float(row["Z"]),
        },

        "yaw": normalize_number(
            row.get("yaw")
        ),

        "health": normalize_number(
            row.get("health")
        ),

        "weapon": normalize_weapon(
            row.get("active_weapon_name")
        ),
    }


def finish_episode(
    player_name,
    round_number,
    points,
):
    if len(points) < 2:
        return None

    start = points[0]
    end = points[-1]

    duration_ticks = (
        end["tick"]
        - start["tick"]
    )

    if duration_ticks < MIN_EPISODE_TICKS:
        return None

    total_distance = 0.0

    for index in range(
        1,
        len(points),
    ):
        total_distance += distance_3d(
            points[index - 1]["position"],
            points[index]["position"],
        )

    if total_distance < MIN_EPISODE_DISTANCE:
        return None

    displacement = distance_3d(
        start["position"],
        end["position"],
    )

    duration_seconds = (
        duration_ticks / 64
    )

    efficiency = (
        displacement / total_distance
        if total_distance > 0
        else 0.0
    )

    average_speed = (
        total_distance / duration_seconds
        if duration_seconds > 0
        else 0.0
    )

    weapon_changes = []

    previous_weapon = (
        points[0]["weapon"]
    )

    for point in points[1:]:
        current_weapon = (
            point["weapon"]
        )

        if (
            current_weapon
            != previous_weapon
        ):
            weapon_changes.append({
                "tick":
                    point["tick"],

                "from":
                    previous_weapon,

                "to":
                    current_weapon,
            })

        previous_weapon = (
            current_weapon
        )

    return {
        "type":
            "movement_episode",

        "player":
            player_name,

        "round":
            int(round_number),

        "start_tick":
            int(start["tick"]),

        "end_tick":
            int(end["tick"]),

        "path": [
            {
                "tick": point["tick"],
                "position": point["position"],
                "yaw": point["yaw"],
                "weapon": point["weapon"],
                "health": point["health"],
            }
            for point in points
        ],

        "duration_ticks":
            int(duration_ticks),

        "duration_seconds":
            round(
                duration_seconds,
                2,
            ),

        "start_position":
            start["position"],

        "end_position":
            end["position"],

        "total_distance":
            round(
                total_distance,
                1,
            ),

        "displacement":
            round(
                displacement,
                1,
            ),

        "path_efficiency":
            round(
                efficiency,
                3,
            ),

        "average_speed":
            round(
                average_speed,
                1,
            ),

        "start_yaw":
            start["yaw"],

        "end_yaw":
            end["yaw"],

        "start_health":
            start["health"],

        "end_health":
            end["health"],

        "start_weapon":
            start["weapon"],

        "end_weapon":
            end["weapon"],

        "weapon_changes":
            weapon_changes,

        "sample_count":
            len(points),


    }


def build_movement_episodes(
    position_df,
    player_name,
    round_number,
    round_start_tick,
    round_end_tick,
    step_ticks=DEFAULT_STEP_TICKS,
):
    player_rows = (
        position_df[
            (position_df["name"] == player_name)
            & (
                position_df["tick"]
                >= round_start_tick
            )
            & (
                position_df["tick"]
                < round_end_tick
            )
            & (
                position_df["is_alive"]
                == True
            )
        ]
        .sort_values("tick")
        .drop_duplicates(
            subset=["tick"]
        )
        .reset_index(drop=True)
    )

    if player_rows.empty:
        return []

    sampled_points = []

    last_sample_tick = None

    for _, row in player_rows.iterrows():
        tick = int(
            row["tick"]
        )

        if (
            last_sample_tick is not None
            and tick - last_sample_tick
            < step_ticks
        ):
            continue

        sampled_points.append(
            make_point(row)
        )

        last_sample_tick = tick

    if len(sampled_points) < 2:
        return []

    result = []

    active_points = None

    last_moving_tick = None
    last_moving_index = None

    for index in range(
        1,
        len(sampled_points),
    ):
        previous = (
            sampled_points[index - 1]
        )

        current = (
            sampled_points[index]
        )

        move_distance = distance_3d(
            previous["position"],
            current["position"],
        )

        is_moving = (
            move_distance
            >= START_MOVE_DISTANCE
        )

        if active_points is None:
            if not is_moving:
                continue

            active_points = [
                previous,
                current,
            ]

            last_moving_tick = (
                current["tick"]
            )

            last_moving_index = 1

            continue

        active_points.append(
            current
        )

        if is_moving:
            last_moving_tick = (
                current["tick"]
            )

            last_moving_index = (
                len(active_points) - 1
            )

            continue

        stopped_ticks = (
            current["tick"]
            - last_moving_tick
        )

        if (
            stopped_ticks
            < STOP_AFTER_TICKS
        ):
            continue

        # Отбрасываем длинную стоянку
        # в конце эпизода.
        episode_points = (
            active_points[
                :last_moving_index + 1
            ]
        )

        episode = finish_episode(
            player_name=
                player_name,

            round_number=
                round_number,

            points=
                episode_points,
        )

        if episode is not None:
            result.append(
                episode
            )

        active_points = None

        last_moving_tick = None
        last_moving_index = None

    if (
        active_points is not None
        and last_moving_index
        is not None
    ):
        episode_points = (
            active_points[
                :last_moving_index + 1
            ]
        )

        episode = finish_episode(
            player_name=
                player_name,

            round_number=
                round_number,

            points=
                episode_points,
        )

        if episode is not None:
            result.append(
                episode
            )

    return result