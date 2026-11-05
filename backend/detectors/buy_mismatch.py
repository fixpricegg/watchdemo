
import math


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def detect_buy_mismatch(library, player):
    findings = []

    for round_number, _, start, end in library.round_intervals:
        try:
            state = library.get_game_state(start, player)
        except ValueError:
            continue

        player_id = state["perspective"]["steamid"]
        team = state["perspective"]["team"]

        teammates = [
            p for p in state["ground_truth"]["players"]
            if p.get("team") == team
        ]

        actor = next(
            (p for p in teammates if p["steamid"] == player_id),
            None,
        )

        if actor is None or len(teammates) < 4:
            continue

        actor_economy = actor.get("economy") or {}
        equipment = number(
            actor_economy.get("current_equip_value")
        )
        balance = number(actor_economy.get("balance"))

        if equipment is None or balance is None:
            continue

        equipped_teammates = 0
        known_teammates = 0

        for teammate in teammates:
            if teammate["steamid"] == player_id:
                continue

            value = number(
                (teammate.get("economy") or {}).get(
                    "current_equip_value"
                )
            )

            if value is None:
                continue

            known_teammates += 1

            if value >= 3000:
                equipped_teammates += 1

        if known_teammates < 3:
            continue

        if not (
            equipped_teammates >= 3
            and equipment <= 1200
            and balance >= 3000
        ):
            continue

        findings.append({
            "type": "buy_mismatch_candidate",
            "status": "review_required",
            "round": int(round_number),
            "tick": int(start),
            "player_steamid": player_id,
            "player_equipment_value": equipment,
            "remaining_balance": balance,
            "equipped_teammates": equipped_teammates,
            "known_teammates": known_teammates,
            "confidence": None,
            "verdict": "not_evaluated",
            "reason": "possible_uncoordinated_buy",
        })

    return findings
