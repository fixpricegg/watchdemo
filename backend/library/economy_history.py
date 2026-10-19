
from copy import deepcopy


def build_economy_history(
    round_snapshots,
    current_round,
    limit=5,
):
    """
    Build historical ground-truth economy records.

    Only completed previous rounds are included.
    Current and future rounds are excluded.

    This is NOT safe for direct AI Decision Input:
    previous enemy economy may contain hidden data.
    """

    if not isinstance(current_round, int):
        raise ValueError("current_round must be an integer")

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    history = []

    for snapshot in round_snapshots:
        if not isinstance(snapshot, dict):
            continue

        round_number = snapshot.get("round")

        if not isinstance(round_number, int):
            continue

        # Strictly previous rounds only.
        if round_number >= current_round:
            continue

        history.append({
            "round": round_number,
            "live_start_tick": snapshot.get(
                "live_start_tick"
            ),
            "status": snapshot.get(
                "status", "unavailable"
            ),
            "teams": deepcopy(snapshot.get("teams")),
        })

    history.sort(key=lambda item: item["round"])

    # Keep the most recent N previous rounds.
    history = history[-limit:]

    return {
        "current_round": current_round,
        "rounds_available": len(history),
        "history": history,
    }
