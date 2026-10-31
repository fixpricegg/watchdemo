
"""Perspective-aware scoreboard without future results."""


def build_perspective_score(completed_results, side_by_round):
    """
    completed_results: only results available at the query tick.
    side_by_round: {round_number: "T" | "CT"} for the player.

    Scores follow the player's team, not fixed CT/T sides.
    """
    ours = 0
    theirs = 0
    unknown_rounds = []

    for result in completed_results:
        round_number = int(result["round"])
        winner = result.get("winner_side")
        our_side = side_by_round.get(round_number)

        if winner not in ("T", "CT") or our_side not in ("T", "CT"):
            unknown_rounds.append(round_number)
            continue

        if winner == our_side:
            ours += 1
        else:
            theirs += 1

    return {
        "ours": ours,
        "theirs": theirs,
        "status": "complete" if not unknown_rounds else "partial",
        "unknown_rounds": unknown_rounds,
        "source": "completed_round_results",
    }
