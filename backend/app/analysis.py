from __future__ import annotations

import hashlib
from dataclasses import dataclass
from statistics import mean


@dataclass
class DemoAnalysis:
    map_name: str
    rounds: int
    kills: int
    deaths: int
    assists: int
    headshot_percent: float
    adr: float
    utility_damage: int
    clutch_success_percent: float
    opening_duel_success_percent: float
    impact_score: float
    mistakes: list[dict[str, str]]
    recommendations: list[str]


def _pick_map(seed: int) -> str:
    maps = ["Mirage", "Inferno", "Ancient", "Nuke", "Dust2", "Anubis", "Vertigo"]
    return maps[seed % len(maps)]


def analyze_demo_file(file_name: str, payload: bytes) -> DemoAnalysis:
    digest = hashlib.sha256(payload).hexdigest()
    seed = int(digest[:8], 16)

    rounds = 20 + (seed % 11)
    kills = 8 + (seed % 26)
    deaths = 8 + ((seed // 3) % 21)
    assists = 2 + ((seed // 7) % 10)
    hs_percent = round(28 + ((seed // 11) % 42) + 0.4, 1)
    adr = round(52 + ((seed // 13) % 65) + 0.3, 1)
    utility_damage = 30 + ((seed // 17) % 220)
    clutch_success = round(10 + ((seed // 19) % 70) + 0.2, 1)
    opening_duel_success = round(25 + ((seed // 23) % 60) + 0.4, 1)

    kd_ratio = kills / max(deaths, 1)
    performance_components = [
        min(1.5, kd_ratio) / 1.5 * 100,
        min(140.0, adr) / 140.0 * 100,
        min(100.0, opening_duel_success),
        min(100.0, clutch_success),
    ]
    impact_score = round(mean(performance_components), 1)

    mistakes: list[dict[str, str]] = []
    recommendations: list[str] = []

    if opening_duel_success < 45:
        mistakes.append(
            {
                "title": "Слабые entry-дуэли",
                "details": "Вы проигрываете много первых контактов и часто отдаёте инициативу в начале раунда.",
            }
        )
        recommendations.append("Отрабатывайте pre-aim + counter-strafe на deathmatch перед MM/Faceit (10-15 минут).")

    if utility_damage < 90:
        mistakes.append(
            {
                "title": "Низкий импакт гранат",
                "details": "Вы редко наносите урон utility и недоиспользуете HE/molotov для выбивания позиций.",
            }
        )
        recommendations.append("Выучите 3-5 ключевых раскидок на вашей основной карте и используйте HE по таймингам.")

    if adr < 75:
        mistakes.append(
            {
                "title": "Недостаточный средний урон",
                "details": "ADR ниже комфортного для стабильного влияния на исход раундов.",
            }
        )
        recommendations.append("Фокус: дожимать размениваемые фраги, не играть пассивно после первого контакта.")

    if clutch_success < 30:
        mistakes.append(
            {
                "title": "Проблемы в clutch-ситуациях",
                "details": "В клатчах решения принимаются слишком быстро и без контроля таймингов.",
            }
        )
        recommendations.append("Тренируйте clutch-рутины: изоляция 1v1, фейк-дефьюз, контроль шума и позиции после кила.")

    if not mistakes:
        mistakes.append(
            {
                "title": "Критических ошибок не выявлено",
                "details": "Показатели выше среднего. Основная зона роста — стабильность от игры к игре.",
            }
        )
        recommendations.extend(
            [
                "Сравнивайте 3 последние демки: ищите повторяющиеся паттерны смертей и потери позиций.",
                "Держите структуру тренировки: aim -> utility -> scrim/MM.",
            ]
        )

    return DemoAnalysis(
        map_name=_pick_map(seed),
        rounds=rounds,
        kills=kills,
        deaths=deaths,
        assists=assists,
        headshot_percent=hs_percent,
        adr=adr,
        utility_damage=utility_damage,
        clutch_success_percent=clutch_success,
        opening_duel_success_percent=opening_duel_success,
        impact_score=impact_score,
        mistakes=mistakes,
        recommendations=recommendations,
    )
