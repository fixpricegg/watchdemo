"""Human-readable report with the same evidence limits as the application."""


def format_time_left(ticks, round_time=115, tickrate=64):
    if ticks is None:
        return "нет данных"
    seconds = max(0, int(round_time - ticks / tickrate))
    return f"{seconds // 60}:{seconds % 60:02d}"


def generate_report(player, stats):
    lines = [f"# WatchDemo — {player}", "",
             "Эпизоды требуют ручной проверки. Подтверждённые игровые ошибки не установлены.",
             "", "## Статистика",
             f"Убийства / смерти: {stats['kills']} / {stats['deaths']}",
             f"K/D: {stats['kd']:.2f}",
             f"ADR: {stats.get('adr') if stats.get('adr') is not None else 'нет данных'}",
             f"Entry kills / deaths: {stats['entry_kills']} / {stats['entry_deaths']}",
             f"Trade kills: {stats['trade_kills']}",
             f"HS%: {round(stats['hs_rate'] * 100, 1) if stats.get('hs_rate') is not None else 'нет данных'}",
             f"Entry success: {stats.get('entry_success') if stats.get('entry_success') is not None else 'нет данных'}",
             f"Multi-kills: {stats.get('multi_kills', 0)}; 2K {stats.get('two_k', 0)}, 3K {stats.get('three_k', 0)}, 4K {stats.get('four_k', 0)}, ace {stats.get('ace', 0)}",
             "", "## Приоритеты разбора"]
    for group in stats.get("top_problems", []):
        lines.append(f"- {group['name']}: {group['description']} Приоритет просмотра {group['score']}.")
    findings = stats.get("review_findings", [])
    if not findings:
        lines.append("Кандидаты по выбранным правилам не найдены. Это не означает отсутствие ошибок.")
    lines.extend(["", "## Эпизоды"])
    for finding in findings:
        lines.extend([f"### {finding['detector']} — раунд {finding['round']}, тик {finding['tick']}",
                      finding["description"], *[f"- {f}" for f in finding["facts"]],
                      *[f"- Ограничение: {v}" for v in finding["limitations"]], ""])
    return "\n".join(lines)
