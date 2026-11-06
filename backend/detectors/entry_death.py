"""Opening deaths are observed events, never automatic verdicts on decisions."""
import pandas as pd

from information import normalize_steamid


def enemy_deaths(deaths, library):
    """Use event-time sides, including halftime; never final scoreboard sides."""
    required = {"tick", "round", "user_steamid", "attacker_steamid"}
    if not required.issubset(deaths.columns):
        return deaths.iloc[:0].copy()
    rows = []
    for _, row in deaths.iterrows():
        victim = normalize_steamid(row["user_steamid"])
        killer = normalize_steamid(row["attacker_steamid"])
        if victim in (None, "0") or killer in (None, "0") or victim == killer:
            continue
        sides = [row.get("user_team_num"), row.get("attacker_team_num")]
        sides = [None if pd.isna(side) else side for side in sides]
        if not all(side in (2, 3) for side in sides):
            try:
                state = library.get_game_state(int(row["tick"]), victim)
            except (ValueError, TypeError, OverflowError):
                continue
            players = {p["steamid"]: p for p in state["ground_truth"]["players"]}
            sides = [players.get(sid, {}).get("team") for sid in (victim, killer)]
        if sides[0] not in (2, 3) or sides[1] not in (2, 3) or sides[0] == sides[1]:
            continue
        copy = row.copy()
        copy["user_team_num"], copy["attacker_team_num"] = sides
        rows.append(copy)
    return pd.DataFrame(rows, columns=list(dict.fromkeys([
        *deaths.columns, "user_team_num", "attacker_team_num",
    ]))).sort_values("tick", kind="stable")


def round_observation_end(library, number, fallback):
    """A complete window cannot extend past the winner event into post-round time."""
    result = next((r for r in getattr(library, "round_results", [])
                   if r["round"] == number), {})
    tick = result.get("result_tick")
    return min(fallback, int(tick)) if tick is not None else fallback


def detect_entry_deaths(library, player, deaths, *, trade_window_ticks=256):
    if not library.death_data_complete:
        return []
    combat = enemy_deaths(deaths, library)
    findings = []
    for number, _, start, end in library.round_intervals:
        end = round_observation_end(library, number, end)
        events = combat[(combat["round"] == number) &
                        (combat["tick"] >= start) & (combat["tick"] < end)]
        if events.empty:
            continue
        first_tick = int(events["tick"].min())
        try:
            state = library.get_game_state(first_tick, player)
        except ValueError:
            continue
        player_id = state["perspective"]["steamid"]
        opening = events[events["tick"] == first_tick]
        deaths_of_player = opening[opening["user_steamid"].map(normalize_steamid) == player_id]
        if deaths_of_player.empty:
            continue
        death = deaths_of_player.iloc[0]
        killer_id = normalize_steamid(death["attacker_steamid"])
        trades = events[(events["tick"] >= first_tick) &
                        (events["tick"] <= first_tick + trade_window_ticks) &
                        (events["user_steamid"].map(normalize_steamid) == killer_id)]
        traded = True if not trades.empty else (
            False if first_tick + trade_window_ticks < end else None
        )
        findings.append({
            "type": "entry_death_candidate", "detector_version": 1,
            "status": "review_required", "verdict": "not_evaluated",
            "round": int(number), "tick": first_tick,
            "player_steamid": player_id, "killer_steamid": killer_id,
            "killer": death.get("attacker_name"),
            "seconds_from_live_start": round((first_tick - start) / 64, 2),
            "simultaneous_opening_deaths": len(opening),
            "traded_within_window": traded,
            "trade_tick": int(trades.iloc[0]["tick"]) if not trades.empty else None,
            "trade_window_ticks": trade_window_ticks,
            "evidence_scope": "post_match_ground_truth",
            "limitations": [
                "Первая смерть подтверждена событием, но не доказывает ошибку выхода.",
                "Исход размена известен после эпизода и не является знанием игрока до решения.",
            ],
        })
    return findings
