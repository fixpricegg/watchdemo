
import math
from bisect import bisect_right

import information

from .game_state import player_from_row
from .player_constraints import assess_player_constraints
from .trade_contact import assess_trade_contact


def _observed(ticks, source_status):
    if ticks:
        return True
    if source_status == "parsed":
        return False
    return None


def build_predeath_support(
    library,
    *,
    player_id,
    teammate_id,
    killer_id,
    observer_team,
    round_number,
    round_start_tick,
    death_tick,
    lookback_ticks=128,
    movement_preroll_ticks=32,
):
    if lookback_ticks <= 0:
        raise ValueError("lookback_ticks must be positive")
    if movement_preroll_ticks < 0:
        raise ValueError("movement_preroll_ticks must be nonnegative")
    player_id = information.normalize_steamid(player_id)
    teammate_id = information.normalize_steamid(teammate_id)
    killer_id = information.normalize_steamid(killer_id)

    start = max(int(round_start_tick), int(death_tick) - lookback_ticks)
    end = int(death_tick) - 1

    position_start = max(
        int(round_start_tick),
        start - movement_preroll_ticks,
    )

    result = {
        "schema_version": "predeath_support_v1",
        "status": "unavailable",
        "evaluation_status": "not_evaluated",
        "scope": "post_match_ground_truth",
        "round": int(round_number),
        "death_tick": int(death_tick),
        "window_start_tick": start,
        "window_end_tick": end,
        "player_steamid": player_id,
        "teammate_steamid": teammate_id,
        "killer_steamid": killer_id,
        "position_samples": [],
        "position_window_start_tick": position_start,
        "distance_change_2d": None,
        "combat": {
            "status": "unavailable",
            "parse_status": {},
            "player_weapon_fire_ticks": [],
            "teammate_weapon_fire_ticks": [],
            "player_hurt_killer_ticks": [],
            "teammate_hurt_killer_ticks": [],
            "killer_hurt_teammate_ticks": [],
            "player_damaged_killer": None,
            "teammate_damaged_killer": None,
            "killer_damaged_teammate": None,
            "player_weapon_event_observed": None,
        },
        "contact": None,
        "limitations": [
            "Position samples do not prove a possible peek.",
            "Weapon fire does not identify the intended target.",
            "A lack of shots does not prove missed support.",
            "Visibility and response time are not established.",
        ],
    }

    if end < start:
        return result

    # Combat evidence is restricted to ticks before death.
    get_combat = getattr(library, "get_combat_window", None)

    if callable(get_combat):
        combat_window = get_combat(start, end)
        events = combat_window["events"]
        sources = combat_window["parse_status"]

        def event_ticks(event_type, actor, victim=None):
            ticks = []

            for event in events:
                if event["type"] != event_type:
                    continue

                data = event.get("data") or {}
                actor_id = information.normalize_steamid(
                    data.get("actor_steamid")
                )
                victim_id = information.normalize_steamid(
                    data.get("victim_steamid")
                )

                if actor_id != actor:
                    continue

                if victim is not None and victim_id != victim:
                    continue

                ticks.append(int(event["tick"]))

            return ticks

        combat = result["combat"]
        combat["status"] = combat_window["status"]
        combat["parse_status"] = sources

        combat["player_weapon_fire_ticks"] = event_ticks(
            "weapon_fire", player_id
        )
        combat["teammate_weapon_fire_ticks"] = event_ticks(
            "weapon_fire", teammate_id
        )
        combat["player_hurt_killer_ticks"] = event_ticks(
            "player_hurt", player_id, killer_id
        )
        combat["teammate_hurt_killer_ticks"] = event_ticks(
            "player_hurt", teammate_id, killer_id
        )
        combat["killer_hurt_teammate_ticks"] = event_ticks(
            "player_hurt", killer_id, teammate_id
        )

        combat["player_damaged_killer"] = _observed(
            combat["player_hurt_killer_ticks"],
            sources.get("player_hurt"),
        )
        combat["teammate_damaged_killer"] = _observed(
            combat["teammate_hurt_killer_ticks"],
            sources.get("player_hurt"),
        )
        combat["killer_damaged_teammate"] = _observed(
            combat["killer_hurt_teammate_ticks"],
            sources.get("player_hurt"),
        )
        combat["player_weapon_event_observed"] = _observed(
            combat["player_weapon_fire_ticks"],
            sources.get("weapon_fire"),
        )

    # Visual-contact evidence is approximate and separate.
    observations = getattr(library, "team_observations", None)

    if observations is not None:
        result["contact"] = assess_trade_contact(
            observations,
            round_number=int(round_number),
            observer_team=int(observer_team),
            player_steamid=player_id,
            killer_steamid=killer_id,
            start_tick=start,
            end_tick=end,
        )

    streams = getattr(library, "player_streams", {})
    player_stream = streams.get(player_id)
    teammate_stream = streams.get(teammate_id)

    if player_stream is None or teammate_stream is None:
        result["status"] = "partial_evidence"
        return result

    player_rows = player_stream[
        (player_stream["tick"] >= position_start)
        & (player_stream["tick"] <= end)
    ].sort_values("tick")

    teammate_rows = teammate_stream[
        (teammate_stream["tick"] >= round_start_tick)
        & (teammate_stream["tick"] <= end)
    ].sort_values("tick")

    teammate_ticks = [
        int(value) for value in teammate_rows["tick"]
    ]

    for _, row in player_rows.iterrows():
        tick = int(row["tick"])
        index = bisect_right(teammate_ticks, tick) - 1

        if index < 0:
            continue

        other_row = teammate_rows.iloc[index]
        sample_age = tick - int(other_row["tick"])

        if not 0 <= sample_age <= library.max_state_age_ticks:
            continue

        player = player_from_row(row)
        teammate = player_from_row(other_row)

        if (
            player["team"] != observer_team
            or teammate["team"] != observer_team
        ):
            continue

        if (
            player["status"]["is_alive"] is not True
            or teammate["status"]["is_alive"] is not True
        ):
            continue

        first = player["position"]
        second = teammate["position"]

        values = [
            first.get(axis) for axis in ("x", "y", "z")
        ] + [
            second.get(axis) for axis in ("x", "y", "z")
        ]

        if not all(
            value is not None and math.isfinite(value)
            for value in values
        ):
            continue

        constraints = assess_player_constraints(
            player,
            tick=tick,
            max_age_ticks=library.max_state_age_ticks,
        )

        result["position_samples"].append({
            "tick": tick,
            "player_sample_tick": player["sample_tick"],
            "teammate_sample_tick": teammate["sample_tick"],
            "player_position": first,
            "teammate_position": second,
            "distance_2d": round(
                math.hypot(
                    first["x"] - second["x"],
                    first["y"] - second["y"],
                ), 2
            ),
            "vertical_separation": round(
                abs(first["z"] - second["z"]), 2
            ),
            "player_yaw": player["view"]["yaw"],
            "player_constraints": {
                "status": constraints["status"],
                "limitations": constraints["limitations"],
            },
        })

    samples = result["position_samples"]

    if len(samples) >= 2:
        result["distance_change_2d"] = round(
            samples[-1]["distance_2d"]
            - samples[0]["distance_2d"],
            2,
        )

    result["status"] = (
        "sampled_evidence" if samples else "partial_evidence"
    )

    return result


def assess_support_timing(
    context,
    *,
    proximity_ticks=32,
    movement_lookback_ticks=32,
    max_sample_age_ticks=16,
):
    if (
        proximity_ticks <= 0
        or movement_lookback_ticks <= 0
        or max_sample_age_ticks < 0
    ):
        raise ValueError("Invalid timing parameters")

    start = int(context["window_start_tick"])
    end = int(context["window_end_tick"])
    death_tick = int(context["death_tick"])
    combat = context["combat"]
    sources = combat.get("parse_status") or {}

    result = {
        "status": "insufficient_evidence",
        "evaluation_status": "not_evaluated",
        "support_opportunity": "not_established",
        "reference_tick": None,
        "reference_source": None,
        "damage_contact_ticks": [],
        "activity": {
            "status": "unknown",
            "weapon_event_ticks": [],
            "damage_killer_ticks": [],
            "nearest_weapon_event_delta_ticks": None,
            "nearest_damage_delta_ticks": None,
        },
        "movement": {
            "status": "insufficient_aligned_samples",
            "before_tick": None,
            "reference_sample_tick": None,
            "player_displacement_2d": None,
            "teammate_displacement_2d": None,
            "separation_change_2d": None,
        },
        "limitations": [
            "Damage contact does not prove a gunfight or peek.",
            "Weapon events do not establish their intended target.",
            "Movement alignment does not establish line of sight.",
            "No missed-support verdict is produced.",
        ],
    }

    if end < start or end >= death_tick:
        return result

    def valid_ticks(field):
        values = []

        for value in combat.get(field, []):
            try:
                tick = int(value)
            except (TypeError, ValueError, OverflowError):
                continue

            if start <= tick <= end:
                values.append(tick)

        return sorted(set(values))

    # Only damage between the teammate and the killer
    # can establish a pre-death damage-contact reference.
    contacts = sorted(set(
        valid_ticks("teammate_hurt_killer_ticks")
        + valid_ticks("killer_hurt_teammate_ticks")
    ))

    if contacts:
        reference = contacts[0]
        result["reference_source"] = "observed_damage_contact"
    else:
        reference = death_tick
        result["reference_source"] = "death_tick_fallback"

    result["reference_tick"] = reference
    result["damage_contact_ticks"] = contacts

    left = max(start, reference - proximity_ticks)
    right = min(end, reference + proximity_ticks)

    def near_reference(values):
        return [
            tick for tick in values
            if left <= tick <= right
        ]

    weapon_ticks = near_reference(
        valid_ticks("player_weapon_fire_ticks")
    )
    damage_ticks = near_reference(
        valid_ticks("player_hurt_killer_ticks")
    )

    def nearest_delta(values):
        if not values:
            return None

        closest = min(
            values,
            key=lambda tick: (abs(tick - reference), tick),
        )
        return closest - reference

    activity = result["activity"]
    activity["weapon_event_ticks"] = weapon_ticks
    activity["damage_killer_ticks"] = damage_ticks
    activity["nearest_weapon_event_delta_ticks"] = (
        nearest_delta(weapon_ticks)
    )
    activity["nearest_damage_delta_ticks"] = (
        nearest_delta(damage_ticks)
    )

    if damage_ticks:
        activity["status"] = "damage_on_killer_observed"
    elif weapon_ticks:
        activity["status"] = "weapon_activity_target_unknown"
    elif sources.get("weapon_fire") == "parsed":
        activity["status"] = "no_weapon_event_observed"
    else:
        activity["status"] = "unknown"

    samples = context.get("position_samples") or []

    def sample_before(target):
        best = None

        for sample in samples:
            try:
                tick = int(sample["tick"])
                player_tick = int(sample["player_sample_tick"])
                teammate_tick = int(sample["teammate_sample_tick"])
            except (KeyError, TypeError, ValueError):
                continue

            if tick > target:
                continue

            if not (
                0 <= target - player_tick <= max_sample_age_ticks
                and 0 <= target - teammate_tick <= max_sample_age_ticks
            ):
                continue

            if player_tick > tick or teammate_tick > tick:
                continue

            if best is None or tick > best["tick"]:
                best = sample

        return best

    baseline_tick = reference - movement_lookback_ticks

    before = sample_before(baseline_tick)
    current = sample_before(reference)

    if before is not None and current is not None:
        def displacement(key):
            first = before[key]
            second = current[key]

            return round(math.hypot(
                second["x"] - first["x"],
                second["y"] - first["y"],
            ), 2)

        movement = result["movement"]
        movement["status"] = "paired_samples"
        movement["before_tick"] = int(before["tick"])
        movement["reference_sample_tick"] = int(
            current["tick"]
        )
        movement["player_displacement_2d"] = displacement(
            "player_position"
        )
        movement["teammate_displacement_2d"] = displacement(
            "teammate_position"
        )
        movement["separation_change_2d"] = round(
            current["distance_2d"]
            - before["distance_2d"],
            2,
        )

    if (
        contacts
        or weapon_ticks
        or damage_ticks
        or result["movement"]["status"] == "paired_samples"
    ):
        result["status"] = "observations_available"

    return result
