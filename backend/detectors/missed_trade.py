
import math

import information
import pandas as pd

from library.trade_geometry import assess_trade_geometry


TICKRATE = 64
TRADE_WINDOW_TICKS = 4 * TICKRATE


def distance_2d(first, second):
    if first is None or second is None:
        return None

    try:
        values = [
            float(first[axis])
            for axis in ("x", "y")
        ] + [
            float(second[axis])
            for axis in ("x", "y")
        ]
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

    if not all(math.isfinite(value) for value in values):
        return None

    return math.hypot(
        values[0] - values[2],
        values[1] - values[3],
    )


def get_possible_missed_trades(
    player_name,
    deaths_df,
    match_library,
    *,
    trade_window_ticks=TRADE_WINDOW_TICKS,
    max_teammate_distance=700,
    max_killer_distance=800,
):
    if trade_window_ticks <= 0:
        raise ValueError("trade_window_ticks must be positive")

    # Without complete death data, we cannot determine
    # whether the killer was traded during the window.
    if not match_library.death_data_complete:
        return []

    required_columns = {
        "round",
        "tick",
        "user_steamid",
        "attacker_steamid",
    }

    if not required_columns.issubset(deaths_df.columns):
        return []

    candidates = []

    deaths = deaths_df.sort_values("tick")

    for _, death in deaths.iterrows():
        victim_id = information.normalize_steamid(
            death["user_steamid"]
        )
        killer_id = information.normalize_steamid(
            death["attacker_steamid"]
        )

        if (
            victim_id is None
            or killer_id is None
            or victim_id == killer_id
        ):
            continue

        try:
            death_tick = int(death["tick"])
            death_round = int(death["round"])
        except (TypeError, ValueError, OverflowError):
            continue

        try:
            state = match_library.get_game_state(
                death_tick, player_name
            )
        except ValueError:
            continue

        round_info = state["round"]

        if death_round != int(round_info["number"]):
            continue

        round_start = int(round_info["live_start_tick"])
        round_end = int(round_info["end_tick"])

        if not round_start <= death_tick < round_end:
            continue

        # Require a complete observation window.
        if death_tick + trade_window_ticks >= round_end:
            continue

        snapshots = {
            str(player["steamid"]): player
            for player in state["ground_truth"]["players"]
            if player.get("steamid") is not None
        }

        player_id = str(state["perspective"]["steamid"])

        if victim_id == player_id or killer_id == player_id:
            continue

        actor = snapshots.get(player_id)
        victim = snapshots.get(victim_id)
        killer = snapshots.get(killer_id)

        if actor is None or victim is None or killer is None:
            continue

        # MatchLibrary filters snapshots by freshness.
        # Check again so the detector's contract is explicit.
        valid_samples = True

        for snapshot in (actor, victim, killer):
            sample_tick = snapshot.get("sample_tick")

            if sample_tick is None:
                valid_samples = False
                break

            age = death_tick - int(sample_tick)

            if not 0 <= age <= match_library.max_state_age_ticks:
                valid_samples = False
                break

        if not valid_samples:
            continue

        actor_team = actor.get("team")
        victim_team = victim.get("team")
        killer_team = killer.get("team")

        if (
            actor_team not in (2, 3)
            or victim_team != actor_team
            or killer_team not in (2, 3)
            or killer_team == actor_team
        ):
            continue

        if actor.get("status", {}).get("is_alive") is not True:
            continue

        player_position = actor.get("position")
        victim_position = victim.get("position")
        killer_position = killer.get("position")

        teammate_distance = distance_2d(
            player_position, victim_position
        )
        killer_distance = distance_2d(
            player_position, killer_position
        )

        if teammate_distance is None or killer_distance is None:
            continue

        # Broad candidate-selection thresholds,
        # not a proof of trade feasibility.
        if (
            teammate_distance > max_teammate_distance
            or killer_distance > max_killer_distance
        ):
            continue

        # Post-match outcome check:
        # exclude cases where the killer was killed
        # within the trade window, by anyone.
        killer_deaths = deaths[
            (deaths["round"] == death_round)
            & (deaths["tick"] > death_tick)
            & (deaths["tick"] <= death_tick + trade_window_ticks)
        ]

        killer_was_traded = any(
            information.normalize_steamid(row["user_steamid"])
            == killer_id
            for _, row in killer_deaths.iterrows()
        )

        if killer_was_traded:
            continue

        navigation = assess_trade_geometry(
            match_library.geometry,
            player_position,
            killer_position,
        )

        # Until navigation evidence is present, do not
        # emit a user-facing review candidate.
        if navigation["status"] != "nav_connected":
            continue

        candidates.append({
            "type": "trade_review_candidate",
            "status": "review_required",
            "evaluation_status": "not_evaluated",
            "round": death_round,
            "tick": death_tick,
            "player_steamid": player_id,
            "victim_steamid": victim_id,
            "killer_steamid": killer_id,
            "dead_teammate": death.get("user_name"),
            "killer": death.get("attacker_name"),
            "teammate_distance_2d": round(teammate_distance, 2),
            "killer_distance_2d": round(killer_distance, 2),
            "trade_window_ticks": trade_window_ticks,
            "geometry": navigation,
            "evidence_scope": "post_match_ground_truth",
            "limitations": [
                "Line of sight has not been verified.",
                "Navigational connectivity does not prove a possible shot.",
                "Enemy location was not necessarily known to the player.",
                "The killer's future survival is outcome data, not decision input.",
                "Trade feasibility has not been established.",
            ],
        })

    return candidates
