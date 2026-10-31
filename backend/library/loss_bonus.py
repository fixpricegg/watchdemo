
from bisect import bisect_right

import pandas as pd


CT_LOSS_FIELD = (
    "CCSGameRulesProxy.CCSGameRules."
    "m_iNumConsecutiveCTLoses"
)

T_LOSS_FIELD = (
    "CCSGameRulesProxy.CCSGameRules."
    "m_iNumConsecutiveTerroristLoses"
)


def build_loss_counter_timeline(df):
    """
    Normalize engine loss counters into a tick timeline.

    The parser returns one row per player.
    GameRules values are shared by the match.

    No monetary interpretation is performed here.
    """
    required = {"tick", CT_LOSS_FIELD, T_LOSS_FIELD}

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing loss counter fields: {missing}"
        )

    timeline = []

    for tick, group in df.groupby("tick", sort=True):
        ct_values = group[CT_LOSS_FIELD].dropna().unique()
        t_values = group[T_LOSS_FIELD].dropna().unique()

        if len(ct_values) != 1 or len(t_values) != 1:
            raise ValueError(
                f"Inconsistent loss counters at tick {tick}"
            )

        timeline.append({
            "tick": int(tick),
            "CT": int(ct_values[0]),
            "T": int(t_values[0]),
        })

    return timeline


def get_loss_counters_at_tick(timeline, tick):
    """
    Return the last recorded counter state at or before tick.

    Never reads a future snapshot.
    """
    ticks = [item["tick"] for item in timeline]
    index = bisect_right(ticks, int(tick)) - 1

    if index < 0:
        return {
            "tick": int(tick),
            "status": "unavailable",
            "source_tick": None,
            "CT": None,
            "T": None,
        }

    state = timeline[index]

    return {
        "tick": int(tick),
        "status": "available",
        "source_tick": state["tick"],
        "CT": state["CT"],
        "T": state["T"],
    }


def counter_to_loss_reward(counter):
    """
    Standard competitive CS2 base loss reward.

    This is not the player's total cash payout.
    """
    if counter is None or isinstance(counter, bool):
        return None

    try:
        value = float(counter)
    except (TypeError, ValueError):
        return None

    if not value.is_integer() or value < 0:
        return None

    return 1400 + 500 * min(int(value), 4)


def get_next_loss_reward(timeline, tick):
    """
    Base reward if a team lost with the counters
    observed at exactly this tick.

    Sparse, outdated snapshots are not treated
    as confirmed current values.
    """
    tick = int(tick)

    state = get_loss_counters_at_tick(timeline, tick)

    exact = (
        state["status"] == "available"
        and state["source_tick"] == tick
    )

    return {
        "tick": tick,
        "status": "available" if exact else "unavailable",
        "source_tick": state["source_tick"],
        "base_reward_if_lost_now": {
            "CT": (
                counter_to_loss_reward(state["CT"])
                if exact else None
            ),
            "T": (
                counter_to_loss_reward(state["T"])
                if exact else None
            ),
        },
    }


def get_loss_reward_for_round(timeline, round_result):
    """
    Calculate the losing team's BASE reward.

    IMPORTANT:
    Use counter at result_tick - 1, because
    CS2 updates the counters at round_end.

    The returned amount is rule-derived, not
    a directly observed cash transaction.
    """
    result = {
        "round": round_result.get("round"),
        "result_tick": round_result.get("result_tick"),
        "winner_side": round_result.get("winner_side"),
        "loser_side": round_result.get("loser_side"),
        "status": "unavailable",
        "counter_before_result": None,
        "counter_after_result": None,
        "base_loss_reward": None,
        "source": "standard_competitive_rules",
    }

    winner = result["winner_side"]
    loser = result["loser_side"]
    end_tick = result["result_tick"]

    if (
        winner not in ("T", "CT")
        or loser not in ("T", "CT")
        or winner == loser
        or end_tick is None
    ):
        result["status"] = "unknown"
        return result

    end_tick = int(end_tick)

    before = get_loss_counters_at_tick(
        timeline, end_tick - 1
    )

    after = get_loss_counters_at_tick(
        timeline, end_tick
    )

    # Exact pre-result sample is required.
    if (
        before["status"] != "available"
        or before["source_tick"] != end_tick - 1
    ):
        return result

    counter = before[loser]

    result["counter_before_result"] = counter
    result["base_loss_reward"] = (
        counter_to_loss_reward(counter)
    )

    if (
        after["status"] == "available"
        and after["source_tick"] == end_tick
    ):
        result["counter_after_result"] = after[loser]

    if result["base_loss_reward"] is not None:
        result["status"] = "available"

    return result
