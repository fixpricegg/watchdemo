"""Small, deterministic public review contract shared by report, events and UI."""
from collections import Counter


LABELS = {
    "entry_death_candidate": ("Entry Death", "Первая смерть в раунде", 3),
    "trade_review_candidate": ("Missed Trade v2", "Проверка возможности размена", 2),
    "buy_mismatch_candidate": ("Buy Mismatch", "Проверка согласованности закупки", 1),
}


def build_review_findings(entries, trades, buys):
    findings = []
    seen = set()
    for candidate in [*entries, *trades, *buys]:
        kind = candidate["type"]
        detector, title, priority = LABELS[kind]
        evidence = candidate.get("decision_evidence") or {}
        if evidence.get("status") == "not_applicable_actor_dead":
            continue
        # Damage/limitations/unknown visibility weaken an alleged missed trade.
        # Keep the evidence accessible, but reduce review priority, never invent severity.
        if kind == "trade_review_candidate" and evidence.get("status") != "review_required":
            priority = 1
        key = (kind, candidate["round"], candidate["tick"], candidate.get("victim_steamid"))
        if key in seen:
            continue
        seen.add(key)
        if kind == "entry_death_candidate":
            description = "Зафиксирована первая смерть игрока от противника в раунде. Причину решения нужно проверить."
            facts = [f"От начала раунда: {candidate['seconds_from_live_start']} с.",
                     "Размен в течение 4 с: " + {True: "наблюдался", False: "не наблюдался", None: "окно неполное"}[candidate["traded_within_window"]]]
        elif kind == "trade_review_candidate":
            description = "После смерти союзника противник выжил в окне 4 с. Навигационный путь найден; возможность выстрела не доказана."
            facts = [f"До союзника: {candidate['teammate_distance_2d']} ед. по XY.",
                     f"До противника: {candidate['killer_distance_2d']} ед. по XY.",
                     "Контекст: " + {
                         "review_required": "доступны наблюдения для разбора",
                         "target_damage_observed": "игрок нанёс урон противнику",
                         "player_limitations_observed": "наблюдались ограничения состояния игрока",
                         "visibility_unverified_smoke": "возможное перекрытие дымом; видимость не подтверждена",
                     }.get(evidence.get("status"), "данных недостаточно") + "."]
        else:
            description = "Слабое снаряжение при доступных деньгах и трёх экипированных союзниках. Намерение команды неизвестно."
            facts = [f"Снаряжение игрока: ${candidate['player_equipment_value']:g}.",
                     f"Остаток: ${candidate['remaining_balance']:g}; союзников со снаряжением от $3000: {candidate['equipped_teammates']}."]
        findings.append({
            "id": f"{kind}:{candidate['round']}:{candidate['tick']}:{candidate.get('victim_steamid') or candidate.get('player_steamid')}",
            "type": kind, "detector": detector, "title": title,
            "round": int(candidate["round"]), "tick": int(candidate["tick"]),
            "status": "review_required", "verdict": "not_evaluated",
            "review_priority": priority,
            "description": description, "facts": facts,
            "limitations": ([
                "Навигационный путь не доказывает возможность выстрела.",
                "Видимость, динамические препятствия и доступная игроку информация восстановлены не полностью.",
                "Посмертные наблюдения и выживание противника не являются знанием игрока до решения.",
                "Выборка состояний не доказывает непрерывную возможность действовать.",
            ] if kind == "trade_review_candidate" else candidate.get("limitations", [])),
            "evidence": candidate,
        })
    return sorted(findings, key=lambda f: (-f["review_priority"], f["round"], f["tick"], f["type"]))


def prioritize_reviews(findings):
    """Priority orders manual review, not probability or severity of a mistake."""
    counts = Counter(f["type"] for f in findings)
    groups = []
    for kind, (detector, title, _) in LABELS.items():
        episodes = [f for f in findings if f["type"] == kind]
        if not episodes:
            continue
        groups.append({
            "name": title, "detector": detector, "type": kind,
            "score": max(f["review_priority"] for f in episodes),
            "status": "review_required", "count": counts[kind],
            "description": f"Эпизодов для ручной проверки: {counts[kind]}. Подтверждённая ошибка не установлена.",
            "advice": ["Пересмотрите факты и ограничения эпизода на радаре."],
            "finding_ids": [f["id"] for f in episodes],
        })
    return sorted(groups, key=lambda p: (-p["score"], -p["count"], p["type"]))[:3]
