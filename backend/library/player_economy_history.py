
import pandas as pd

from .game_state import player_from_row


def build_player_economy_history(
    player_stream,
    round_intervals,
    geometry=None,
    current_tick=None,
):
    """
    Ground-truth player economy observations by round.

    Does not infer survival or carried equipment.

    If current_tick is provided, only completed
    rounds and observations up to that tick are used.
    """
    if player_stream is None or player_stream.empty:
        return []

    stream = player_stream.sort_values("tick")
    records = []

    for match_round, demo_round, start, end in round_intervals:
        start = int(start)
        end = int(end)

        if current_tick is not None:
            if end > int(current_tick):
                continue

        rows = stream[
            (stream["tick"] >= start)
            & (stream["tick"] < end)
        ]

        if rows.empty:
            records.append({
                "round": int(match_round),
                "demo_round": int(demo_round),
                "live_start_tick": start,
                "end_tick": end,
                "status": "unavailable",
                "post_buy": None,
                "last_observed": None,
                "carried_equipment": None,
            })
            continue

        first = rows.iloc[0]
        last = rows.iloc[-1]

        first_state = player_from_row(first, geometry)
        last_state = player_from_row(last, geometry)

        def equipment_status(state):
            status = state["status"]

            return {
                "armor": status.get("armor"),
                "has_helmet": status.get("has_helmet"),
                "has_defuser": status.get("has_defuser"),
            }

        # A later sample must not be presented
        # as an exact start-of-round snapshot.
        exact_start = int(first["tick"]) == start

        records.append({
            "round": int(match_round),
            "demo_round": int(demo_round),
            "live_start_tick": start,
            "end_tick": end,
            "status": "available",

            "post_buy": (
                {
                    "sample_tick": start,
                    "economy": first_state["economy"],
                    "inventory": first_state["inventory"],
                    "weapon": first_state["weapon"],
                    "equipment_status": equipment_status(first_state),
                }
                if exact_start else None
            ),

            "first_observed_tick": int(first["tick"]),

            "last_observed": {
                "sample_tick": int(last["tick"]),
                "economy": last_state["economy"],
                "inventory": last_state["inventory"],
                "weapon": last_state["weapon"],
                "is_alive": last_state["status"]["is_alive"],
                "equipment_status": equipment_status(last_state),
            },

            # Requires death events and carry-over validation.
            "carried_equipment": None,
        })

    return records


def get_round_survival(
    player_death_ticks,
    live_start_tick,
    end_tick,
    death_data_complete=False,
):
    """
    Determine survival from player_death events.

    player_death_ticks contains confirmed death ticks
    for ONE player.

    An empty list does not prove survival unless
    the death event dataset is complete.
    """
    if not death_data_complete:
        return {
            "status": "unknown",
            "survived": None,
            "death_tick": None,
        }

    deaths = sorted(
        int(tick)
        for tick in player_death_ticks
        if tick is not None
        and int(live_start_tick) <= int(tick) < int(end_tick)
    )

    if deaths:
        return {
            "status": "died",
            "survived": False,
            "death_tick": deaths[0],
        }

    return {
        "status": "survived",
        "survived": True,
        "death_tick": None,
    }


def get_saved_equipment_candidate(
    record,
    max_age_ticks=16,
):
    """
    Estimate saved equipment from a survivor's
    last observed state.

    This is NOT confirmed carry-over.

    A recent sample is evidence, not proof that
    the inventory stayed unchanged until round end.
    """
    survival = record.get("survival") or {}
    last = record.get("last_observed")

    result = {
        "status": "unknown",
        "source_tick": None,
        "age_ticks": None,
        "inventory": None,
        "equipment_status": None,
        "confidence": "unknown",
    }

    if survival.get("status") == "died":
        result["status"] = "died"
        return result

    if survival.get("status") != "survived":
        return result

    if last is None or record.get("end_tick") is None:
        return result

    source_tick = int(last["sample_tick"])
    end_tick = int(record["end_tick"])

    # end_tick is an exclusive boundary.
    last_possible_tick = end_tick - 1
    age = last_possible_tick - source_tick

    result["source_tick"] = source_tick
    result["age_ticks"] = age

    if age < 0:
        result["status"] = "invalid"
        return result

    if age > max_age_ticks:
        result["status"] = "stale"
        return result

    if last.get("is_alive") is not True:
        result["status"] = "inconsistent"
        return result

    result.update({
        "status": "observed_near_end",
        "inventory": last.get("inventory"),
        "equipment_status": last.get("equipment_status"),
        "confidence": "provisional",
    })

    return result


def build_prebuy_snapshots(parser, round_intervals):
    """
    Read equipment shortly after round_prestart.

    Returns {(round_number, steamid): snapshot}.
    Only zero-spend snapshots qualify as pre-buy.
    """
    from information import normalize_steamid

    events = parser.parse_event("round_prestart")

    if events.empty or "tick" not in events.columns:
        return {}

    prestart_ticks = sorted(
        int(t) for t in events["tick"].dropna()
    )

    sample_to_round = {}

    previous_end = -1

    for match_round, _, live_start, end_tick in round_intervals:
        live_start = int(live_start)

        candidates = [
            t for t in prestart_ticks
            if previous_end <= t < live_start
        ]

        if candidates:
            sample_tick = candidates[-1] + 1

            if sample_tick < live_start:
                sample_to_round[sample_tick] = int(match_round)

        previous_end = int(end_tick)

    if not sample_to_round:
        return {}

    fields = [
        "inventory",
        "team_num",
        "armor",
        "has_helmet",
        "has_defuser",
        "balance",
        "cash_spent_this_round",
        "current_equip_value",
        "round_start_equip_value",
    ]

    df = parser.parse_ticks(
        fields,
        ticks=sorted(sample_to_round),
    )

    snapshots = {}

    for _, row in df.iterrows():
        tick = int(row["tick"])
        round_number = sample_to_round.get(tick)

        if round_number is None:
            continue

        spent = row.get("cash_spent_this_round")

        # Missing spending data is not proof of zero purchases.
        if pd.isna(spent) or float(spent) != 0:
            continue

        steamid = normalize_steamid(row.get("steamid"))

        if steamid is None:
            continue

        state = player_from_row(row)

        snapshots[(round_number, steamid)] = {
            "sample_tick": tick,
            "economy": state["economy"],
            "inventory": state["inventory"],
            "equipment_status": {
                "armor": state["status"]["armor"],
                "has_helmet": state["status"]["has_helmet"],
                "has_defuser": state["status"]["has_defuser"],
            },
            "source": "round_prestart_snapshot",
            "status": "observed_before_spending",
        }

    return snapshots
