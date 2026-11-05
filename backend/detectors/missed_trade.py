
import math

import information
from detectors.entry_death import round_observation_end
import pandas as pd

from library.trade_geometry import (
    assess_trade_geometry,
    assess_trade_static_collision,
)
from library.trade_contact import assess_trade_contact
from library.smoke_visibility import assess_smoke_visibility



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
        round_end = round_observation_end(match_library, death_round, int(round_info["end_tick"]))

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
            & (deaths["tick"] >= death_tick)
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

        static_collision = assess_trade_static_collision(
            match_library,
            player_position,
            killer_position,
        )

        temporal_context = {
            "status": "unavailable",
            "reason": "temporal_context_not_supported",
            "samples": [],
            "sample_count": 0,
            "continuous_state_verified": False,
        }

        get_timeline = getattr(
            match_library,
            "get_player_constraints_timeline",
            None,
        )

        if callable(get_timeline):
            temporal_context = get_timeline(
                death_tick,
                death_tick + trade_window_ticks,
                player_id,
            )


        contact = assess_trade_contact(
            match_library.team_observations,
            round_number=death_round,
            observer_team=actor_team,
            player_steamid=player_id,
            killer_steamid=killer_id,
            start_tick=death_tick,
            end_tick=death_tick + trade_window_ticks,
        )

        candidate = {
            "type": "trade_review_candidate",
            "detector_version": 2,
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
            "static_collision": static_collision,
            "temporal_context": temporal_context,
            "confidence": None,
            "severity": None,
            "evidence_scope": "post_match_ground_truth",
            "limitations": [
                "Line of sight has not been verified.",
                "Navigational connectivity does not prove a possible shot.",
                "Enemy location was not necessarily known to the player.",
                "The killer's future survival is outcome data, not decision input.",
                "Trade feasibility has not been established.",
                "Static trace uses sampled player origins, not eye positions.",
                "Static collision tracing is experimental and is not verified LOS.",
                "Temporal samples do not prove continuous action feasibility.",
                "Post-death observations are evaluation evidence, not prior knowledge.",
            ],
            "contact": contact,
            "display_eligibility": "review_only",
        }

        candidate["decision_evidence"] = collect_trade_decision_evidence(
            match_library,
            player_name,
            victim_id,
            killer_id,
            death_tick,
            trade_window_ticks,
            round_end,
            actor_position=player_position,
            killer_position=killer_position,
        )

        candidates.append(candidate)


    return candidates


def collect_trade_decision_evidence(
    library,
    player_name,
    victim_id,
    killer_id,
    death_tick,
    trade_window_ticks,
    round_end,
    actor_position=None,
    killer_position=None,
):
    result = {
        "status": "insufficient_evidence",
        "verdict": "not_evaluated",
        "support_opportunity": "not_established",
        "predeath": None,
        "constraints": None,
        "postdeath": {
            "status": "unavailable",
            "weapon_event_ticks": [],
            "damage_killer_ticks": [],
            "weapon_event_observed": None,
            "damaged_killer": None,
        },
        "smoke_visibility": {
            "status": "unknown",
        },
    }

    get_predeath = getattr(
        library, "get_predeath_support_context", None
    )

    if callable(get_predeath):
        pre = get_predeath(
            death_tick, player_name, victim_id, killer_id
        )

        timing = pre.get("support_timing") or {}
        geometry = pre.get("support_geometry") or {}

        result["predeath"] = {
            "status": pre.get("status"),
            "reference_tick": timing.get("reference_tick"),
            "reference_source": timing.get("reference_source"),
            "actor_life": timing.get("actor_life_at_reference"),
            "activity": (timing.get("activity") or {}).get("status"),
            "movement": timing.get("movement"),
            "geometry_status": geometry.get("status"),
            "geometry_tick": geometry.get("tick"),
        }

    get_constraints = getattr(
        library, "get_player_constraints", None
    )

    if callable(get_constraints):
        constraints = get_constraints(
            death_tick, player_name
        )

        result["constraints"] = {
            "status": constraints.get("status"),
            "limitations": constraints.get("limitations", []),
            "unknown_fields": constraints.get("unknown_fields", []),
            "evidence": constraints.get("evidence", {}),
        }

    get_combat = getattr(library, "get_combat_window", None)

    if callable(get_combat):
        end = min(
            death_tick + trade_window_ticks,
            round_end - 1,
        )

        if end >= death_tick:
            window = get_combat(death_tick, end)
            sources = window.get("parse_status") or {}

            weapon_ticks = []
            damage_ticks = []
            player_id = information.normalize_steamid(
                library.get_game_state(
                    death_tick, player_name
                )["perspective"]["steamid"]
            )
            for event in window.get("events", []):
                tick = int(event["tick"])

                if not death_tick <= tick <= end:
                    continue

                data = event.get("data") or {}
                actor_id = information.normalize_steamid(
                    data.get("actor_steamid")
                )
                target_id = information.normalize_steamid(
                    data.get("victim_steamid")
                )

                if actor_id != player_id:
                    continue

                if event["type"] == "weapon_fire":
                    weapon_ticks.append(tick)

                elif (
                    event["type"] == "player_hurt"
                    and target_id == killer_id
                ):
                    damage_ticks.append(tick)

            post = result["postdeath"]
            post["status"] = window.get("status", "unknown")
            post["weapon_event_ticks"] = sorted(set(weapon_ticks))
            post["damage_killer_ticks"] = sorted(set(damage_ticks))

            post["weapon_event_observed"] = (
                True if weapon_ticks
                else False if sources.get("weapon_fire") == "parsed"
                else None
            )

            post["damaged_killer"] = (
                True if damage_ticks
                else False if sources.get("player_hurt") == "parsed"
                else None
            )

    get_utility = getattr(
        library, "get_active_utility_effects", None
    )

    if callable(get_utility):
        try:
            utility = get_utility(
                death_tick, player_name
            )
        except (ValueError, RuntimeError):
            utility = None

        result["smoke_visibility"] = assess_smoke_visibility(
            actor_position,
            killer_position,
            utility,
        )

    pre = result["predeath"] or {}
    constraints = result["constraints"] or {}
    post = result["postdeath"]

    if pre.get("actor_life") == "dead":
        result["status"] = "not_applicable_actor_dead"

    elif (
        (pre.get("activity") == "damage_on_killer_observed")
        or post["damaged_killer"] is True
    ):
        result["status"] = "target_damage_observed"

    elif constraints.get("limitations"):
        result["status"] = "player_limitations_observed"

    elif (
        pre.get("actor_life") == "alive"
        and post["status"] == "sources_parsed"
    ):
        result["status"] = "review_required"

    if (
        result["smoke_visibility"]["status"]
        == "possible_smoke_occlusion"
        and result["status"] not in (
            "not_applicable_actor_dead",
            "target_damage_observed",
        )
    ):
        result["status"] = "visibility_unverified_smoke"

    return result

