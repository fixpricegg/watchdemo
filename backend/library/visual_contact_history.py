
"""Historical visual contacts from existing team observations."""

from collections import defaultdict
from copy import deepcopy


def build_visual_contact_history(
    observations,
    *,
    round_number,
    observer_team,
    tick,
    limit_per_enemy=20,
):
    if not isinstance(limit_per_enemy, int) or limit_per_enemy < 1:
        raise ValueError("limit_per_enemy must be positive")

    tick = int(tick)
    grouped = defaultdict(list)

    for observation in observations:
        if observation["round"] != round_number:
            continue
        if observation["observer_team"] != observer_team:
            continue
        if int(observation["tick"]) > tick:
            continue

        enemy_id = observation["target_steamid"]

        grouped[enemy_id].append({
            "tick": int(observation["tick"]),
            "position": deepcopy(observation["position"]),
            "spotters": list(observation.get("spotters") or []),
        })

    result = []

    for enemy_id, contacts in grouped.items():
        contacts.sort(key=lambda item: item["tick"])
        latest = contacts[-1]
        age = tick - latest["tick"]

        result.append({
            "target_steamid": enemy_id,
            "last_seen_tick": latest["tick"],
            "last_seen_position": deepcopy(latest["position"]),
            "last_seen_by": list(latest["spotters"]),
            "age_ticks": age,
            "status": (
                "observed_at_tick"
                if age == 0 else "last_known"
            ),
            "history": deepcopy(contacts[-limit_per_enemy:]),
            "source": "approximate_spotted_by",
        })

    result.sort(
        key=lambda item: (
            item["age_ticks"],
            str(item["target_steamid"]),
        )
    )

    return result
