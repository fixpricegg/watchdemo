
"""Observed utility effects without future-event leakage."""

from copy import deepcopy


START_EVENTS = {
    "smokegrenade_detonate": "smoke",
    "inferno_startburn": "fire",
}

END_EVENTS = {
    "smokegrenade_expired": "smoke",
    "inferno_expire": "fire",
}


def build_active_utility(events, tick):
    """
    Reconstruct utility effects from events already observed.

    No predicted expiry times or future projectile data.
    """
    tick = int(tick)

    effects = {}
    unmatched_ends = []

    ordered = sorted(
        (
            e for e in events
            if int(e["tick"]) <= tick
        ),
        key=lambda e: int(e["tick"]),
    )

    for event in ordered:
        event_type = event["type"]
        event_tick = int(event["tick"])
        data = event.get("data") or {}

        entity_id = data.get("entity_id")

        if event_type in START_EVENTS:
            kind = START_EVENTS[event_type]

            # Entity ID is needed for reliable matching.
            if entity_id is None:
                continue

            key = (kind, str(entity_id))

            effects[key] = {
                "type": kind,
                "entity_id": entity_id,
                "start_tick": event_tick,
                "end_tick": None,
                "x": data.get("x"),
                "y": data.get("y"),
                "z": data.get("z"),
                "status": "end_unconfirmed",
                "source": "demo_event",
            }

        elif event_type in END_EVENTS:
            kind = END_EVENTS[event_type]

            if entity_id is None:
                unmatched_ends.append(event_tick)
                continue

            key = (kind, str(entity_id))

            if key in effects:
                effects[key]["end_tick"] = event_tick
                effects[key]["status"] = "ended"
            else:
                unmatched_ends.append(event_tick)

    ongoing_candidates = [
        effect for effect in effects.values()
        if effect["end_tick"] is None
    ]

    ended = [
        effect for effect in effects.values()
        if effect["end_tick"] is not None
    ]

    return {
        "tick": tick,
        "status": (
            "partial" if unmatched_ends else "observed"
        ),
        "ongoing_candidates": deepcopy(ongoing_candidates),
        "ended": deepcopy(ended),
        "unmatched_end_ticks": unmatched_ends,
        "flash_blind_state": {
            "status": "unavailable",
            "reason": "player_blind_data_not_integrated",
        },
    }
