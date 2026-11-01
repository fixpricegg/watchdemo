
import information


def assess_trade_contact(
    observations,
    *,
    round_number,
    observer_team,
    player_steamid,
    killer_steamid,
    start_tick,
    end_tick,
):
    if end_tick < start_tick:
        raise ValueError("Invalid contact window")

    player_id = information.normalize_steamid(player_steamid)
    killer_id = information.normalize_steamid(killer_steamid)

    personal_ticks = []
    team_ticks = []

    for observation in observations:
        if int(observation["round"]) != round_number:
            continue

        if int(observation["observer_team"]) != observer_team:
            continue

        tick = int(observation["tick"])

        if not start_tick <= tick <= end_tick:
            continue

        target_id = information.normalize_steamid(
            observation.get("target_steamid")
        )

        if target_id != killer_id:
            continue

        spotters = {
            information.normalize_steamid(value)
            for value in observation.get("spotters", [])
        }

        if not spotters:
            continue

        team_ticks.append(tick)

        if player_id in spotters:
            personal_ticks.append(tick)

    return {
        "source": "approximate_spotted_by",
        "window_start_tick": int(start_tick),
        "window_end_tick": int(end_tick),
        "personal_contact_observed": bool(personal_ticks),
        "team_contact_observed": bool(team_ticks),
        "first_personal_contact_tick": (
            min(personal_ticks) if personal_ticks else None
        ),
        "first_team_contact_tick": (
            min(team_ticks) if team_ticks else None
        ),
        "line_of_fire": "not_verified",
        "trade_feasibility": "not_established",
    }
