
import math
from information import normalize_steamid


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
        if team not in (2, 3):
            continue

        teammates = [
            p for p in state["ground_truth"]["players"]
            if p.get("team") == team
            and p.get("sample_tick") == start
            and p.get("status", {}).get("is_alive") is True
            and normalize_steamid(p.get("steamid")) is not None
        ]

        actor = next(
            (p for p in teammates if p["steamid"] == player_id),
            None,
        )

        if (actor is None or len(teammates) < 4
                or len({p["steamid"] for p in teammates}) != len(teammates)):
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
            "detector_version": 1,
            "sample_tick": int(start),
            "evidence_scope": "round_live_start_snapshot",
            "limitations": [
                "Пороги: минимум 3 союзника от $3000; игрок до $1200 и остаток от $3000.",
                "Стоимость снаряжения не равна сумме потраченных денег.",
                "Неизвестны план команды, договорённости о дропе и намеренное сохранение денег.",
                "Снимок первого live-тика не моделирует все покупки после начала раунда.",
            ],
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
