"""Match data access: normalized state streams + event-derived team observations.

Construct once per match, query GameState(tick) many times. No DEM reparse per tick.
"""
import pandas as pd
from copy import deepcopy
import information
from .game_state import find_round, player_from_row
from .economy import build_round_economy, build_team_loadout
from .economy import build_round_start_economy
from .economy_history import build_economy_history
from .round_results import build_round_results
from .player_economy_history import build_player_economy_history
from .economic_rewards import RewardRules, build_round_kill_rewards
from .round_state import build_round_state
from .loss_bonus import (
    build_loss_counter_timeline,
    get_loss_counters_at_tick,
    get_next_loss_reward,
    get_loss_reward_for_round,
)
from .match_score import build_perspective_score
from bisect import bisect_right
from .event_timeline import EventTimeline
from copy import deepcopy

from .utility_state import (
    build_player_utility_from_inventory,
    build_team_utility,
)
from .active_utility import build_active_utility


class MatchLibrary:
    def __init__(self, *, map_name, position_df, round_intervals,
                 deaths_df=None, geometry=None, team_observations=None,
                 team_spot_windows=None, max_state_age_ticks=16,
                 round_ends=None,
                 loss_counter_df=None, prebuy_snapshots=None,
                 kill_reward_history=None, economic_reward_rules=None,
                 death_data_complete=True):
        if not {'tick', 'steamid', 'team_num'}.issubset(position_df.columns):
            raise ValueError('position_df requires tick, steamid, team_num')
        self.map_name = str(map_name)
        self.round_intervals = list(round_intervals)
        self.round_results = build_round_results(
            self.round_intervals,
            round_ends,
        )
        self.loss_counter_timeline = (
            build_loss_counter_timeline(loss_counter_df)
            if loss_counter_df is not None
            else []
        )
        self.geometry = geometry
        self.max_state_age_ticks = int(max_state_age_ticks)
        self.position_df = position_df.copy()
        self.position_df['tick'] = pd.to_numeric(self.position_df['tick'], errors='coerce')
        self.position_df = self.position_df.dropna(subset=['tick', 'steamid'])
        self.position_df['tick'] = self.position_df['tick'].astype('int64')
        self.position_df = self.position_df.sort_values('tick')
        # Index by player so repeated queries do not scan unrelated players.
        self.player_streams = {}
        for steamid, stream in self.position_df.groupby('steamid', sort=False):
            normalized = information.normalize_steamid(steamid)
            if normalized is not None:
                self.player_streams[normalized] = stream
        self.deaths_df = deaths_df
        self.death_data_complete = bool(death_data_complete)
        self.economic_reward_rules = economic_reward_rules or RewardRules()
        self.team_observations = (team_observations if team_observations is not None
                                  else information.build_team_observations(self.position_df, self.round_intervals))
        if team_spot_windows is None:
            spots = information.build_spot_events(self.position_df, self.round_intervals)
            team_spot_windows = information.build_team_spot_windows(spots)
        self.team_spot_windows = team_spot_windows
        self.prebuy_snapshots = (
            prebuy_snapshots
            if prebuy_snapshots is not None
            else {}
        )
        # Legacy counters are diagnostics only and never enter economy history.
        self.engine_kill_reward_diagnostics = (
            kill_reward_history
            if kill_reward_history is not None
            else {}
        )
        self._bomb_states = []
        self._bomb_ticks = []
        self._round_tickrate = None
        self._round_time_seconds = None

    def get_game_state(self, tick, player):
        """Return ground truth separate from team knowledge.

        player is SteamID (preferred) or name. Knowledge never includes future observations.
        Only sampled live-round positions within max_state_age_ticks are current.
        """
        tick = int(tick)
        round_info = find_round(self.round_intervals, tick)
        if round_info is None:
            raise ValueError(f'Tick {tick} is outside live round intervals')
        snapshots = []
        for stream in self.player_streams.values():
            rows = stream[(stream['tick'] <= tick) &
                          (stream['tick'] >= round_info['live_start_tick'])]
            if rows.empty:
                continue
            row = rows.iloc[-1]
            if tick - int(row['tick']) > self.max_state_age_ticks:
                continue
            snapshots.append(player_from_row(row, self.geometry))
        snapshots.sort(key=lambda x: x['steamid'])
        player_id = information.normalize_steamid(player)
        perspective = next((p for p in snapshots if p['steamid'] == player_id or p['name'] == player), None)
        if perspective is None:
            raise ValueError(f'No sufficiently recent live-round state for player {player!r} at tick {tick}')
        team = perspective['team']
        if team not in (2, 3):
            raise ValueError('Player team is unknown at the requested tick')
        knowledge = information.get_team_visual_state_at_tick(
            self.team_observations, self.team_spot_windows,
            round_number=round_info['number'], observer_team=team,
            tick=tick, deaths_df=self.deaths_df)
        # DO NOT add coordinates of unknown actual enemies to team_knowledge.
        return {
            'tick': tick, 'map': self.map_name, 'round': round_info,
            'perspective': {'steamid': perspective['steamid'], 'name': perspective['name'], 'team': team},
            'ground_truth': {'players': snapshots},
            'team_knowledge': {'visual_enemies': knowledge, 'other_sources': 'not_implemented'},
            'expected_state': {'status': 'not_implemented'},
            'economy': build_round_economy(snapshots),
            "loadout": {
                "T": build_team_loadout(snapshots, 2),
                "CT": build_team_loadout(snapshots, 3),
            },
        }


    def get_round_start_economy(self, tick, player):
        """Return round-start economy as ground truth."""
        state = self.get_game_state(tick, player)
        round_info = state["round"]

        if round_info is None:
            return None

        start_tick = round_info["live_start_tick"]

        try:
            start_state = self.get_game_state(
                start_tick, player
            )
        except ValueError:
            return {
                "round": round_info["number"],
                "live_start_tick": start_tick,
                "status": "unavailable",
                "teams": None
            }

        players = start_state["ground_truth"]["players"]

        return {
            "round": round_info["number"],
            "live_start_tick": start_tick,
            "teams": build_round_start_economy(players),
            "status": "available",
        }




    def get_round_start_loadout(self, tick, player):
        """Ground-truth loadouts at the first live tick."""
        state = self.get_game_state(tick, player)
        round_info = state["round"]

        if round_info is None:
            return None

        start_tick = round_info["live_start_tick"]

        try:
            start_state = self.get_game_state(
                start_tick, player
            )
        except ValueError:
            return {
                "round": round_info["number"],
                "live_start_tick": start_tick,
                "status": "unavailable",
                "teams": None,
            }

        players = start_state["ground_truth"]["players"]

        return {
            "round": round_info["number"],
            "live_start_tick": start_tick,
            "status": "available",
            "teams": {
                "T": build_team_loadout(players, 2),
                "CT": build_team_loadout(players, 3),
            },
        }


    def get_economy_history(self, tick, player, limit=5):
        """
        Return ground-truth economy history
        for previous completed rounds only.
        """

        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be positive")

        state = self.get_game_state(tick, player)
        current = state["round"]

        if current is None:
            return None

        current_start = current["live_start_tick"]
        previous_rounds = []

        for match_round, demo_round, start, end in self.round_intervals:
            if int(end) < current_start:
                previous_rounds.append(
                    (int(match_round), int(start))
                )

        previous_rounds.sort(key=lambda item: item[1])
        snapshots = []

        results_by_round = {
            result["round"]: result
            for result in self.get_round_results_at_tick(tick)
        }

        for round_number, start_tick in previous_rounds[-limit:]:
            try:
                snapshot = self.get_round_start_economy(
                    start_tick, player
                )

            except ValueError:
                snapshot = None

            if snapshot is None:
                snapshot = {
                    "round": round_number,
                    "live_start_tick": start_tick,
                    "status": "unavailable",
                    "teams": None,
                }


            round_result = results_by_round.get(
                round_number
            )

            snapshot["round_result"] = (
                dict(round_result)
                if round_result is not None
                else None
            )

            snapshot["loss_bonus"] = (
                get_loss_reward_for_round(
                    self.loss_counter_timeline,
                    round_result,
                )
                if round_result is not None
                else None
            )


            snapshots.append(snapshot)

        return build_economy_history(
            round_snapshots=snapshots,
            current_round=current["number"],
            limit=limit,
        )


    def get_player_economy_history(
        self, player, current_tick=None
    ):
        player_id = information.normalize_steamid(player)

        stream = self.player_streams.get(player_id)

        if stream is None:
            raise ValueError(
                f"No player stream found: {player}"
            )


        from .player_economy_history import get_round_survival

        history = build_player_economy_history(
            player_stream=stream,
            round_intervals=self.round_intervals,
            geometry=self.geometry,
            current_tick=current_tick,
        )

        deaths = self.deaths_df

        death_data_complete = (
            self.death_data_complete
            and deaths is not None
            and isinstance(deaths, pd.DataFrame)
            and {"tick", "user_steamid"}.issubset(deaths.columns)
        )

        player_death_ticks = []

        if death_data_complete:
            for _, death in deaths.iterrows():
                victim_id = information.normalize_steamid(
                    death["user_steamid"]
                )

                if victim_id != player_id:
                    continue

                death_tick = death["tick"]

                if pd.notna(death_tick):
                    player_death_ticks.append(int(death_tick))

        for record in history:
            if record["status"] != "available":
                record["survival"] = {
                    "status": "unknown",
                    "survived": None,
                    "death_tick": None,
                }
                continue

            record["survival"] = get_round_survival(
                player_death_ticks=player_death_ticks,
                live_start_tick=record["live_start_tick"],
                end_tick=record["end_tick"],
                death_data_complete=death_data_complete,
            )


        from .player_economy_history import (
            get_saved_equipment_candidate,
        )

        for record in history:
            record["saved_equipment"] = (
                get_saved_equipment_candidate(
                    record,
                    max_age_ticks=self.max_state_age_ticks,
                )
            )


        for record in history:
            key = (record["round"], player_id)
            snapshot = self.prebuy_snapshots.get(key)
            sample_tick = snapshot.get("sample_tick") if snapshot else None
            # Historical legacy snapshots without a tick remain offline-only.
            if current_tick is not None and (
                sample_tick is None or int(sample_tick) > int(current_tick)
                or int(sample_tick) > record["live_start_tick"]
            ):
                snapshot = None
            record["pre_buy"] = deepcopy(snapshot)


        rewards = {r["round"]: r for r in self.get_player_economic_rewards(
            player_id, current_tick=current_tick
        )}
        for record in history:
            record["kill_rewards"] = rewards.get(record["round"])



        return history

    def get_player_economic_rewards(self, player, current_tick=None):
        """Ground-truth nominal kill awards; an optional as-of cutoff is inclusive.

        Deliberately absent from get_decision_input: an opponent's ground-truth
        reward history must not become team knowledge automatically.
        """
        player_id = information.normalize_steamid(player)
        if player_id not in self.player_streams:
            raise ValueError(f"No player stream found: {player}")
        rewards = build_round_kill_rewards(
            self.deaths_df, self.round_intervals, player_ids=[player_id],
            current_tick=current_tick, rules=self.economic_reward_rules,
            death_data_complete=self.death_data_complete,
        )
        return [record for (steamid, _), record in rewards.items() if steamid == player_id]




    def get_round_results(self):
        """Complete ground-truth round results."""
        return [dict(result) for result in self.round_results]

    def get_round_results_at_tick(self, tick):
        """Round results already established by the requested tick."""
        tick = int(tick)
        history = []

        for result in self.round_results:
            result_tick = result["result_tick"]

            if result_tick is not None:
                if result_tick <= tick:
                    history.append(dict(result))
            elif result["end_tick"] <= tick:
                history.append(dict(result))

        return history


    def get_loss_bonus_state(self, tick):
        """
        Return loss counters known at the requested tick.

        Counters are engine values, not monetary rewards.
        """
        state = get_loss_counters_at_tick(
            self.loss_counter_timeline,
            tick,
        )

        next_reward = get_next_loss_reward(
            self.loss_counter_timeline,
            tick,
        )

        return {
            "tick": state["tick"],
            "status": state["status"],
            "source_tick": state["source_tick"],
            "engine_counters": {
                "CT": state["CT"],
                "T": state["T"],
            },
            "monetary_bonus": {
                "CT": None,
                "T": None,
            },
            "next_loss_reward": next_reward[
                "base_reward_if_lost_now"
            ],
            "next_loss_reward_status": next_reward["status"],
        }



    def get_round_loss_rewards_at_tick(self, tick):
        """
        Ground-truth base loss rewards for rounds
        completed by the requested tick.
        """
        results = self.get_round_results_at_tick(tick)

        return [
            get_loss_reward_for_round(
                self.loss_counter_timeline,
                result,
            )
            for result in results
        ]


    def attach_radar_round_context(
        self, bomb, *, tickrate, round_time_seconds
    ):
        """Reuse existing radar C4 states; never reparse the demo."""
        if bomb.get("coordinate_source") != "CC4/CPlantedC4":
            raise ValueError("Real C4 entity source is required")

        self._bomb_states = sorted(
            [deepcopy(s) for s in bomb.get("states", [])
             if s.get("tick") is not None],
            key=lambda s: int(s["tick"]),
        )
        self._bomb_ticks = [
            int(s["tick"]) for s in self._bomb_states
        ]
        self._round_tickrate = float(tickrate)
        self._round_time_seconds = float(round_time_seconds)

        if self._round_tickrate <= 0 or self._round_time_seconds <= 0:
            raise ValueError("Invalid round clock configuration")

    def get_bomb_ground_truth_at_tick(self, tick, round_info):
        """Internal truth only. Never expose directly to Decision Input."""
        index = bisect_right(self._bomb_ticks, int(tick)) - 1

        if index < 0:
            return None

        sample = self._bomb_states[index]

        if int(sample["tick"]) < int(round_info["live_start_tick"]):
            return None

        return deepcopy(sample)



    def get_round_state(self, tick, player):
        """Decision-safe round context at a specific tick."""
        state = self.get_game_state(tick, player)
        round_info = state["round"]

        result = build_round_state(
            tick=tick,
            round_info=round_info,
            players=state["ground_truth"]["players"],
            completed_results=self.get_round_results_at_tick(tick),
        )

        result["score"] = self.get_match_score(tick, player)

        # Clock estimate from configured match constants,
        # never from the actual future round-end event.
        if self._round_tickrate is not None:
            elapsed = max(
                0.0,
                (int(tick) - int(round_info["live_start_tick"]))
                / self._round_tickrate,
            )
            remaining = max(
                0.0, self._round_time_seconds - elapsed
            )
            result["clock"] = {
                "remaining_seconds": round(remaining, 2),
                "status": "configured_estimate",
            }

        bomb_truth = self.get_bomb_ground_truth_at_tick(
            tick, round_info
        )

        observer_team = state["perspective"]["team"]
        bomb_status = (
            bomb_truth.get("state")
            if bomb_truth is not None
            else None
        )

        # CT must not receive hidden C4 position or carrier.
        # T can know its own team's carried/dropped bomb.
        public_status = "unknown"

        if bomb_status in ("planted", "defused", "exploded"):
            public_status = bomb_status
        elif observer_team == 2 and bomb_status in ("carried", "dropped"):
            public_status = bomb_status

        result["bomb"] = {
            "status": public_status,
            "carrier": (
                bomb_truth.get("carrier_steamid")
                if observer_team == 2
                and public_status == "carried"
                else None
            ),
            "site": None,
            "source_tick": (
                int(bomb_truth["tick"])
                if public_status != "unknown"
                and bomb_truth is not None
                else None
            ),
        }

        if public_status in ("planted", "defused", "exploded"):
            # Standard round clock no longer describes
            # the active bomb countdown.
            result["clock"]["remaining_seconds"] = None
            result["clock"]["status"] = "postplant_clock_unavailable"

        return result



    def get_match_score(self, tick, player):
        """Score from completed results known by tick."""
        state = self.get_game_state(tick, player)
        player_id = state["perspective"]["steamid"]

        stream = self.player_streams.get(player_id)
        completed = self.get_round_results_at_tick(tick)
        side_by_round = {}

        if stream is not None:
            intervals = {
                int(match_round): (int(start), int(end))
                for match_round, _, start, end
                in self.round_intervals
            }

            for result in completed:
                round_number = int(result["round"])
                interval = intervals.get(round_number)

                if interval is None:
                    continue

                start, end = interval

                rows = stream[
                    (stream["tick"] >= start)
                    & (stream["tick"] < end)
                    & stream["team_num"].isin([2, 3])
                ]

                if rows.empty:
                    continue

                side_number = int(rows.iloc[0]["team_num"])
                side_by_round[round_number] = (
                    "T" if side_number == 2 else "CT"
                )

        return build_perspective_score(
            completed,
            side_by_round,
        )


    def attach_event_timeline(
        self,
        *,
        grenade_event_frames=None,
        bomb_event_frames=None,
        grenade_tracks=None,
    ):
        """Build the event index once from existing parsed data."""
        self.event_timeline = EventTimeline(
            round_intervals=self.round_intervals,
            deaths_df=self.deaths_df,
            grenade_event_frames=grenade_event_frames,
            bomb_event_frames=bomb_event_frames,
            grenade_tracks=grenade_tracks,
        )

    def get_event_history(
        self,
        tick,
        *,
        round_number=None,
        limit=100,
    ):
        """Ground truth history, NOT team knowledge."""
        if not hasattr(self, "event_timeline"):
            raise RuntimeError("Event timeline has not been attached")

        return self.event_timeline.history(
            tick,
            round_number=round_number,
            limit=limit,
        )


    def get_player_utility_state(self, tick, player):
        state = self.get_game_state(tick, player)
        player_id = state["perspective"]["steamid"]

        snapshot = next(
            (
                p for p in state["ground_truth"]["players"]
                if str(p.get("steamid")) == str(player_id)
            ),
            None,
        )

        if snapshot is None or snapshot.get("inventory") is None:
            return {
                "status": "unavailable",
                "items": None,
                "counts": None,
                "total": None,
            }

        utility = build_player_utility_from_inventory(snapshot)

        return {
            "status": "observed",
            "items": utility["items"],
            "counts": {
                key: value
                for key, value in utility.items()
                if key not in ("items", "total")
            },
            "total": utility["total"],
        }

    def get_team_utility_state(self, tick, player):
        state = self.get_game_state(tick, player)
        team = state["perspective"]["team"]

        teammates = [
            p for p in state["ground_truth"]["players"]
            if p.get("team") == team
        ]

        known = [
            p for p in teammates
            if p.get("inventory") is not None
        ]

        aggregate = build_team_utility(known)

        complete = len(teammates) == 5 and len(known) == 5

        return {
            "status": "complete" if complete else "partial",
            "team": team,
            "observed_players": len(known),
            "expected_players": 5,
            "counts": {
                key: value
                for key, value in aggregate.items()
                if key not in ("players", "total")
            },
            "observed_total": aggregate["total"],
        }

    def get_utility_history(self, tick, player, *, limit=100):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be positive")

        state = self.get_game_state(tick, player)
        round_number = state["round"]["number"]

        if not hasattr(self, "event_timeline"):
            raise RuntimeError("Event timeline is not attached")

        events = self.event_timeline.history(
            tick,
            round_number=round_number,
            limit=max(1, len(self.event_timeline.events)),
        )

        return deepcopy([
            event for event in events
            if event["kind"] == "utility"
        ][-limit:])


    def get_active_utility_effects(self, tick, player):
        """
        Ground-truth utility effects in the current round.
        Not automatically safe for Decision Input.
        """
        state = self.get_game_state(tick, player)
        round_number = state["round"]["number"]

        if not hasattr(self, "event_timeline"):
            raise RuntimeError("Event timeline is not attached")

        events = self.event_timeline.history(
            tick,
            round_number=round_number,
            limit=max(1, len(self.event_timeline.events)),
        )

        utility_events = [
            event for event in events
            if event["kind"] == "utility"
        ]

        return build_active_utility(utility_events, tick)






    def get_decision_input(self, tick, player):
        """Return information available to the player's team."""
        state = self.get_game_state(tick, player)

        observer_team = state["perspective"]["team"]

        friends = [
            p for p in state["ground_truth"]["players"]
            if p["team"] == observer_team
        ]

        team_side = "T" if observer_team == 2 else "CT"
        round_state = self.get_round_state(tick, player)

        return {
            "tick": state["tick"],
            "map": state["map"],
            # Actual end time is a future outcome during the current round.
            "round": {key: value for key, value in state["round"].items()
                      if key != "end_tick"},
            "perspective": state["perspective"],

            "team_players": friends,
            "team_economy": state["economy"][team_side],
            "team_loadout": state["loadout"][team_side],

            "known_enemies": state["team_knowledge"]["visual_enemies"],
            "other_information_sources": "not_implemented",
            "expected_state": state["expected_state"],
            "round_state": round_state,
        }
