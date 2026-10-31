import math


TICKRATE = 64

DEFAULT_WINDOW_TICKS = TICKRATE
DEFAULT_OUTCOME_TICKS = 3 * TICKRATE




def _normalize_angle(angle):
    while angle > 180:
        angle -= 360

    while angle < -180:
        angle += 360

    return angle


def _build_facing_context(
    player_snapshot,
    enemy_last_seen_position,
):
    if player_snapshot is None:
        return None

    if enemy_last_seen_position is None:
        return None

    player_position = player_snapshot.get(
        "position"
    )

    player_yaw = player_snapshot.get(
        "yaw"
    )

    if (
        player_position is None
        or player_yaw is None
    ):
        return None

    dx = (
        float(
            enemy_last_seen_position["x"]
        )
        - float(
            player_position["x"]
        )
    )

    dy = (
        float(
            enemy_last_seen_position["y"]
        )
        - float(
            player_position["y"]
        )
    )

    distance_2d = math.sqrt(
        dx * dx
        + dy * dy
    )

    if distance_2d < 1e-6:
        return {
            "target_yaw": None,
            "player_yaw": player_yaw,
            "angle_error_degrees": None,
            "distance_2d": 0.0,
        }

    target_yaw = math.degrees(
        math.atan2(
            dy,
            dx,
        )
    )

    angle_difference = (
        _normalize_angle(
            target_yaw
            - player_yaw
        )
    )

    return {
        "target_yaw":
            round(
                target_yaw,
                2,
            ),

        "player_yaw":
            round(
                player_yaw,
                2,
            ),

        "angle_error_degrees":
            round(
                abs(angle_difference),
                2,
            ),

        "signed_angle_difference":
            round(
                angle_difference,
                2,
            ),

        "distance_2d":
            round(
                distance_2d,
                1,
            ),
    }


def _safe_float(value):
    try:
        result = float(value)

        if math.isnan(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def _get_closest_player_row(
    position_df,
    player_name,
    target_tick,
    round_start_tick,
    round_end_tick,
):
    rows = position_df[
        (position_df["name"] == player_name)
        & (
            position_df["tick"]
            >= round_start_tick
        )
        & (
            position_df["tick"]
            < round_end_tick
        )
    ].copy()

    if rows.empty:
        return None

    rows["tick_distance"] = (
        rows["tick"] - target_tick
    ).abs()

    return (
        rows
        .sort_values(
            ["tick_distance", "tick"]
        )
        .iloc[0]
    )


def _build_player_snapshot(
    geometry,
    position_df,
    player_name,
    target_tick,
    round_start_tick,
    round_end_tick,
):
    row = _get_closest_player_row(
        position_df,
        player_name,
        target_tick,
        round_start_tick,
        round_end_tick,
    )

    if row is None:
        return None

    x = float(row["X"])
    y = float(row["Y"])
    z = float(row["Z"])

    area = geometry.find_area(
        x,
        y,
        z,
    )

    if isinstance(area, dict):
        area_id = int(area["id"])

    elif area is not None:
        area_id = int(area)

    else:
        area_id = None

    return {
        "requested_tick":
            int(target_tick),

        "actual_tick":
            int(row["tick"]),

        "area_id":
            area_id,

        "position": {
            "x": x,
            "y": y,
            "z": z,
        },

        "yaw":
            _safe_float(
                row.get("yaw")
            ),

        "health":
            _safe_float(
                row.get("health")
            ),

        "armor":
            _safe_float(
                row.get("armor")
            ),

        "is_alive":
            bool(
                row["is_alive"]
            ),

        "weapon":
            row.get(
                "active_weapon_name"
            ),
    }


def _find_first_damage(
    position_df,
    player_name,
    candidate_tick,
    outcome_end_tick,
    starting_health,
):
    if starting_health is None:
        return None

    rows = (
        position_df[
            (position_df["name"] == player_name)
            & (
                position_df["tick"]
                >= candidate_tick
            )
            & (
                position_df["tick"]
                <= outcome_end_tick
            )
        ]
        .sort_values("tick")
        .drop_duplicates(
            subset=["tick"]
        )
    )

    if rows.empty:
        return None

    for _, row in rows.iterrows():
        health = _safe_float(
            row.get("health")
        )

        if health is None:
            continue

        if health < starting_health:
            damage_tick = int(
                row["tick"]
            )

            return {
                "tick":
                    damage_tick,

                "after_seconds":
                    round(
                        (
                            damage_tick
                            - candidate_tick
                        )
                        / TICKRATE,
                        2,
                    ),

                "health_before":
                    starting_health,

                "health_after":
                    health,

                "health_lost":
                    round(
                        starting_health
                        - health,
                        1,
                    ),
            }

    return None


def _find_player_death(
    deaths_df,
    player_name,
    round_number,
    candidate_tick,
    outcome_end_tick,
):
    if deaths_df is None:
        return None

    if deaths_df.empty:
        return None

    deaths = deaths_df[
        (deaths_df["user_name"] == player_name)
        & (
            deaths_df["round"]
            == round_number
        )
        & (
            deaths_df["tick"]
            >= candidate_tick
        )
        & (
            deaths_df["tick"]
            <= outcome_end_tick
        )
    ].sort_values("tick")

    if deaths.empty:
        return None

    death = deaths.iloc[0]

    death_tick = int(
        death["tick"]
    )

    return {
        "tick":
            death_tick,

        "after_seconds":
            round(
                (
                    death_tick
                    - candidate_tick
                )
                / TICKRATE,
                2,
            ),

        "killer_name":
            death.get(
                "attacker_name"
            ),

        "killer_steamid":
            (
                int(
                    death["attacker_steamid"]
                )
                if not math.isnan(
                    float(
                        death[
                            "attacker_steamid"
                        ]
                    )
                )
                else None
            ),

        "weapon":
            death.get(
                "weapon"
            ),
    }


def _find_enemy_respot(
    team_spot_windows,
    candidate,
    outcome_end_tick,
):
    enemy_name = candidate.get(
        "enemy_name"
    )

    round_number = int(
        candidate["round"]
    )

    candidate_tick = int(
        candidate["tick"]
    )

    possible_windows = []

    for window in team_spot_windows:

        if (
            window.get("target_name")
            != enemy_name
        ):
            continue

        if (
            int(window["round"])
            != round_number
        ):
            continue

        start_tick = int(
            window["start_tick"]
        )

        if start_tick <= candidate_tick:
            continue

        if start_tick > outcome_end_tick:
            continue

        possible_windows.append(
            window
        )

    if not possible_windows:
        return None

    possible_windows.sort(
        key=lambda window:
            int(
                window["start_tick"]
            )
    )

    first_window = (
        possible_windows[0]
    )

    respot_tick = int(
        first_window["start_tick"]
    )

    return {
        "tick":
            respot_tick,

        "after_seconds":
            round(
                (
                    respot_tick
                    - candidate_tick
                )
                / TICKRATE,
                2,
            ),
    }


def build_candidate_context(
    geometry,
    position_df,
    deaths_df,
    team_spot_windows,
    candidate,
    window_ticks=DEFAULT_WINDOW_TICKS,
    outcome_ticks=DEFAULT_OUTCOME_TICKS,
):
    candidate_tick = int(
        candidate["tick"]
    )

    player_name = candidate[
        "player"
    ]

    round_number = int(
        candidate["round"]
    )

    round_start_tick = int(
        candidate[
            "round_start_tick"
        ]
    )

    round_end_tick = int(
        candidate[
            "round_end_tick"
        ]
    )

    before_tick = max(
        round_start_tick,
        candidate_tick
        - window_ticks,
    )

    after_tick = min(
        round_end_tick - 1,
        candidate_tick
        + window_ticks,
    )

    outcome_end_tick = min(
        round_end_tick - 1,
        candidate_tick
        + outcome_ticks,
    )

    before = _build_player_snapshot(
        geometry,
        position_df,
        player_name,
        before_tick,
        round_start_tick,
        round_end_tick,
    )

    current = _build_player_snapshot(
        geometry,
        position_df,
        player_name,
        candidate_tick,
        round_start_tick,
        round_end_tick,
    )

    after = _build_player_snapshot(
        geometry,
        position_df,
        player_name,
        after_tick,
        round_start_tick,
        round_end_tick,
    )

    facing = _build_facing_context(
        current,
        candidate.get(
            "enemy_last_seen_position"
        ),
    )

    teammate_support = (
        _build_teammate_context(
            geometry=geometry,
            position_df=position_df,
            player_name=player_name,
            candidate_tick=candidate_tick,
            observer_team=int(
                candidate["observer_team"]
            ),
            player_snapshot=current,
        )
    )

    starting_health = None

    if current is not None:
        starting_health = current.get(
            "health"
        )

    first_damage = (
        _find_first_damage(
            position_df,
            player_name,
            candidate_tick,
            outcome_end_tick,
            starting_health,
        )
    )

    death = (
        _find_player_death(
            deaths_df,
            player_name,
            round_number,
            candidate_tick,
            outcome_end_tick,
        )
    )

    enemy_respot = (
        _find_enemy_respot(
            team_spot_windows,
            candidate,
            outcome_end_tick,
        )
    )

    killer_is_candidate_enemy = False

    if death is not None:
        killer_is_candidate_enemy = (
            death.get(
                "killer_name"
            )
            == candidate.get(
                "enemy_name"
            )
        )

    return {
        "candidate":
            candidate,

        "window_ticks":
            int(window_ticks),

        "outcome_ticks":
            int(outcome_ticks),

        "before":
            before,

        "current":
            current,

        "after":
            after,

        "facing":
            facing,

        "teammate_support":
            teammate_support,

        "outcome": {
            "first_damage":
                first_damage,

            "death":
                death,

            "enemy_respot":
                enemy_respot,

            "killer_is_candidate_enemy":
                killer_is_candidate_enemy,
        },
    }


def build_contexts(
    geometry,
    position_df,
    deaths_df,
    team_spot_windows,
    candidates,
    window_ticks=DEFAULT_WINDOW_TICKS,
    outcome_ticks=DEFAULT_OUTCOME_TICKS,
):
    result = []

    for candidate in candidates:

        item = build_candidate_context(
            geometry=geometry,
            position_df=position_df,
            deaths_df=deaths_df,
            team_spot_windows=team_spot_windows,
            candidate=candidate,
            window_ticks=window_ticks,
            outcome_ticks=outcome_ticks,
        )

        result.append(
            item
        )

    return result

def _build_teammate_context(
    geometry,
    position_df,
    player_name,
    candidate_tick,
    observer_team,
    player_snapshot,
):
    if player_snapshot is None:
        return None

    player_area_id = player_snapshot.get(
        "area_id"
    )

    if player_area_id is None:
        return None

    rows = position_df[
        (position_df["tick"] == candidate_tick)
        & (position_df["team_num"] == observer_team)
        & (position_df["is_alive"] == True)
        & (position_df["name"] != player_name)
    ].copy()

    if rows.empty:
        return {
            "alive_teammates": 0,
            "teammates": [],
            "nearest_teammate": None,
        }

    # Один раз считаем nav-distance
    # от area анализируемого игрока.
    nav_distances = geometry.reachable_areas(
        player_area_id,
        max_distance=3000,
    )

    teammates = []

    for _, row in rows.iterrows():
        x = float(row["X"])
        y = float(row["Y"])
        z = float(row["Z"])

        area = geometry.find_area(
            x,
            y,
            z,
        )

        if isinstance(area, dict):
            teammate_area_id = int(
                area["id"]
            )

        elif area is not None:
            teammate_area_id = int(area)

        else:
            teammate_area_id = None

        nav_distance = None

        if teammate_area_id is not None:
            nav_distance = nav_distances.get(
                teammate_area_id
            )

        dx = (
            x
            - player_snapshot[
                "position"
            ]["x"]
        )

        dy = (
            y
            - player_snapshot[
                "position"
            ]["y"]
        )

        dz = (
            z
            - player_snapshot[
                "position"
            ]["z"]
        )

        euclidean_distance = math.sqrt(
            dx * dx
            + dy * dy
            + dz * dz
        )

        teammates.append({
            "name":
                row["name"],

            "steamid":
                row.get("steamid"),

            "area_id":
                teammate_area_id,

            "position": {
                "x": x,
                "y": y,
                "z": z,
            },

            "nav_distance":
                (
                    round(
                        float(nav_distance),
                        1,
                    )
                    if nav_distance
                    is not None
                    else None
                ),

            "euclidean_distance":
                round(
                    euclidean_distance,
                    1,
                ),

            "weapon":
                row.get(
                    "active_weapon_name"
                ),

            "health":
                _safe_float(
                    row.get("health")
                ),
        })

    teammates.sort(
        key=lambda teammate: (
            teammate["nav_distance"]
            if teammate[
                "nav_distance"
            ] is not None
            else math.inf
        )
    )

    nearest_teammate = (
        teammates[0]
        if teammates
        else None
    )

    return {
        "alive_teammates":
            len(teammates),

        "teammates":
            teammates,

        "nearest_teammate":
            nearest_teammate,
    }