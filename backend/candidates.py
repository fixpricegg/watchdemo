import information
import threats


DEFAULT_STEP_TICKS = 16


def detect_player_enters_enemy_region(
    geometry,
    position_df,
    team_observations,
    team_spot_windows,
    player_name,
    round_number,
    round_start_tick,
    round_end_tick,
    deaths_df,
    step_ticks=DEFAULT_STEP_TICKS,
):
    """
    Ищет моменты, когда игрок сам входит
    в УЖЕ существовавшую possible region врага.

    Это НЕ ошибка.

    Это candidate moment:
    потенциально значимое решение игрока,
    которое потом нужно оценивать в контексте.
    """

    player_rows = (
        position_df[
            (position_df["name"] == player_name)
            & (position_df["tick"] >= round_start_tick)
            & (position_df["tick"] < round_end_tick)
            & (position_df["is_alive"] == True)
        ]
        .sort_values("tick")
        .drop_duplicates(subset=["tick"])
        .reset_index(drop=True)
    )

    if player_rows.empty:
        return []

    candidates = []

    # Состояние каждого врага
    # на предыдущем обработанном тике.
    previous_enemy_states = {}

    last_processed_tick = None

    for _, player_row in player_rows.iterrows():
        tick = int(player_row["tick"])

        if (
            last_processed_tick is not None
            and tick - last_processed_tick < step_ticks
        ):
            continue

        last_processed_tick = tick

        team_num = player_row.get("team_num")

        try:
            observer_team = int(team_num)
        except (TypeError, ValueError):
            continue

        player_position = {
            "x": float(player_row["X"]),
            "y": float(player_row["Y"]),
            "z": float(player_row["Z"]),
        }

        visual_state = (
            information.get_team_visual_state_at_tick(
                team_observations,
                team_spot_windows,
                round_number=round_number,
                observer_team=observer_team,
                tick=tick,
                deaths_df=deaths_df,
            )
        )

        movement_state = (
            threats.build_movement_threats(
                geometry,
                player_position,
                visual_state,
            )
        )

        current_player_area = movement_state.get(
            "player_area_id"
        )

        if current_player_area is None:
            continue

        current_player_area = int(
            current_player_area
        )

        current_enemy_ids = set()

        for enemy in movement_state["threats"]:

            enemy_id = enemy.get(
                "enemy_steamid"
            )

            if enemy_id is None:
                enemy_id = enemy.get(
                    "enemy_name"
                )

            if enemy_id is None:
                continue

            current_enemy_ids.add(
                enemy_id
            )

            current_region = set(
                enemy.get(
                    "possible_area_ids",
                    [],
                )
            )

            previous_state = (
                previous_enemy_states.get(
                    enemy_id
                )
            )

            if previous_state is not None:

                previous_player_area = int(
                    previous_state[
                        "player_area_id"
                    ]
                )

                previous_region = (
                    previous_state[
                        "possible_area_ids"
                    ]
                )

                player_changed_area = (
                    current_player_area
                    != previous_player_area
                )

                # На прошлом шаге игрок
                # находился вне possible region.
                was_outside_region = (
                    previous_player_area
                    not in previous_region
                )

                # Текущая area игрока уже была
                # possible для врага ДО движения игрока.
                entered_existing_region = (
                    current_player_area
                    in previous_region
                )

                # И новая информация не исключила
                # эту area прямо сейчас.
                still_possible_now = (
                    current_player_area
                    in current_region
                )

                # Пока отдельно не смешиваем
                # confirmed contact.
                enemy_is_last_known = (
                    enemy.get("status")
                    == "last_known"
                )

                if (
                    player_changed_area
                    and was_outside_region
                    and entered_existing_region
                    and still_possible_now
                    and enemy_is_last_known
                ):
                    candidates.append({
                        "type":
                            "player_entered_enemy_region",

                        "round":
                            int(round_number),

                        "tick":
                            tick,

                        "player":
                            player_name,

                        "previous_player_area_id":
                            previous_player_area,

                        "player_area_id":
                            current_player_area,

                        "enemy_name":
                            enemy.get(
                                "enemy_name"
                            ),

                        "enemy_steamid":
                            enemy.get(
                                "enemy_steamid"
                            ),

                        "enemy_status":
                            enemy.get(
                                "status"
                            ),

                        "enemy_info_age_seconds":
                            enemy.get(
                                "age_seconds"
                            ),

                        "freshness":
                            enemy.get(
                                "freshness"
                            ),

                        "possible_area_count":
                            enemy.get(
                                "possible_area_count"
                            ),
                        "round_start_tick":
                            int(round_start_tick),

                        "round_end_tick":
                            int(round_end_tick),

                        "observer_team":
                            int(observer_team),

                        "enemy_last_seen_position":
                            enemy.get(
                                "last_seen_position"
                            ),
                    })

            # Сохраняем состояние врага
            # для следующего обработанного тика.
            previous_enemy_states[
                enemy_id
            ] = {
                "player_area_id":
                    current_player_area,

                "possible_area_ids":
                    current_region,
            }

        # Если враг исчез из information state,
        # не тащим старое состояние дальше.
        missing_enemy_ids = (
            set(
                previous_enemy_states.keys()
            )
            - current_enemy_ids
        )

        for enemy_id in missing_enemy_ids:
            previous_enemy_states.pop(
                enemy_id,
                None,
            )

    return candidates