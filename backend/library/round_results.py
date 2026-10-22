
import pandas as pd


def build_round_results(round_intervals, round_ends):
    """
    Build ground-truth round results.

    round_intervals:
        (match_round, demo_round, live_start_tick, end_tick)

    round_ends:
        DataFrame with tick and winner columns.

    No winner is invented for missing events.
    """

    results = []

    if not isinstance(round_ends, pd.DataFrame):
        round_ends = pd.DataFrame()

    required = {"tick", "winner"}

    if required.issubset(round_ends.columns):
        events = round_ends.copy()
        events["tick"] = pd.to_numeric(
            events["tick"], errors="coerce"
        )
        events = events.dropna(subset=["tick"])
        events = events.sort_values("tick")
    else:
        events = pd.DataFrame(
            columns=["tick", "winner"]
        )

    for match_round, demo_round, start, end in round_intervals:
        start = int(start)
        end = int(end)

        matching = events[
            (events["tick"] >= start) &
            (events["tick"] < end)
        ]

        winner = None
        result_tick = None

        for _, event in matching.iterrows():
            candidate = str(event["winner"]).upper()

            if candidate in ("T", "CT"):
                winner = candidate
                result_tick = int(event["tick"])
                break

        results.append({
            "round": int(match_round),
            "demo_round": int(demo_round),
            "live_start_tick": start,
            "end_tick": end,
            "result_tick": result_tick,
            "winner_side": winner,
            "loser_side": (
                "CT" if winner == "T"
                else "T" if winner == "CT"
                else None
            ),
            "status": (
                "finished" if winner is not None
                else "unknown"
            ),
        })

    return results
