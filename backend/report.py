def format_time_left(ticks, round_time=115, tickrate=64):
    if ticks is None:
        return "нет данных"

    seconds_passed = ticks / tickrate
    seconds_left = int(round_time - seconds_passed)

    minutes = seconds_left // 60
    seconds = seconds_left % 60

    return f"{minutes}:{seconds:02d}"

def generate_report(player, stats):
    kd = stats["kd"]
    kills = stats["kills"]
    trade_kills = stats["trade_kills"]
    deaths = stats["deaths"]
    hs_rate = stats["hs_rate"]
    entry_kills = stats["entry_kills"]
    entry_deaths = stats["entry_deaths"]
    entry_success = stats["entry_success"]
    avg_time_first_kill = stats["avg_time_first_kill"]
    avg_time_first_death = stats["avg_time_first_death"]
    top_problems = stats["top_problems"]
    events = stats["events"]

    # ===== MAIN PROBLEMS =====
    problems = []

    if hs_rate is not None:
        if hs_rate < 0.20:
            problems.append((60, f"Очень низкий процент хедшотов - {hs_rate * 100:.1f}%"))
        elif hs_rate < 0.30:
            problems.append((50, f"Низкий процент хедшотов - {hs_rate * 100:.1f}%"))

    if kd < 0.8:
        problems.append((90, f"Слабая результативность в дуэлях - K/D {kd:.2f}"))
    elif kd < 1.0:
        problems.append((70, f"Ниже среднего результативность в дуэлях - K/D {kd:.2f}"))

    if entry_success is not None:
        entry_total = entry_kills + entry_deaths

        if entry_total >= 3:
            if entry_success < 40 and entry_deaths > 3:
                problems.append((80, f"Слабое влияние в opening-дуэлях - {entry_success:.0f}% успешности. Ты довольно часто фидишь первым."))
            elif entry_success < 50:
                problems.append((60, f"Нестабильное влияние в opening-дуэлях - {entry_success:.0f}% успешности"))

    if avg_time_first_death is not None:
        avg_first_death_sec = avg_time_first_death / 64

        if avg_first_death_sec < 25 and entry_deaths > 3:
            problems.append((85, f"Слишком ранние смерти - в среднем на {format_time_left(avg_time_first_death)}"))
        elif avg_first_death_sec < 40 and entry_deaths > 3:
            problems.append((60, f"Довольно ранние смерти - в среднем на {format_time_left(avg_time_first_death)}"))

    if avg_time_first_kill is not None:
        avg_first_kill_sec = avg_time_first_kill / 64

        if avg_first_kill_sec > 60:
            problems.append((50, f"Позднее вступление в первые дуэли - в среднем на {format_time_left(avg_time_first_kill)}"))
    problems.sort(reverse=True, key=lambda x: x[0])
    main_problems = problems[:3]

    lines = []

    lines.append("# WATCHDEMO REPORT")
    lines.append("")
    lines.append(f"## Player: {player}")
    lines.append("")

    lines.append("## KEY MOMENTS")

    if events:
        for i, event in enumerate(events, start=1):
            title = event.get("title", event.get("type", "event"))
            round_number = event.get("round", "нет данных")
            time = event.get("time")

            if time is not None:
                lines.append(f"{i}. {title} — Round {round_number}, {time}")
            else:
                lines.append(f"{i}. {title} — Round {round_number}")

            description = event.get("description")
            if description:
                lines.append(f"  - {description}")

            data = event.get("data", {})

            if "killer" in data:
                lines.append(f"  - Killer: {data['killer']}")

            if "kills" in data:
                lines.append(f"  - Kills: {data['kills']}")

            if "importance" in event:
                lines.append(f"  - Importance: {event['importance']}")

    else:
        lines.append("Ключевых моментов пока не найдено.")

    lines.append("")

    lines.append("## TOP PROBLEMS")
    if top_problems:
        for i, p in enumerate(top_problems, start=1):
            lines.append(f"{i}. {p['name'][:1].upper() + p['name'][1:]} \n{p['description']} \n \n")
            lines.append("Что делать:")
            for advice in p["advice"]:
                lines.append(f"- {advice}")
    else:
        lines.append("Явных проблем не найдено")
    lines.append("")

    # ===== SUMMARY =====
    summary = []
    strengths = []

    if hs_rate is not None and hs_rate >= 0.5:
        strengths.append("хорошая стрельба по голове")

    if entry_success is not None and entry_success >= 60:
        strengths.append("хорошее влияние в opening-дуэлях")

    if avg_time_first_death is not None and avg_time_first_death > 3500:
        strengths.append("аккуратная игра в начале раунда")

    if top_problems:
        main_problem = top_problems[0]

        summary.append(
            f"Основная проблема — {main_problem['name']}: {main_problem['description']}"
        )

    for p in top_problems[1:]:
        summary.append(
            f"Также наблюдается проблема: {p['name'].lower()}."
        )

    if not top_problems:
        summary.append(
            "Явных проблем в игре не обнаружено."
        )
    if strengths:
        summary.append(f"Сильная сторона: {strengths[0]}.")
    # if kd < 1:
    #     summary.append(f"Ты показываешь низкую результативность в дуэлях (K/D {kd:.2f}),")
    # elif kd < 1.2:
    #     summary.append(f"Ты показываешь среднюю результативность в дуэлях (K/D {kd:.2f}),")
    # else:
    #     summary.append(f"Ты показываешь хорошую результативность в дуэлях (K/D {kd:.2f}),")
    #
    # if hs_rate is not None:
    #     if hs_rate < 0.30:
    #         summary.append(f"также у тебя низкий процент хедшотов (HS% {hs_rate * 100:.1f})")
    #     elif hs_rate < 0.50:
    #         summary.append(f"также у тебя средний процент хедшотов (HS% {hs_rate * 100:.1f})")
    #     else:
    #         summary.append(f"также у тебя высокий процент хедшотов (HS% {hs_rate * 100:.1f})")
    #
    # if entry_success is not None:
    #     if entry_success < 40:
    #         summary.append("Влияние в opening-дуэлях довольно слабое.")
    #     elif entry_success < 60:
    #         summary.append("Влияние в opening-дуэлях остается нестабильным.")
    #     else:
    #         summary.append("Твое влияние в opening-дуэлях очень хорошее, ты часто даешь команде преимущество на старте.")
    #
    # if avg_time_first_death is not None:
    #     if avg_time_first_death < 1600 and entry_deaths >= 2:
    #         summary.append(f"Ты слишком рано умираешь в начале раунда (AVG: {format_time_left(avg_time_first_death)})")
    #     elif avg_time_first_death < 3520 and entry_deaths >= 2:
    #         summary.append(f"Ты довольно рано умираешь в начале раунда (AVG: {format_time_left(avg_time_first_death)})")
    #     else:
    #         summary.append(f"Ты редко умираешь на ранних таймингах. (AVG: {format_time_left(avg_time_first_death)})")

    lines.append("### SUMMARY")
    if summary:
        for item in summary:
            lines.append(f"- {item}")

    else:
        lines.append("- Недостаточно данных для итогового вывода")
    lines.append("")


    lines.append("## STATS")
    lines.append("### COMBAT")
    lines.append(f"- K/D: {kd:.2f}")
    lines.append(f"- Kills: {kills}")
    lines.append(f"- Deaths: {deaths}")

    if kd < 1:
        lines.append("- Комментарий: низкая результативность в дуэлях")
    elif kd < 1.2:
        lines.append("- Комментарий: средняя результативность")
    else:
        lines.append("- Комментарий: хорошая результативность")
    lines.append("")

    lines.append("### MULTI-KILLS")
    lines.append(f"- 2K rounds: {stats['two_k']}")
    lines.append(f"- 3K rounds: {stats['three_k']}")
    lines.append(f"- 4K rounds: {stats['four_k']}")
    lines.append(f"- Ace rounds: {stats['ace']}")
    lines.append(f"- Multi-kill rounds: {stats['multi_kills']}")
    lines.append("")

    lines.append("### AIM")
    if hs_rate is not None:
        lines.append(f"- HS%: {hs_rate * 100:.1f}")
        if hs_rate < 0.30:
            lines.append("- Комментарий: низкий процент хедшотов")
        elif hs_rate < 0.50:
            lines.append("- Комментарий: нормальный процент хедшотов")
        else:
            lines.append("- Комментарий: сильная стрельба по голове")
    else:
        lines.append("- HS%: нет данных")
    lines.append("")

    lines.append("### ENTRY")
    lines.append(f"- Entry kills: {entry_kills}")
    lines.append(f"- Entry deaths: {entry_deaths}")
    if entry_success is not None:
        lines.append(f"- Entry success: {entry_success:.0f}%")
    else:
        lines.append("- Entry success: нет данных")
    lines.append("")

    lines.append("### TRADE")
    lines.append(f"- Trade kills: {trade_kills}")
    lines.append("")

    lines.append("### TIMING")
    if avg_time_first_kill is not None:
        formatted_kill_time = format_time_left(avg_time_first_kill)
        lines.append(f"- Среднее время опен-килла: {formatted_kill_time}")
        if avg_time_first_kill < 1600:
            lines.append("- Комментарий: ты часто находишь ранние опен-киллы, но это рискованный стиль")
        elif avg_time_first_kill < 3520:
            lines.append("- Комментарий: у тебя умеренные тайминги на первые дуэли")
        else:
            lines.append("- Комментарий: ты поздно вступаешь в первые контакты")
    else:
        lines.append("- Среднее время опен-килла: нет данных")

    if avg_time_first_death is not None:
        formatted_death_time = format_time_left(avg_time_first_death)
        lines.append(f"- Среднее время первой смерти: {formatted_death_time}")
        if avg_time_first_death < 2240:
            lines.append("- Комментарий: ты слишком рано умираешь в начале раунда")
        elif avg_time_first_death < 3840:
            lines.append('''- Комментарий: тайминги первых смертей в норме.
             Ты не фидишь в начале раунда''')
        else:
            lines.append("- Комментарий: ты редко умираешь на ранних таймингах")
    else:
        lines.append("- Среднее время первой смерти: нет данных")
    lines.append("")

    return "\n".join(lines)