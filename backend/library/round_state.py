
"""Round context from observations available at a requested tick."""

from collections import Counter


def _alive_value(player):
    status = player.get("status")
    if isinstance(status, dict):
        value = status.get("is_alive")
    else:
        value = player.get("is_alive")

    return value if isinstance(value, bool) else None


def build_round_state(
    *,
    tick,
    round_info,
    players,
    completed_results,
    expected_players_per_team=5,
):
    tick = int(tick)

    alive = Counter()
    observed = Counter()
    unknown_alive = Counter()

    for player in players:
        team = player.get("team")
        if team not in (2, 3):
            continue

        side = "T" if team == 2 else "CT"
        observed[side] += 1

        value = _alive_value(player)
        if value is True:
            alive[side] += 1
        elif value is None:
            unknown_alive[side] += 1

    alive_counts = {}
    coverage = {}

    for side in ("T", "CT"):
        complete = (
            observed[side] == expected_players_per_team
            and unknown_alive[side] == 0
        )
        alive_counts[side] = (
            alive[side] if complete else None
        )
        coverage[side] = {
            "observed_players": observed[side],
            "expected_players": expected_players_per_team,
            "unknown_alive": unknown_alive[side],
            "complete": complete,
        }

    # A CT/T win count is NOT necessarily the actual
    # team scoreboard after halftime side switches.
    wins_by_side = {"T": 0, "CT": 0}

    for result in completed_results:
        winner = result.get("winner")
        if winner in wins_by_side:
            wins_by_side[winner] += 1

    return {
        "tick": tick,
        "round_number": round_info["number"],
        "live_start_tick": round_info["live_start_tick"],
        "phase": "live",
        "alive": alive_counts,
        "alive_coverage": coverage,
        "completed_wins_by_side": wins_by_side,
        "score": {
            "status": "not_available",
            "reason": "team_identity_history_required",
            "team_a": None,
            "team_b": None,
        },
        "clock": {
            "remaining_seconds": None,
            "status": "awaiting_clock_source",
        },
        "bomb": {
            "status": "unknown",
            "carrier": None,
            "site": None,
            "source_tick": None,
        },
    }
