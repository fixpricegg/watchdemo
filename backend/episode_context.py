import pandas as pd

import information
import threats


OUTCOME_WINDOW_TICKS = 192


def get_player_team_at_tick(
    position_df,
    player_name,
    tick,
):
    rows = position_df[
        (position_df["name"] == player_name)
        & (position_df["tick"] <= tick)
        & (position_df["team_num"].notna())
    ].sort_values("tick")

    if rows.empty:
        return None

    return int(
        rows.iloc[-1]["team_num"]
    )


def compact_threat(threat):
    return {
        "enemy_name":
            threat.get("enemy_name"),

        "enemy_steamid":
            threat.get("enemy_steamid"),

        "status":
            threat.get("status"),

        "age_seconds":
            threat.get("age_seconds"),

        "freshness":
            threat.get("freshness"),

        "possible_area_count":
            threat.get(
                "possible_area_count"
            ),

        "last_seen_position":
            threat.get(
                "last_seen_position"
            ),

        "possible_area_ids":
            threat.get(
                "possible_area_ids",
                [],
            ),
    }

def get_teammate_support_at_tick(
    geometry,
    position_df,
    player_name,
    observer_team,
    tick,
    player_area_id,
):
    teammates = []

    if player_area_id is None:
        return teammates

    player_area = geometry.areas.get(int(player_area_id))
    if player_area is None:
        return teammates

    # Build one current snapshot first, then filter by team.
    # If we filter by team before taking the latest row, an old row from
    # earlier in the match can survive and make an enemy look like a teammate.
    snapshot_rows = position_df[
        (position_df["tick"] <= tick)
        & (position_df["steamid"].notna())
    ].sort_values("tick")

    if snapshot_rows.empty:
        return teammates

    latest_rows = (
        snapshot_rows
        .groupby("steamid", as_index=False)
        .tail(1)
    )

    team_rows = latest_rows[
        (latest_rows["team_num"] == observer_team)
        & (latest_rows["name"] != player_name)
    ].copy()

    if "is_alive" in team_rows.columns:
        team_rows = team_rows[team_rows["is_alive"] == True]

    for _, row in team_rows.iterrows():
        teammate_position = {
            "x": float(row["X"]),
            "y": float(row["Y"]),
            "z": float(row["Z"]),
        }

        teammate_area = geometry.find_area(
            teammate_position["x"],
            teammate_position["y"],
            teammate_position["z"],
        )

        if teammate_area is None:
            continue

        teammate_area_id = int(teammate_area["id"])

        nav_path = geometry.shortest_path(
            int(player_area_id),
            teammate_area_id,
        )

        nav_distance = None

        if nav_path is not None:
            nav_distance = 0.0

            for index in range(1, len(nav_path)):
                nav_distance += geometry.area_distance(
                    geometry.areas[nav_path[index - 1]],
                    geometry.areas[nav_path[index]],
                )

            nav_distance = round(nav_distance, 1)

        teammates.append({
            "name": row["name"],
            "steamid": information.normalize_steamid(
                row.get("steamid")
            ),
            "position": teammate_position,
            "area_id": teammate_area_id,
            "nav_distance": nav_distance,
            "state_tick": int(row["tick"]),
        })

    teammates.sort(
        key=lambda teammate: (
            teammate["nav_distance"]
            if teammate["nav_distance"] is not None
            else float("inf")
        )
    )

    return teammates

def build_episode_contexts(
    geometry,
    position_df,
    team_observations,
    team_spot_windows,
    deaths_df,
    movement_episodes,
):
    contexts = []

    for episode in movement_episodes:
        player_name = episode["player"]
        round_number = episode["round"]

        start_tick = episode[
            "start_tick"
        ]

        end_tick = episode[
            "end_tick"
        ]

        observer_team = (
            get_player_team_at_tick(
                position_df,
                player_name,
                start_tick,
            )
        )

        if observer_team is None:
            continue

        start_visual_state = (
            information
            .get_team_visual_state_at_tick(
                team_observations,
                team_spot_windows,
                round_number=
                    round_number,

                observer_team=
                    observer_team,

                tick=
                    start_tick,

                deaths_df=
                    deaths_df,
            )
        )

        end_visual_state = (
            information
            .get_team_visual_state_at_tick(
                team_observations,
                team_spot_windows,
                round_number=
                    round_number,

                observer_team=
                    observer_team,

                tick=
                    end_tick,

                deaths_df=
                    deaths_df,
            )
        )

        start_threat_state = (
            threats.build_movement_threats(
                geometry,
                episode[
                    "start_position"
                ],
                start_visual_state,
            )
        )

        end_threat_state = (
            threats.build_movement_threats(
                geometry,
                episode[
                    "end_position"
                ],
                end_visual_state,
            )
        )

        start_player_area = (
            start_threat_state.get(
                "player_area_id"
            )
        )

        end_player_area = (
            end_threat_state.get(
                "player_area_id"
            )
        )

        start_threats = [
            compact_threat(threat)
            for threat
            in start_threat_state.get(
                "threats",
                [],
            )
        ]

        end_threats = [
            compact_threat(threat)
            for threat
            in end_threat_state.get(
                "threats",
                [],
            )
        ]

        start_overlaps = []

        for threat in start_threats:
            possible_areas = set(
                threat.get(
                    "possible_area_ids",
                    [],
                )
            )

            if (
                start_player_area
                in possible_areas
            ):
                start_overlaps.append(
                    threat
                )

        end_overlaps = []

        for threat in end_threats:
            possible_areas = set(
                threat.get(
                    "possible_area_ids",
                    [],
                )
            )

            if (
                end_player_area
                in possible_areas
            ):
                end_overlaps.append(
                    threat
                )

        team_contacts_during = []

        for window in team_spot_windows:
            if (
                    window["round"]
                    != round_number
            ):
                continue

            if (
                    window["observer_team"]
                    != observer_team
            ):
                continue

            contact_start = max(
                start_tick,
                window["start_tick"],
            )

            contact_end = min(
                end_tick,
                window["end_tick"],
            )

            if contact_start >= contact_end:
                continue

            team_contacts_during.append({
                "enemy_name":
                    window.get(
                        "target_name"
                    ),

                "enemy_steamid":
                    window.get(
                        "target_steamid"
                    ),

                "contact_start_tick":
                    int(contact_start),

                "contact_end_tick":
                    int(contact_end),

                "contact_duration_seconds":
                    round(
                        (
                                contact_end
                                - contact_start
                        ) / 64,
                        2,
                    ),

                "started_before_episode":
                    (
                            window["start_tick"]
                            < start_tick
                    ),
            })

        player_deaths = deaths_df[
            (deaths_df["round"] == round_number)
            & (
                deaths_df["tick"]
                >= start_tick
            )
            & (
                deaths_df["tick"]
                <= (
                    end_tick
                    + OUTCOME_WINDOW_TICKS
                )
            )
            & (
                deaths_df["user_name"]
                == player_name
            )
        ].sort_values("tick")

        death = None

        if not player_deaths.empty:
            row = player_deaths.iloc[0]

            death = {
                "tick":
                    int(row["tick"]),

                "killer":
                    row.get(
                        "attacker_name"
                    ),

                "weapon":
                    row.get(
                        "weapon"
                    ),
            }

        path_areas = []

        sampled_areas = []

        for point in episode["path"]:
            area = geometry.find_area(
                point["position"]["x"],
                point["position"]["y"],
                point["position"]["z"],
            )

            if area is None:
                continue

            area_id = int(
                area["id"]
            )

            if (
                    sampled_areas
                    and sampled_areas[-1][
                "area_id"
            ] == area_id
            ):
                continue

            sampled_areas.append({
                "tick":
                    int(point["tick"]),

                "area_id":
                    area_id,

                "position":
                    point["position"],
            })

        for index, current_point in enumerate(
                sampled_areas
        ):
            if index == 0:
                path_areas.append(
                    current_point
                )
                continue

            previous_point = (
                sampled_areas[index - 1]
            )

            previous_area_id = (
                previous_point["area_id"]
            )

            current_area_id = (
                current_point["area_id"]
            )

            nav_path = geometry.shortest_path(
                previous_area_id,
                current_area_id,
            )

            if (
                    nav_path is None
                    or len(nav_path) < 2
            ):
                if (
                        not path_areas
                        or path_areas[-1][
                    "area_id"
                ] != current_area_id
                ):
                    path_areas.append(
                        current_point
                    )

                continue

            segment_areas = [
                geometry.areas[area_id]
                for area_id
                in nav_path
            ]

            cumulative_distances = [0.0]

            total_distance = 0.0

            for path_index in range(
                    1,
                    len(segment_areas),
            ):
                total_distance += (
                    geometry.area_distance(
                        segment_areas[
                            path_index - 1
                            ],
                        segment_areas[
                            path_index
                        ],
                    )
                )

                cumulative_distances.append(
                    total_distance
                )

            tick_start = (
                previous_point["tick"]
            )

            tick_end = (
                current_point["tick"]
            )

            for path_index in range(
                    1,
                    len(nav_path),
            ):
                area_id = int(
                    nav_path[path_index]
                )

                if total_distance > 0:
                    progress = (
                            cumulative_distances[
                                path_index
                            ]
                            / total_distance
                    )
                else:
                    progress = 1.0

                estimated_tick = int(
                    round(
                        tick_start
                        + (
                                tick_end
                                - tick_start
                        )
                        * progress
                    )
                )

                area = geometry.areas[
                    area_id
                ]

                if (
                        path_areas
                        and path_areas[-1][
                    "area_id"
                ] == area_id
                ):
                    continue

                if area_id == current_area_id:
                    position = (
                        current_point[
                            "position"
                        ]
                    )
                    estimated_tick = (
                        current_point[
                            "tick"
                        ]
                    )
                else:
                    position = {
                        "x":
                            area["center"]["x"],

                        "y":
                            area["center"]["y"],

                        "z":
                            area["center"]["z"],
                    }

                path_areas.append({
                    "tick":
                        estimated_tick,

                    "area_id":
                        area_id,

                    "position":
                        position,
                })

        route_trace = []

        for path_point in path_areas:
            point_tick = path_point["tick"]
            point_position = path_point["position"]

            visual_state = (
                information
                .get_team_visual_state_at_tick(
                    team_observations,
                    team_spot_windows,
                    round_number=
                    round_number,

                    observer_team=
                    observer_team,

                    tick=
                    point_tick,

                    deaths_df=
                    deaths_df,
                )
            )

            threat_state = (
                threats.build_movement_threats(
                    geometry,
                    point_position,
                    visual_state,
                )
            )

            player_area_id = (
                threat_state.get(
                    "player_area_id"
                )
            )

            overlapping_threats = []

            for threat in threat_state.get(
                    "threats",
                    [],
            ):
                possible_areas = set(
                    threat.get(
                        "possible_area_ids",
                        [],
                    )
                )

                if player_area_id in possible_areas:
                    overlapping_threats.append({
                        "enemy_name":
                            threat.get(
                                "enemy_name"
                            ),

                        "enemy_steamid":
                            threat.get(
                                "enemy_steamid"
                            ),

                        "status":
                            threat.get(
                                "status"
                            ),

                        "age_seconds":
                            threat.get(
                                "age_seconds"
                            ),

                        "freshness":
                            threat.get(
                                "freshness"
                            ),

                        "possible_area_ids":
                            threat.get(
                                "possible_area_ids",
                                [],
                            ),
                    })

            route_trace.append({
                "tick":
                    int(point_tick),

                "area_id":
                    int(
                        path_point[
                            "area_id"
                        ]
                    ),

                "position":
                    point_position,

                "threat_count":
                    len(
                        overlapping_threats
                    ),

                "threats":
                    overlapping_threats,

                "all_threats": [
                    {
                        "enemy_name":
                            threat.get(
                                "enemy_name"
                            ),

                        "enemy_steamid":
                            threat.get(
                                "enemy_steamid"
                            ),

                        "status":
                            threat.get(
                                "status"
                            ),

                        "age_seconds":
                            threat.get(
                                "age_seconds"
                            ),

                        "freshness":
                            threat.get(
                                "freshness"
                            ),

                        "possible_area_ids":
                            threat.get(
                                "possible_area_ids",
                                [],
                            ),
                    }
                    for threat
                    in threat_state.get(
                        "threats",
                        [],
                    )
                ],
            })

        risk_entries = []

        if route_trace:
            first_point = route_trace[0]

            if first_point["threat_count"] > 0:
                risk_entries.append({
                    "type":
                        "started_inside_risk",

                    "tick":
                        first_point["tick"],

                    "area_id":
                        first_point["area_id"],

                    "threats":
                        first_point["threats"],
                })

            for index in range(
                    1,
                    len(route_trace),
            ):
                previous = route_trace[
                    index - 1
                    ]

                current = route_trace[
                    index
                ]

                was_safe = (
                        previous[
                            "threat_count"
                        ]
                        == 0
                )

                became_risky = (
                        current[
                            "threat_count"
                        ]
                        > 0
                )

                if not (
                        was_safe
                        and became_risky
                ):
                    continue

                entry_threats = []

                for threat in current[
                    "threats"
                ]:
                    enemy_id = threat.get(
                        "enemy_steamid"
                    )

                    previous_enemy = None

                    for previous_threat in previous[
                        "all_threats"
                    ]:
                        if (
                                previous_threat.get(
                                    "enemy_steamid"
                                )
                                == enemy_id
                        ):
                            previous_enemy = (
                                previous_threat
                            )
                            break

                    previous_region = set()

                    if previous_enemy is not None:
                        previous_region = set(
                            previous_enemy.get(
                                "possible_area_ids",
                                [],
                            )
                        )

                    current_area_was_already_risky = (
                            current[
                                "area_id"
                            ]
                            in previous_region
                    )

                    entry_threats.append({
                        **threat,

                        "current_area_was_already_risky":
                            current_area_was_already_risky,
                    })

                player_entered_existing_risk = any(
                    threat[
                        "current_area_was_already_risky"
                    ]
                    for threat
                    in entry_threats
                )

                entry_type = (
                    "player_entered_existing_risk"
                    if player_entered_existing_risk
                    else "risk_expanded_or_appeared"
                )


                teammate_support = (
                    get_teammate_support_at_tick(
                        geometry,
                        position_df,
                        player_name,
                        observer_team,
                        current["tick"],
                        current["area_id"],
                    )
                )

                # Which teammate supplied information about the concrete
                # enemy/enemies responsible for this risk entry?
                previous_visual_state = (
                    information
                    .get_team_visual_state_at_tick(
                        team_observations,
                        team_spot_windows,
                        round_number=round_number,
                        observer_team=observer_team,
                        tick=previous["tick"],
                        deaths_df=deaths_df,
                    )
                )

                information_sources = {}

                for enemy in previous_visual_state:
                    enemy_id = information.normalize_steamid(
                        enemy.get("target_steamid")
                    )

                    if enemy_id is None:
                        continue

                    information_sources[enemy_id] = {
                        information.normalize_steamid(source_id)
                        for source_id in enemy.get("last_seen_by", [])
                        if information.normalize_steamid(source_id)
                        is not None
                    }

                for teammate in teammate_support:
                    teammate_id = teammate.get("steamid")
                    supported_threats = []

                    for threat in entry_threats:
                        enemy_id = information.normalize_steamid(
                            threat.get("enemy_steamid")
                        )

                        if (
                            enemy_id is not None
                            and teammate_id
                            in information_sources.get(
                                enemy_id,
                                set(),
                            )
                        ):
                            supported_threats.append(
                                threat.get("enemy_name")
                            )

                    teammate[
                        "information_on_entry_threats"
                    ] = supported_threats

                risk_entries.append({
                    "type":
                        entry_type,

                    "tick":
                        current["tick"],

                    "from_area_id":
                        previous[
                            "area_id"
                        ],

                    "area_id":
                        current[
                            "area_id"
                        ],

                    "position":
                        current[
                            "position"
                        ],

                    "threats":
                        entry_threats,

                    "teammate_support":
                        teammate_support,
                })


        contexts.append({
            "episode":
                episode,

            "observer_team":
                observer_team,

            "start_player_area_id":
                start_player_area,

            "end_player_area_id":
                end_player_area,

            "start_known_enemies":
                start_threats,

            "end_known_enemies":
                end_threats,

            "start_region_overlaps":
                start_overlaps,

            "end_region_overlaps":
                end_overlaps,

            "team_contacts_during":
                team_contacts_during,

            "death_after_or_during":
                death,

            "path_areas":
                path_areas,

            "route_trace":
                route_trace,

            "risk_entries":
                risk_entries,
        })

    return contexts
