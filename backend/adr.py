"""Observed completed-round ADR, independent of Match Library and detectors."""
import math


def integer(value):
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number == int(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def sid(value):
    # Do not pass 64-bit Steam IDs through float.
    try:
        return str(int(value)) if value is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def calculate_adr(hurts, rounds, round_ends, positions, pre_health, player_id):
    result = {"value": None, "status": "unavailable", "known_damage": 0,
              "rounds_played": 0, "rounds": [], "unknown_hits": 0,
              "reason": "Недостаточно данных player_hurt, участия или границ раундов"}
    if player_id is None or hurts is None or positions is None or round_ends is None:
        return result
    required = {"tick", "attacker_steamid", "user_steamid", "attacker_team_num", "user_team_num", "dmg_health", "health", "weapon"}
    if not required.issubset(hurts.columns) or not {"tick", "steamid", "team_num"}.issubset(positions.columns) or not {"tick", "winner"}.issubset(round_ends.columns):
        return result
    # Steam IDs lose integer precision if a source coerces them to floating point.
    for frame, column in ((hurts, "attacker_steamid"), (hurts, "user_steamid"), (positions, "steamid")):
        if any(isinstance(value, float) and math.isfinite(value) and abs(value) > 2 ** 53 for value in frame[column]):
            return result
    player_id = sid(player_id)
    if player_id in (None, "0"):
        return result
    selected = positions[positions.steamid.map(sid) == player_id]
    intervals = []
    incomplete = False
    for round_data in rounds:
        start, stop = int(round_data["live_start_tick"]), int(round_data["end_tick"])
        ends = round_ends[(round_ends.tick >= start) & (round_ends.tick < stop) & round_ends.winner.isin(["CT", "T"])]
        active = selected[(selected.tick >= start) & (selected.tick < stop) & selected.team_num.isin([2, 3])]
        if active.empty:
            continue
        if ends.empty:
            incomplete = True
            continue
        end = int(ends.tick.min())
        if active[active.tick <= end].empty:
            continue
        row = {"round": int(round_data["round"]), "damage": 0}
        intervals.append((start, end, row))
        result["rounds"].append(row)
    result["rounds_played"] = len(intervals)
    if not intervals:
        return result
    before = {}
    if pre_health is not None and {"tick", "steamid", "health"}.issubset(pre_health.columns):
        for row in pre_health.itertuples(index=False):
            snapshot_tick = integer(row.tick)
            if snapshot_tick is None:
                continue
            key = (snapshot_tick + 1, sid(row.steamid))
            health = integer(row.health)
            if key in before and before[key] != health:
                before[key] = None
            else:
                before[key] = health
    # Stable event order matters when several hits affect one victim in a tick.
    same_tick = {}
    for event in hurts.sort_values("tick", kind="stable").to_dict("records"):
        tick = integer(event["tick"])
        victim = sid(event["user_steamid"])
        key = (tick, victim)
        prior = same_tick.get(key, before.get(key))
        same_tick[key] = integer(event["health"])
        if sid(event["attacker_steamid"]) != player_id or victim == player_id:
            continue
        if tick is None:
            result["unknown_hits"] += 1
            continue
        interval = next((row for start, end, row in intervals if tick is not None and start <= tick <= end), None)
        if interval is None or str(event["weapon"]).lower() in {"world", "c4", "planted_c4"}:
            continue
        attacker_team, victim_team = integer(event["attacker_team_num"]), integer(event["user_team_num"])
        if attacker_team in (2, 3) and attacker_team == victim_team:
            continue
        damage = integer(event["dmg_health"])
        if attacker_team not in (2, 3) or victim_team not in (2, 3) or victim in (None, "0") or damage is None or damage < 0 or prior is None or prior < 0:
            result["unknown_hits"] += 1
            continue
        interval["damage"] += min(damage, prior)
    result["known_damage"] = sum(row["damage"] for row in result["rounds"])
    if result["unknown_hits"] or incomplete:
        result.update(status="partial", reason="Неполные данные попаданий или незавершённый раунд; ADR не вычислен")
    else:
        result.update(value=round(result["known_damage"] / len(intervals), 2), status="ok", reason=None)
    return result
