from copy import deepcopy


GRENADE_NAME_MAP = {
    "Smoke Grenade": "smoke",
    "Flashbang": "flash",
    "HE Grenade": "he",
    "High Explosive Grenade": "he",
    "Molotov": "molotov",
    "Incendiary Grenade": "incendiary",
    "Decoy Grenade": "decoy",
}


def normalize_grenade_name(name):
    if not name:
        return None
    return GRENADE_NAME_MAP.get(str(name).strip())


def build_player_utility_from_inventory(player_state):
    """
    Extract current utility from player inventory snapshot.

    Returns:
        {
            "smoke": 0/1,
            "flash": int,
            "he": 0/1,
            "molotov": 0/1,
            "incendiary": 0/1,
            "decoy": 0/1,
            "total": int,
            "items": [...]
        }
    """
    inventory = player_state.get("inventory") or []
    counts = {
        "smoke": 0,
        "flash": 0,
        "he": 0,
        "molotov": 0,
        "incendiary": 0,
        "decoy": 0,
    }
    items = []

    for item in inventory:
        grenade = normalize_grenade_name(item)
        if grenade is None:
            continue
        counts[grenade] += 1
        items.append(grenade)

    result = deepcopy(counts)
    result["total"] = sum(counts.values())
    result["items"] = items
    return result


def build_team_utility(players):
    """
    Aggregate utility for a team from player snapshots.
    """
    team = {
        "smoke": 0,
        "flash": 0,
        "he": 0,
        "molotov": 0,
        "incendiary": 0,
        "decoy": 0,
        "total": 0,
        "players": 0,
    }

    for player in players:
        util = build_player_utility_from_inventory(player)
        for key in ("smoke", "flash", "he", "molotov", "incendiary", "decoy"):
            team[key] += util[key]
        team["total"] += util["total"]
        team["players"] += 1

    return team


def build_round_utility_timeline(event_rows, round_intervals, current_tick=None):
    """
    Build utility event timeline without future leakage.

    event_rows: iterable of dicts with at least:
      - tick
      - type
      - round (optional)
      - thrower / steamid / team (optional)

    round_intervals: [(match_round, demo_round, start_tick, end_tick), ...]

    Returns list:
      [
        {
          "round": 1,
          "events": [...]
        }
      ]
    """
    result = []

    for match_round, demo_round, start_tick, end_tick in round_intervals:
        if current_tick is not None and start_tick > int(current_tick):
            break

        effective_end = end_tick
        if current_tick is not None:
            effective_end = min(int(end_tick), int(current_tick))

        round_events = []
        for row in event_rows:
            tick = int(row["tick"])
            if tick < int(start_tick) or tick >= int(effective_end):
                continue

            round_events.append({
                "tick": tick,
                "type": row.get("type"),
                "thrower": row.get("thrower"),
                "steamid": row.get("steamid"),
                "team": row.get("team"),
                "position": row.get("position"),
                "extra": row.get("extra"),
            })

        result.append({
            "round": int(match_round),
            "demo_round": int(demo_round),
            "start_tick": int(start_tick),
            "end_tick": int(effective_end),
            "events": sorted(round_events, key=lambda x: x["tick"]),
        })

    return result