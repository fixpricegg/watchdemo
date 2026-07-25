from demoparser2 import DemoParser
from missed_trade import get_possible_missed_trades
from report import generate_report
import radar
import draw_radar
import json
import pandas as pd


def clean_deaths(df):
    if "weapon" in df.columns:
        df = df[df["weapon"].fillna("").str.lower() != "world"]

    df = df[
        ~df["attacker_name"].fillna("").str.lower().eq("world") &
        ~df["user_name"].fillna("").str.lower().eq("world")
    ]

    return df


def format_time_left(ticks, round_time=115, tickrate=64):
    if ticks is None:
        return "нет данных"

    seconds_passed = ticks / tickrate
    seconds_left = int(round_time - seconds_passed)

    if seconds_left < 0:
        seconds_left = 0

    minutes = seconds_left // 60
    seconds = seconds_left % 60

    return f"{minutes}:{seconds:02d}"


def get_game_ticks_between(start_tick, event_tick, live_ticks_df):
    if live_ticks_df is None:
        return max(0, event_tick - start_tick)

    ticks_in_range = live_ticks_df[
        (live_ticks_df["tick"] >= start_tick) &
        (live_ticks_df["tick"] <= event_tick)
    ]
    return ticks_in_range["tick"].nunique()

def safe_parse_event(parser, event_name):
    try:
        result = parser.parse_event(event_name)

        if isinstance(result, pd.DataFrame):
            return result

        if result is None:
            return pd.DataFrame()

        return pd.DataFrame(result)

    except Exception as e:
        print(f"WARNING: не удалось прочитать event {event_name}: {e}")
        return pd.DataFrame()

def create_event(
    event_type,
    category,
    round_number,
    tick=None,
    time=None,
    importance=1,
    title=None,
    description="",
    data=None,
):
    return {
        "type": event_type,
        "category": category,
        "round": int(round_number),
        "tick": int(tick) if tick is not None else None,
        "time": time,
        "importance": int(importance),
        "title": title or event_type,
        "description": description,
        "data": data or {}
    }

def get_player_team(steamid, team_by_steamid):
    if pd.isna(steamid):
        return None

    steamid = int(steamid)
    return team_by_steamid.get(steamid)


def get_match_start_tick(parser):
    begin_new_match = safe_parse_event(
        parser,
        "begin_new_match"
    )

    if (
        not begin_new_match.empty
        and "tick" in begin_new_match.columns
    ):
        ticks = (
            begin_new_match["tick"]
            .dropna()
            .astype(int)
            .tolist()
        )

        if ticks:
            return max(ticks)

    announce_match_start = safe_parse_event(
        parser,
        "round_announce_match_start"
    )

    if (
        not announce_match_start.empty
        and "tick" in announce_match_start.columns
    ):
        ticks = (
            announce_match_start["tick"]
            .dropna()
            .astype(int)
            .tolist()
        )

        if ticks:
            return max(ticks)

    return None

def score_low_impact(kd, entry_kills, entry_deaths, entry_success):
    entry_total = entry_kills + entry_deaths

    if kd >= 0.9:
        return 0

    if entry_kills < 3:
        if kd < 0.7:
            return 3
        return 2

    if entry_success is not None and entry_success < 50:
        if kd < 0.7:
            return 3
        return 2

    return 0


def score_early_death(avg_time_first_death, entry_deaths, deaths_count):
    if avg_time_first_death is None or deaths_count == 0:
        return 0

    if avg_time_first_death < 1600 and entry_deaths >= deaths_count * 0.30:
        return 3
    elif avg_time_first_death < 2240 and entry_deaths >= deaths_count * 0.27:
        return 2
    else:
        return 0


def score_entry_success(entry_kills, entry_deaths):
    entry_total = entry_kills + entry_deaths

    if entry_total < 5:
        return 0

    success = entry_kills / entry_total

    if success < 0.40:
        return 3
    elif success < 0.50:
        return 2
    else:
        return 0


def score_passive_play(entry_kills, entry_deaths, avg_time_first_kill):
    entry_total = entry_kills + entry_deaths

    if entry_total < 3:
        return 0

    if avg_time_first_kill is None:
        return 0

    if entry_total <= 3 and avg_time_first_kill >= 4160:
        return 3
    elif entry_total <= 4 and avg_time_first_kill >= 3840:
        return 2
    else:
        return 0


def score_hs(hs_rate):
    if hs_rate is None:
        return 0

    if hs_rate < 0.25:
        return 3
    elif hs_rate < 0.30:
        return 2
    else:
        return 0


demo_path = "demos/match18cache.dem"
player = "StRoGo"

parser = DemoParser(demo_path)

map_name = radar.get_map_name(parser)

print()
print("MAP:")
print(map_name)
pd.set_option("display.max_columns", None)

player_info = parser.parse_player_info()

team_by_steamid = {
    int(row["steamid"]): int(row["team_number"])
    for _, row in player_info.iterrows()
}


# =========================
# 1. Tick-level state
# =========================
try:
    tick_df = parser.parse_ticks([
        "tick",
        "is_freeze_period",
        "is_technical_timeout",
        "is_waiting_for_resume",
        "is_ct_timeout",
        "is_terrorist_timeout"
    ])

    live_ticks = tick_df[
        (~tick_df["is_freeze_period"]) &
        (~tick_df["is_technical_timeout"]) &
        (~tick_df["is_waiting_for_resume"]) &
        (~tick_df["is_ct_timeout"]) &
        (~tick_df["is_terrorist_timeout"])
    ]

    live_ticks = live_ticks[["tick"]].drop_duplicates().sort_values("tick")

except Exception as e:
    print("WARNING: parse_ticks сломался, тайминги будут считаться без фильтра пауз.")
    print("parse_ticks error:", e)
    live_ticks = None

# =========================
# 2. Deaths
# =========================
deaths = parser.parse_event("player_death")

if deaths.empty:
    print("В демке не найдено событий player_death.")
    exit()

deaths = clean_deaths(deaths)

# Отдельная копия для kill feed.
# Здесь сохраняются в том числе убийства ножом.
deaths_for_kill_feed = deaths.copy()

if "weapon" in deaths.columns:
    knife_weapons = [
        "knife",
        "knife_t",
        "knife_gg",
        "bayonet",
        "knife_css",
        "knife_flip",
        "knife_gut",
        "knife_karambit",
        "knife_m9_bayonet",
        "knife_tactical",
        "knife_falchion",
        "knife_survival_bowie",
        "knife_butterfly",
        "knife_push"
    ]
    deaths = deaths[~deaths["weapon"].isin(knife_weapons)]

if deaths.empty:
    print("После очистки не осталось игровых смертей.")
    exit()



# =========================
# 3. Round live starts через round_freeze_end
# =========================
round_live_starts = parser.parse_event("round_freeze_end")

round_starts = parser.parse_event("round_prestart")

round_ends = safe_parse_event(parser, "round_end")

# Реальный конец демки нельзя определять
# по последнему убийству.
demo_end_tick = None

if (
    "tick_df" in globals()
    and isinstance(tick_df, pd.DataFrame)
    and not tick_df.empty
    and "tick" in tick_df.columns
):
    demo_end_tick = int(
        tick_df["tick"].dropna().max()
    )

elif (
    isinstance(round_ends, pd.DataFrame)
    and not round_ends.empty
    and "tick" in round_ends.columns
):
    demo_end_tick = int(
        round_ends["tick"].dropna().max()
    )

else:
    demo_end_tick = int(
        deaths_for_kill_feed["tick"]
        .dropna()
        .max()
    )

# Core events drive the persistent bomb state. Begin/abort events are retained
# in radar.json for Timeline/debug, but they do not change that state.
bomb_event_names = [
    "bomb_pickup",
    "bomb_dropped",
    "bomb_beginplant",
    "bomb_abortplant",
    "bomb_planted",
    "bomb_begindefuse",
    "bomb_abortdefuse",
    "bomb_defused",
    "bomb_exploded",
]

bomb_event_frames = {
    event_name: safe_parse_event(parser, event_name)
    for event_name in bomb_event_names
}

try:
    grenade_df = parser.parse_grenades()
    grenade_event_names = [
        "flashbang_detonate",
        "hegrenade_detonate",
        "smokegrenade_detonate",
        "smokegrenade_expired",
        "inferno_startburn",
        "inferno_expire",
        "decoy_started",
        "decoy_detonate",
    ]

    grenade_event_frames = {
        event_name: safe_parse_event(parser, event_name)
        for event_name in grenade_event_names
    }

    if not isinstance(grenade_df, pd.DataFrame):
        grenade_df = pd.DataFrame(grenade_df)

except Exception as e:
    print("WARNING: не удалось прочитать гранаты:", e)
    grenade_df = pd.DataFrame()

# =========================
# 3.1 Реальное начало матча
# =========================
match_marker_tick = get_match_start_tick(parser)

prestart_ticks = (
    round_starts["tick"]
    .dropna()
    .astype(int)
    .drop_duplicates()
    .sort_values()
    .tolist()
)

freeze_end_ticks = (
    round_live_starts["tick"]
    .dropna()
    .astype(int)
    .drop_duplicates()
    .sort_values()
    .tolist()
)

if match_marker_tick is not None:
    # Служебные prestart до последнего match-start нам не нужны.
    MATCH_START_TOLERANCE_TICKS = 64

    real_prestart_ticks = [
        tick
        for tick in prestart_ticks
        if tick >= match_marker_tick - MATCH_START_TOLERANCE_TICKS
    ]
else:
    print(
        "WARNING: match_start_tick не найден. "
        "Использую все round_prestart."
    )
    real_prestart_ticks = prestart_ticks

if not real_prestart_ticks:
    raise RuntimeError(
        "Не удалось найти round_prestart после начала матча."
    )

# =========================
# 3.2. Собираем раунды хронологически
# prestart -> ближайший freeze_end -> следующий prestart
# =========================
round_pairs = []

for index, freeze_start_tick in enumerate(real_prestart_ticks):
    if index < len(real_prestart_ticks) - 1:
        next_freeze_start_tick = real_prestart_ticks[index + 1]
    else:
        next_freeze_start_tick = demo_end_tick + 1

    live_candidates = [
        tick
        for tick in freeze_end_ticks
        if freeze_start_tick < tick < next_freeze_start_tick
    ]

    if not live_candidates:
        continue

    live_start_tick = live_candidates[0]

    round_pairs.append({
        "round": len(round_pairs) + 1,
        "demo_round": len(round_pairs) + 1,
        "freeze_start_tick": int(freeze_start_tick),
        "live_start_tick": int(live_start_tick),
        "end_tick": int(next_freeze_start_tick),
    })

if not round_pairs:
    raise RuntimeError(
        "Не удалось сопоставить round_prestart и round_freeze_end."
    )

timeline_rounds = round_pairs

round_intervals = [
    (
        int(round_data["round"]),
        int(round_data["demo_round"]),
        int(round_data["live_start_tick"]),
        int(round_data["end_tick"]),
    )
    for round_data in timeline_rounds
]



# =========================
# 4. Deaths inside live rounds
# =========================
clean_deaths_list = []

for _, death in deaths.iterrows():
    death_tick = death["tick"]

    for match_round, demo_round, start_tick, end_tick in round_intervals:
        if start_tick <= death_tick < end_tick:
            death_copy = death.copy()
            death_copy["round"] = match_round
            death_copy["match_round"] = match_round
            death_copy["demo_round"] = demo_round
            clean_deaths_list.append(death_copy)
            break

deaths_clean = pd.DataFrame(clean_deaths_list)


if deaths_clean.empty:
    print("После фильтрации по live-раундам не осталось смертей.")
    exit()

# =========================
# 4.0.1 Kill feed
# =========================
kill_feed = []

for _, death in deaths_for_kill_feed.sort_values("tick").iterrows():
    death_tick = int(death["tick"])

    kill_round = None

    for match_round, demo_round, start_tick, end_tick in round_intervals:
        if start_tick <= death_tick < end_tick:
            kill_round = int(match_round)
            break

    # Не тащим события разминки и служебные смерти вне реальных раундов.
    if kill_round is None:
        continue

    attacker_name = death.get("attacker_name")
    victim_name = death.get("user_name")

    attacker_steamid = death.get("attacker_steamid")
    victim_steamid = death.get("user_steamid")

    # World, неизвестный источник урона или битая строка.
    if (
        pd.isna(attacker_name)
        or pd.isna(victim_name)
        or pd.isna(attacker_steamid)
        or pd.isna(victim_steamid)
    ):
        continue

    attacker_steamid = int(attacker_steamid)
    victim_steamid = int(victim_steamid)

    # Самоубийства в обычный kill feed пока не выводим.
    if attacker_steamid == victim_steamid:
        continue

    weapon = death.get("weapon")
    headshot = death.get("headshot")
    assister_name = death.get("assister_name")
    assister_steamid = death.get("assister_steamid")

    kill_feed.append({
        "tick": death_tick,
        "round": kill_round,

        "attacker_name": str(attacker_name),
        "attacker_steamid": attacker_steamid,

        "victim_name": str(victim_name),
        "victim_steamid": victim_steamid,

        "weapon": (
            str(weapon)
            if not pd.isna(weapon)
            else "unknown"
        ),

        "headshot": (
            bool(headshot)
            if not pd.isna(headshot)
            else False
        ),

        "assister_name": (
            str(assister_name)
            if not pd.isna(assister_name)
            else None
        ),

        "assister_steamid": (
            int(assister_steamid)
            if not pd.isna(assister_steamid)
            else None
        ),
    })

print(f"KILL FEED EVENTS: {len(kill_feed)}")

# =========================
# 4.1 Positions
# =========================
try:
    position_df = parser.parse_ticks([
        "tick",
        "name",
        "steamid",
        "X",
        "Y",
        "Z",
        "yaw",
        "health",
        "armor",
        "has_helmet",
        "active_weapon_name",
        "is_alive",
        "team_num",
        "inventory",
        "is_bomb_dropped",
        "is_bomb_planted",
    ])
except Exception as e:
    print("POSITION PARSE WITH TEAM ERROR:", e)
    print("Пробую прочитать позиции без team_num.")

    position_df = parser.parse_ticks([
        "tick",
        "name",
        "steamid",
        "X",
        "Y",
        "Z",
        "yaw",
        "health",
        "armor",
        "has_helmet",
        "active_weapon_name",
        "is_alive",
        "inventory",
        "is_bomb_dropped",
        "is_bomb_planted",
    ])

    position_df["team_num"] = None

# =========================
# 4.1.1 Timeline score
# =========================
player_team_rows = (
    position_df[
        (position_df["name"] == player) &
        (position_df["team_num"].notna())
    ][["tick", "team_num"]]
    .drop_duplicates()
    .sort_values("tick")
    .reset_index(drop=True)
)


def get_player_side_at_tick(target_tick):
    if player_team_rows.empty:
        return None

    rows_before_tick = player_team_rows[
        player_team_rows["tick"] <= target_tick
    ]

    if not rows_before_tick.empty:
        return int(rows_before_tick.iloc[-1]["team_num"])

    rows_after_tick = player_team_rows[
        player_team_rows["tick"] > target_tick
    ]

    if not rows_after_tick.empty:
        return int(rows_after_tick.iloc[0]["team_num"])

    return None


player_team_score = 0
enemy_team_score = 0

for timeline_round in timeline_rounds:
    live_start_tick = int(timeline_round["live_start_tick"])
    end_tick = int(timeline_round["end_tick"])

    player_side_number = get_player_side_at_tick(live_start_tick)

    if player_side_number == 3:
        timeline_round["ct_score"] = int(player_team_score)
        timeline_round["t_score"] = int(enemy_team_score)
        player_side_name = "CT"

    elif player_side_number == 2:
        timeline_round["ct_score"] = int(enemy_team_score)
        timeline_round["t_score"] = int(player_team_score)
        player_side_name = "T"

    else:
        timeline_round["ct_score"] = int(player_team_score)
        timeline_round["t_score"] = int(enemy_team_score)
        player_side_name = None

    round_result = round_ends[
        (round_ends["tick"] >= live_start_tick) &
        (round_ends["tick"] < end_tick) &
        (round_ends["winner"].notna())
    ].sort_values("tick")

    if round_result.empty or player_side_name is None:
        continue

    winner_side = str(
        round_result.iloc[0]["winner"]
    ).upper()

    if winner_side == player_side_name:
        player_team_score += 1
    elif winner_side in ["CT", "T"]:
        enemy_team_score += 1

# =========================
# 4.2 Radar
# =========================
round_reset_ticks = [
    int(timeline_round["freeze_start_tick"])
    for timeline_round in timeline_rounds
]

radar_match = radar.build_radar_match(
    position_df,
    map_name,
    player_info,
    bomb_event_frames=bomb_event_frames,
    round_reset_ticks=round_reset_ticks,
    grenade_df=grenade_df,
    grenade_event_frames=grenade_event_frames,
)

radar_match["kills"] = kill_feed

# radar.export_radar_json(
#     radar_match,
#     timeline_rounds
# )



test_tick = 100000

# draw_radar.build_frame(
#     radar_match,
#     50000
# )
#
# draw_radar.build_frame(
#     radar_match,
#     100000
# )
#
# draw_radar.build_frame(
#     radar_match,
#     150000
# )



# =========================
# 5. Player stats
# =========================
events = []

missed_trade_events = []

if position_df is not None:
    missed_trade_events = get_possible_missed_trades(
        player,
        deaths_clean,
        player_info,
        position_df
    )

player_kills = deaths_clean[deaths_clean["attacker_name"] == player]
player_deaths = deaths_clean[deaths_clean["user_name"] == player]

kills_count = len(player_kills)
deaths_count = len(player_deaths)

if deaths_count > 0:
    kd = kills_count / deaths_count
else:
    kd = float(kills_count)

if "headshot" in player_kills.columns and kills_count > 0:
    headshots = player_kills[player_kills["headshot"] == True]
    hs_rate = len(headshots) / kills_count
else:
    hs_rate = None

# =========================
# 5.1 Multi-kills
# =========================
if not player_kills.empty and "round" in player_kills.columns:
    kills_by_round = player_kills.groupby("round").size()

    two_k = int((kills_by_round == 2).sum())
    three_k = int((kills_by_round == 3).sum())
    four_k = int((kills_by_round == 4).sum())
    ace = int((kills_by_round >= 5).sum())

    multi_kills = int((kills_by_round >= 2).sum())
    for round_number, kills_in_round in kills_by_round.items():

        if kills_in_round < 2:
            continue

        importance = 1

        if kills_in_round == 3:
            importance = 2
        elif kills_in_round == 4:
            importance = 3
        elif kills_in_round >= 5:
            importance = 4

        events.append(
            create_event(
                event_type="multi_kill",
                category="positive",
                round_number=round_number,
                importance=importance,
                title=f"{int(kills_in_round)}K round",
                description=f"Ты сделал {int(kills_in_round)} убийства в раунде.",
                data={
                    "kills": int(kills_in_round)
                }
            )
        )
else:
    two_k = 0
    three_k = 0
    four_k = 0
    ace = 0
    multi_kills = 0

# =========================
# 5.2 Missed trades
# =========================


print("\nMISSED TRADES:")
print(missed_trade_events)

for missed_trade in missed_trade_events:
    events.append(
        create_event(
            event_type="missed_trade",
            category="negative",
            round_number=missed_trade["round"],
            tick=missed_trade["tick"],
            importance=2,
            title="Missed Trade",
            description=(
                f"После смерти {missed_trade['dead_teammate']} "
                f"у тебя мог быть размен. "
                f"{missed_trade['killer']} оставался жив ещё "
                f"{missed_trade['killer_alive_ticks'] / 64:.1f} сек."
            ),
            data=missed_trade
        )
    )

# =========================
# 5.3 Trade kills
# =========================
TRADE_WINDOW_TICKS = 4 * 64

trade_kills_count = 0

for _, kill in player_kills.iterrows():

    kill_tick = int(kill["tick"])
    kill_round = int(kill["round"])

    player_team = get_player_team(
        kill["attacker_steamid"],
        team_by_steamid
    )

    if player_team is None:
        continue

    recent_deaths = deaths_clean[
        (deaths_clean["round"] == kill_round) &
        (deaths_clean["tick"] < kill_tick) &
        (kill_tick - deaths_clean["tick"] <= TRADE_WINDOW_TICKS)
        ].sort_values("tick", ascending=False)

    for _, death in recent_deaths.iterrows():

        dead_teammate_team = get_player_team(
            death["user_steamid"],
            team_by_steamid
        )

        killer_team = get_player_team(
            death["attacker_steamid"],
            team_by_steamid
        )

        if dead_teammate_team != player_team:
            continue

        if killer_team == player_team:
            continue

        if (
                pd.isna(kill["user_steamid"])
                or pd.isna(death["attacker_steamid"])
        ):
            continue

        killed_enemy_steamid = int(kill["user_steamid"])
        previous_killer_steamid = int(death["attacker_steamid"])

        if killed_enemy_steamid != previous_killer_steamid:
            continue

        events.append(
            create_event(
                event_type="trade_kill",
                category="positive",
                round_number=kill_round,
                tick=kill_tick,
                importance=2,
                title="Trade Kill",
                description=f"Ты быстро разменял погибшего тиммейта {death['user_name']}.",
                data={
                    "traded_teammate": death["user_name"],
                    "enemy": kill["user_name"]
                }
            )
        )
        trade_kills_count += 1

        break

print("\n== TRADE DEBUG ==")
print(f"Trade kills: {trade_kills_count}")

print("\n== TRADE EVENTS ==")

for event in events:
    if event["type"] == "trade_kill":
        print(
            f"Round {event['round']} | "
            f"{event['data']['traded_teammate']} traded"
        )





# =========================
# 5.4. Entry + timing + events
# =========================
entry_kills = 0
entry_deaths = 0
first_kill_times = []
first_death_times = []

for match_round, demo_round, live_start_tick, live_end_tick in round_intervals:
    round_kills = deaths_clean[
        (deaths_clean["tick"] >= live_start_tick) &
        (deaths_clean["tick"] < live_end_tick)
    ]

    if round_kills.empty:
        continue

    first_kill = round_kills.loc[round_kills["tick"].idxmin()]

    game_ticks_to_first_event = get_game_ticks_between(
        int(live_start_tick),
        int(first_kill["tick"]),
        live_ticks
    )

    if first_kill["attacker_name"] == player:
        entry_kills += 1
        first_kill_times.append(game_ticks_to_first_event)

    if first_kill["user_name"] == player:
        entry_deaths += 1
        first_death_times.append(game_ticks_to_first_event)

        event_type = "early_death"
        importance = 2

        if game_ticks_to_first_event < 1600:
            event_type = "failed_entry"
            importance = 3

        events.append(
            create_event(
                event_type=event_type,
                category="negative",
                round_number=match_round,
                tick=first_kill["tick"],
                time=format_time_left(game_ticks_to_first_event),
                importance=importance,
                title="Провальный entry" if event_type == "failed_entry" else "Ранняя смерть",
                description="Ты умер первым в раунде и оставил команду в меньшинстве.",
                data={
                    "killer": first_kill["attacker_name"],
                    "victim": first_kill["user_name"],
                    "demo_round": int(demo_round),
                }
            )
        )

# =========================
# 6. Averages
# =========================
avg_time_first_kill = (
    sum(first_kill_times) / len(first_kill_times)
    if first_kill_times else None
)

avg_time_first_death = (
    sum(first_death_times) / len(first_death_times)
    if first_death_times else None
)

entry_total = entry_kills + entry_deaths
entry_success = (
    entry_kills / entry_total * 100
    if entry_total > 0 else None
)

# =========================
# 7. Scoring
# =========================
low_impact_score = score_low_impact(
    kd,
    entry_kills,
    entry_deaths,
    entry_success
)

early_score = score_early_death(
    avg_time_first_death,
    entry_deaths,
    deaths_count
)

entry_score = score_entry_success(entry_kills, entry_deaths)
passive_score = score_passive_play(entry_kills, entry_deaths, avg_time_first_kill)
hs_score = score_hs(hs_rate)

problems = [
    {
        "name": "Низкий Impact",
        "score": low_impact_score,
        "description": "Ты редко выигрываешь дуэли и слабо влияешь на ход раундов. При таком K/D ты чаще теряешь преимущество, чем создаёшь его для команды.",
        "advice": [
            "Не принимать лишние дуэли без преимущества",
            "Играть ближе к тиммейтам, чтобы тебя могли разменять",
            "Выбирать позиции, где легче забрать первый контакт или отойти после него",
            "Не играть слишком пассивно, если команда уже создаёт пространство"
        ]
    },
    {
        "name": "Ранние смерти",
        "score": early_score,
        "description": "Ты часто умираешь одним из первых в начале раунда, не успевая внести импакт и оставляя команду в меньшинстве.",
        "advice": [
            "Не занимать агрессивные позиции без флешек или поддержки тиммейтов",
            "Играть от информации: не пикать без понимания позиций противника",
            "Учить базовые тайминги карты",
            "Улучшать кроссхейр-плейсмент, чтобы выигрывать первые дуэли",
            "Стараться играть в размен, а не в одиночные выходы"
        ]
    },
    {
        "name": "Низкий Entry Success",
        "score": entry_score,
        "description": "Ты чаще умираешь при попытке сделать первый фраг, чем приносишь команде преимущество.",
        "advice": [
            "Не выходить первым без подготовки",
            "Играть entry только при поддержке тиммейтов",
            "Избегать очевидных позиций, где тебя ждут",
            "Тренировать первые выстрелы и кроссхейр-плейсмент"
        ]
    },
    {
        "name": "Пассивная игра",
        "score": passive_score,
        "description": "Ты редко участвуешь в первых контактах и чаще вступаешь в игру на поздних таймингах раунда.",
        "advice": [
            "Чаще участвовать в первых разменах вместе с командой",
            "Использовать флешки и помощь тиммейтов для безопасного выхода",
            "В отдельных раундах брать инициативу и искать первый контакт"
        ]
    },
    {
        "name": "Низкий HS%",
        "score": hs_score,
        "description": "Ты редко делаешь убийства в голову, это говорит о проблемах с кроссхейр-плейсментом и первыми выстрелами.",
        "advice": [
            "Тренировать кроссхейр-плейсмент",
            "Изучать стандартные позиции противников и заранее наводиться на них",
            "Играть префаер-карты для закрепления паттернов стрельбы"
        ]
    },
]

top_problems = sorted(problems, key=lambda x: x["score"], reverse=True)
top_problems = [p for p in top_problems if p["score"] >= 2][:3]

# =========================
# 8. Stats for report.py
# =========================
stats = {
    "kd": kd,
    "kills": kills_count,
    "two_k": two_k,
    "three_k": three_k,
    "four_k": four_k,
    "ace": ace,
    "multi_kills": multi_kills,
    "trade_kills": trade_kills_count,
    "deaths": deaths_count,
    "hs_rate": hs_rate,
    "entry_kills": entry_kills,
    "entry_deaths": entry_deaths,
    "entry_success": entry_success,
    "avg_time_first_kill": avg_time_first_kill,
    "avg_time_first_death": avg_time_first_death,
    "top_problems": top_problems,
    "events": events,
}

# =========================
# 8.1 Report JSON for frontend
# =========================
report_data = {
    "player": player,
    "map": map_name,
    "summary": {
        "kills": int(kills_count),
        "deaths": int(deaths_count),
        "kd": round(float(kd), 2),
        "hs_rate": round(float(hs_rate) * 100, 1) if hs_rate is not None else None,
        "entry_kills": int(entry_kills),
        "entry_deaths": int(entry_deaths),
        "entry_success": round(float(entry_success), 1) if entry_success is not None else None,
        "trade_kills": int(trade_kills_count),
        "multi_kills": int(multi_kills),
        "two_k": int(two_k),
        "three_k": int(three_k),
        "four_k": int(four_k),
        "ace": int(ace),
    },
    "top_problems": top_problems
}

with open("report.json", "w", encoding="utf-8") as f:
    json.dump(
        report_data,
        f,
        ensure_ascii=False,
        indent=2
    )

print("Frontend report сохранён в report.json")

# =========================
# 9. Console output
# =========================
print("\n==| WATCHDEMO REPORT |==")
print(f"Player: {player}\n")

print("==| TOP PROBLEMS |==")
for i, p in enumerate(top_problems, start=1):
    print(f"{i}. {p['name']} (score: {p['score']})")

print("\n==| COMBAT |==")
print(f"K/D: {kd:.2f}")
print(f"Kills: {kills_count}")
print(f"Deaths: {deaths_count}")

print("\n==| AIM |==")
if hs_rate is not None:
    print(f"HS%: {hs_rate * 100:.1f}")
else:
    print("HS%: нет данных")

print("\n==| ENTRY |==")
print(f"Entry kills: {entry_kills}")
print(f"Entry deaths: {entry_deaths}")
if entry_success is not None:
    print(f"Entry success %: {entry_success:.0f}%")
else:
    print("Entry success %: нет данных")

print("\n==| TIMING |==")
if avg_time_first_kill is not None:
    print(f"Средний тайминг опен-килла: {format_time_left(avg_time_first_kill)}")
else:
    print("Среднее время опен-килла: нет данных")

if avg_time_first_death is not None:
    print(f"Средний тайминг первой смерти: {format_time_left(avg_time_first_death)}")
else:
    print("Среднее время первой смерти: нет данных")

print("\n==| EVENTS |==")
print(f"Events found: {len(events)}")

print("\n==| MULTI-KILLS |==")
print(f"2K rounds: {two_k}")
print(f"3K rounds: {three_k}")
print(f"4K rounds: {four_k}")
print(f"Ace rounds: {ace}")
print(f"Multi-kill rounds: {multi_kills}\n")


# =========================
# 10. Save markdown report
# =========================
report_text = generate_report(player, stats)

with open("report.md", "w", encoding="utf-8") as f:
    f.write(report_text)

print("\nОтчёт сохранён в report.md")

radar.export_radar_json(
    radar_match,
    timeline_rounds,
    events
)