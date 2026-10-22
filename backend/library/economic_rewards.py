"""Event-attributed nominal awards, never counter deltas or cash income.

Defaults: CS2 competitive after 2024-04-25. Historical demos and server
overrides require an explicit RewardRules profile. All outputs are ground truth.
"""
from dataclasses import dataclass, field
from copy import deepcopy
import math
import re
import pandas as pd
from information import normalize_steamid

KILL_REWARD_FIELD = (
    "CCSPlayerController.CCSPlayerController_ActionTrackingServices."
    "CSPerRoundStats_t.m_iKillReward"
)

# Valve 2024-04-25: CZ75 100 -> 300, XM1014 900 -> 600, Zeus 0 -> 100.
WEAPON_REWARDS = {
    **dict.fromkeys((
        "ak47", "aug", "famas", "galilar", "m4a1", "m4a1_silencer",
        "sg556", "ssg08", "scar20", "g3sg1", "m249", "negev",
        "glock", "hkp2000", "usp_silencer", "p250", "deagle", "elite",
        "tec9", "fiveseven", "cz75a", "revolver", "p90", "hegrenade",
        "molotov", "incgrenade", "inferno", "smokegrenade", "flashbang", "decoy",
    ), 300),
    **dict.fromkeys(("mac10", "mp9", "mp7", "mp5sd", "ump45", "bizon"), 600),
    **dict.fromkeys(("nova", "mag7", "sawedoff"), 900),
    "xm1014": 600, "awp": 100, "taser": 100, "knife": 1500,
}
ALIASES = {
    "m4a4": "m4a1", "m4a1s": "m4a1_silencer", "usps": "usp_silencer",
    "usp": "usp_silencer", "p2000": "hkp2000", "glock18": "glock",
    "deserteagle": "deagle", "dualberettas": "elite", "cz75auto": "cz75a",
    "cz75": "cz75a", "r8revolver": "revolver", "sg553": "sg556",
    "galil": "galilar", "ppbizon": "bizon", "zeusx27": "taser", "zeus": "taser",
    "incendiarygrenade": "incgrenade",
}
KNIVES = {
    "knife", "knife_t", "knife_gg", "bayonet", "knife_css", "knife_flip",
    "knife_gut", "knife_karambit", "knife_m9_bayonet", "knife_tactical",
    "knife_falchion", "knife_survival_bowie", "knife_butterfly", "knife_push",
    "knife_cord", "knife_canis", "knife_ursus", "knife_gypsy_jackknife",
    "knife_outdoor", "knife_stiletto", "knife_widowmaker", "knife_skeleton", "knife_kukri",
}


def normalize_weapon(value):
    if value is None or pd.isna(value):
        return None
    token = str(value).strip().lower().removeprefix("weapon_")
    if token in KNIVES:
        return "knife"
    compact = re.sub(r"[\s_-]", "", token)
    return ALIASES.get(compact, next(
        (key for key in WEAPON_REWARDS if key.replace("_", "") == compact), token
    ))


@dataclass(frozen=True)
class RewardRules:
    profile: str = "cs2_competitive_post_2024_04_25"
    confirmed: bool = False  # Does not claim that server convars were observed.
    player_cash_awards: bool = True
    enemy_factor: float = 1.0
    teamkill_penalty: int = -300
    weapon_rewards: dict = field(default_factory=lambda: dict(WEAPON_REWARDS))

    def __post_init__(self):
        if not math.isfinite(self.enemy_factor) or self.enemy_factor < 0:
            raise ValueError("enemy_factor must be finite and nonnegative")
        if self.teamkill_penalty > 0:
            raise ValueError("teamkill_penalty must be nonpositive")
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
               for v in self.weapon_rewards.values()):
            raise ValueError("weapon awards must be nonnegative integers")


def _int(value):
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number.is_integer() else None
    except (ValueError, TypeError, OverflowError):
        return None


def _identity(value):
    if isinstance(value, bool):
        return None
    try:
        normalized = normalize_steamid(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return normalized if normalized is not None and int(normalized) > 0 else None


def _team(value):
    if isinstance(value, str) and value.upper() in ("T", "CT"):
        return 2 if value.upper() == "T" else 3
    value = _int(value)
    return value if value in (2, 3) else None


def build_kill_reward_events(deaths_df, round_intervals, *, rules=None, current_tick=None):
    """Use the full death stream, including knives. Teams must be event-time facts.

    Exact duplicates are removed; conflicting records for one victim/tick stay
    uncertain. Warmup, freeze and future events are excluded.
    """
    rules = rules or RewardRules()
    if not isinstance(deaths_df, pd.DataFrame) or "tick" not in deaths_df:
        return []
    events, seen, victim_keys = [], set(), {}
    for row in deaths_df.to_dict("records"):
        tick = _int(row.get("tick"))
        if tick is None or (current_tick is not None and tick > int(current_tick)):
            continue
        interval = next((r for r in round_intervals if int(r[2]) <= tick < int(r[3])), None)
        if interval is None:
            continue
        attacker = _identity(row.get("attacker_steamid"))
        victim = _identity(row.get("user_steamid"))
        weapon = normalize_weapon(row.get("weapon"))
        at, vt = _team(row.get("attacker_team_num")), _team(row.get("user_team_num"))
        key = (tick, attacker, victim, weapon, at, vt)
        if key in seen:
            continue
        seen.add(key)
        kind, reason, amount, penalty = "unknown", None, None, None
        if attacker is None:
            kind = "world" if weapon in ("world", "worldspawn", "trigger_hurt", "planted_c4", "c4") else "unattributed"
            reason = "no_player_attacker"
            amount = 0 if kind == "world" else None
        elif victim is None:
            reason = "missing_victim_identity"
        elif attacker == victim:
            kind, amount, penalty = "suicide", 0, 0
        elif weapon in ("world", "worldspawn", "trigger_hurt", "planted_c4", "c4"):
            kind, amount, penalty = "world", 0, 0
        elif at is None or vt is None:
            reason = "missing_event_team"
        elif at == vt:
            kind, amount = "teamkill", 0
            penalty = (rules.teamkill_penalty if rules.player_cash_awards else 0) if rules.profile != "unknown" else None
        else:
            kind = "enemy_kill"
            if rules.profile == "unknown":
                reason = "unknown_rules"
            elif not rules.player_cash_awards:
                amount = 0
            elif weapon not in rules.weapon_rewards:
                reason = "unknown_weapon"
            else:
                amount, penalty = int(rules.weapon_rewards[weapon] * rules.enemy_factor), 0
        event = {
            "tick": tick, "round": int(interval[0]), "attacker_steamid": attacker,
            "victim_steamid": victim, "attacker_team": at, "victim_team": vt,
            "weapon": weapon, "kind": kind, "nominal_reward": amount,
            "nominal_penalty": penalty, "actual_income": None, "reason": reason,
            "status": "rule_derived" if amount is not None else "unknown",
            "source": "player_death", "rules_profile": rules.profile,
            "rules_confirmed": rules.confirmed,
        }
        events.append(event)
        if victim is not None:
            victim_keys.setdefault((tick, victim), []).append(event)
    for conflicts in victim_keys.values():
        if len(conflicts) > 1:
            for event in conflicts:
                event.update(kind="unknown", status="unknown", nominal_reward=None,
                             nominal_penalty=None, reason="conflicting_death_events")
    return sorted(events, key=lambda e: (e["tick"], e["attacker_steamid"] or "", e["victim_steamid"] or ""))


def build_round_kill_rewards(deaths_df, round_intervals, *, player_ids=(),
                             current_tick=None, rules=None, death_data_complete=True):
    """Index by (SteamID, round). Current round returns only the as-of prefix.

    Cash caps, simultaneous transactions, bot control and server plugins prevent
    an actual-income claim. Bomb/team/loss money and penalties are separate.
    Missing events are never represented as confirmed zero.
    """
    rules = rules or RewardRules()
    required = {"tick", "attacker_steamid", "user_steamid"}
    valid = isinstance(deaths_df, pd.DataFrame) and required.issubset(deaths_df.columns)
    complete = bool(death_data_complete and valid)
    # An event with no usable timestamp could belong anywhere in the prefix.
    if valid and any(_int(t) is None for t in deaths_df["tick"]):
        complete = False
    intervals = list(round_intervals)
    events = build_kill_reward_events(deaths_df, intervals, rules=rules, current_tick=current_tick)
    roster = {_identity(p) for p in player_ids} - {None}
    roster.update(e["attacker_steamid"] for e in events if e["attacker_steamid"])
    result = {}
    for number, _, start, end in intervals:
        if current_tick is not None and int(start) > int(current_tick):
            continue
        round_events = [e for e in events if e["round"] == int(number)]
        unattributed = sum(e["kind"] == "unattributed" for e in round_events)
        for player_id in sorted(roster):
            own = [e for e in round_events if e["attacker_steamid"] == player_id]
            unknown = sum(e["nominal_reward"] is None for e in own)
            known_amount = sum(e["nominal_reward"] for e in own if e["nominal_reward"] is not None)
            fully_attributed = complete and not unknown and not unattributed
            penalties = [e["nominal_penalty"] for e in own if e["kind"] == "teamkill"]
            result[(player_id, int(number))] = {
                "round": int(number), "steamid": player_id,
                "status": "rule_derived" if fully_attributed else "partial" if valid else "unavailable",
                "source": "player_death_and_weapon_rules", "coverage_complete": complete,
                "unknown_reward_events": unknown, "unattributed_events": unattributed,
                "enemy_kills": sum(e["kind"] == "enemy_kill" for e in own),
                "teamkills": sum(e["kind"] == "teamkill" for e in own),
                "suicides": sum(e["kind"] == "suicide" for e in own),
                "nominal_kill_reward": known_amount if fully_attributed else None,
                "known_nominal_kill_reward": known_amount,
                "nominal_teamkill_penalty": sum(penalties) if all(p is not None for p in penalties) else None,
                "actual_income": None, "actual_income_status": "not_observed",
                "rules_profile": rules.profile, "rules_confirmed": rules.confirmed,
                "through_tick": min(int(end) - 1, int(current_tick)) if current_tick is not None else int(end) - 1,
                "round_complete": current_tick is None or int(current_tick) >= int(end),
                "events": deepcopy(own),
            }
    return result


def calculate_reward_delta(previous, current):
    """Legacy diagnostic arithmetic only; never used for attribution."""
    previous, current = _int(previous), _int(current)
    if previous is None or current is None or previous < 0 or current < previous:
        return None
    return current - previous


def build_kill_reward_history(observations):
    """Raw diagnostics: m_iKillReward is not a cumulative income ledger."""
    return [{
        "tick": item["tick"], "round": item.get("round"),
        "engine_value": _int(item.get("kill_reward")),
        "delta_since_previous_sample": None, "status": "diagnostic_only",
        "actual_income": None, "attribution_status": "unsupported_engine_counter_semantics",
    } for item in sorted(observations, key=lambda item: item["tick"])]
