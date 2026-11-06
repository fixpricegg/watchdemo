def detect_potentially_bad_entries(
    candidate_contexts,
):
    """
    Первый detector v1.

    Он НЕ утверждает, что игрок ошибся.

    Он только выбирает candidate moments,
    где одновременно есть несколько
    подозрительных признаков.
    """

    findings = []

    for item in candidate_contexts:
        candidate = item.get(
            "candidate",
            {}
        )

        current = item.get(
            "current"
        )

        facing = item.get(
            "facing"
        )

        support = item.get(
            "teammate_support"
        )

        outcome = item.get(
            "outcome",
            {}
        )

        if current is None:
            continue

        reasons = []

        # =========================
        # 1. Facing
        # =========================

        facing_error = None

        if facing is not None:
            facing_error = facing.get(
                "angle_error_degrees"
            )

        if (
            facing_error is not None
            and facing_error >= 90
        ):
            reasons.append({
                "type":
                    "facing_away",

                "value":
                    facing_error,
            })

        # =========================
        # 2. Teammate support
        # =========================

        nearest_teammate = None

        if support is not None:
            nearest_teammate = support.get(
                "nearest_teammate"
            )

        if nearest_teammate is None:
            reasons.append({
                "type":
                    "no_nearby_teammate_data",
            })

        else:
            nav_distance = (
                nearest_teammate.get(
                    "nav_distance"
                )
            )

            if (
                nav_distance is not None
                and nav_distance >= 1000
            ):
                reasons.append({
                    "type":
                        "teammate_far",

                    "value":
                        nav_distance,

                    "teammate":
                        nearest_teammate.get(
                            "name"
                        ),
                })

        # =========================
        # 3. Weapon state
        # =========================

        weapon = str(
            current.get(
                "weapon"
            )
            or ""
        ).lower()

        knife_like = (
            "knife" in weapon
            or "bayonet" in weapon
        )

        if knife_like:
            reasons.append({
                "type":
                    "knife_out",

                "weapon":
                    current.get(
                        "weapon"
                    ),
            })

        # =========================
        # 4. Short-term outcome
        # =========================

        damage = outcome.get(
            "first_damage"
        )

        death = outcome.get(
            "death"
        )

        enemy_respot = outcome.get(
            "enemy_respot"
        )

        if damage is not None:
            reasons.append({
                "type":
                    "damage_after_entry",

                "after_seconds":
                    damage.get(
                        "after_seconds"
                    ),
            })

        if enemy_respot is not None:
            reasons.append({
                "type":
                    "enemy_respot_after_entry",

                "after_seconds":
                    enemy_respot.get(
                        "after_seconds"
                    ),
            })

        if death is not None:
            reasons.append({
                "type":
                    "death_after_entry",

                "after_seconds":
                    death.get(
                        "after_seconds"
                    ),

                "killer":
                    death.get(
                        "killer_name"
                    ),
            })

        if outcome.get(
            "killer_is_candidate_enemy"
        ):
            reasons.append({
                "type":
                    "killed_by_candidate_enemy",
            })

        # =========================
        # 5. Detector decision
        # =========================
        #
        # Пока не используем score.
        # Просто требуем минимум два
        # независимых подозрительных признака.
        #

        if len(reasons) < 2:
            continue

        findings.append({
            "type":
                "potentially_bad_entry",

            "round":
                candidate.get(
                    "round"
                ),

            "tick":
                candidate.get(
                    "tick"
                ),

            "player":
                candidate.get(
                    "player"
                ),

            "enemy":
                candidate.get(
                    "enemy_name"
                ),

            "enemy_info_age_seconds":
                candidate.get(
                    "enemy_info_age_seconds"
                ),

            "player_area_id":
                candidate.get(
                    "player_area_id"
                ),

            "previous_player_area_id":
                candidate.get(
                    "previous_player_area_id"
                ),

            "possible_area_count":
                candidate.get(
                    "possible_area_count"
                ),

            "reason_count":
                len(reasons),

            "reasons":
                reasons,

            "context":
                item,
        })

    return findings