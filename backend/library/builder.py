"""Match data access: normalized state streams + event-derived team observations.

Construct once per match, query GameState(tick) many times. No DEM reparse per tick.
"""
import pandas as pd
import information
from .game_state import find_round, player_from_row
from .economy import build_round_economy, build_team_loadout
from .economy import build_round_start_economy
from .economy_history import build_economy_history
from .round_results import build_round_results




class MatchLibrary:
    def __init__(self, *, map_name, position_df, round_intervals,
                 deaths_df=None, geometry=None, team_observations=None,
                 team_spot_windows=None, max_state_age_ticks=16,
                 round_ends=None):
        if not {'tick', 'steamid', 'team_num'}.issubset(position_df.columns):
            raise ValueError('position_df requires tick, steamid, team_num')
        self.map_name = str(map_name)
        self.round_intervals = list(round_intervals)
        self.round_results = build_round_results(
            self.round_intervals,
            round_ends,
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
        self.team_observations = (team_observations if team_observations is not None
                                  else information.build_team_observations(self.position_df, self.round_intervals))
        if team_spot_windows is None:
            spots = information.build_spot_events(self.position_df, self.round_intervals)
            team_spot_windows = information.build_team_spot_windows(spots)
        self.team_spot_windows = team_spot_windows

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

            snapshots.append(snapshot)

        return build_economy_history(
            round_snapshots=snapshots,
            current_round=current["number"],
            limit=limit,
        )


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






    def get_decision_input(self, tick, player):
        """Return information available to the player's team."""
        state = self.get_game_state(tick, player)

        observer_team = state["perspective"]["team"]

        friends = [
            p for p in state["ground_truth"]["players"]
            if p["team"] == observer_team
        ]

        team_side = "T" if observer_team == 2 else "CT"

        return {
            "tick": state["tick"],
            "map": state["map"],
            "round": state["round"],
            "perspective": state["perspective"],

            "team_players": friends,
            "team_economy": state["economy"][team_side],
            "team_loadout": state["loadout"][team_side],

            "known_enemies": state["team_knowledge"]["visual_enemies"],
            "other_information_sources": "not_implemented",
            "expected_state": state["expected_state"],
        }
