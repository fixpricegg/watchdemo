
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
