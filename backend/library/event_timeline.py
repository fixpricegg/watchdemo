
"""Ground-truth event timeline, built from already parsed match data."""

from bisect import bisect_right
from copy import deepcopy
import pandas as pd


GRENADE_EVENTS = (
    "flashbang_detonate",
    "hegrenade_detonate",
    "smokegrenade_detonate",
    "smokegrenade_expired",
    "inferno_startburn",
    "inferno_expire",
    "decoy_started",
    "decoy_detonate",
)

BOMB_EVENTS = (
    "bomb_pickup",
    "bomb_dropped",
    "bomb_planted",
    "bomb_defused",
    "bomb_exploded",
    "bomb_beginplant",
    "bomb_abortplant",
    "bomb_begindefuse",
    "bomb_abortdefuse",
)


def _optional(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _steamid(value):
    value = _optional(value)
    if value is None:
        return None
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value)


class EventTimeline:
    def __init__(
        self,
        *,
        round_intervals,
        deaths_df=None,
        grenade_event_frames=None,
        bomb_event_frames=None,
        grenade_tracks=None,
    ):
        self.round_intervals = [
            (int(number), int(start), int(end))
            for number, _, start, end in round_intervals
        ]

        events = []

        def append(tick, kind, event_type, source, data):
            tick = _optional(tick)
            if tick is None:
                return

            tick = int(tick)
            round_number = next(
                (
                    number
                    for number, start, end in self.round_intervals
                    if start <= tick < end
                ),
                None,
            )

            if round_number is None:
                return

            events.append({
                "tick": tick,
                "round": round_number,
                "kind": kind,
                "type": event_type,
                "source": source,
                "data": data,
            })

        # Actual death events, already extracted by analyzer.
        if isinstance(deaths_df, pd.DataFrame):
            if "tick" in deaths_df.columns:
                for _, row in deaths_df.iterrows():
                    append(
                        row["tick"],
                        "combat",
                        "player_death",
                        "demo_event",
                        {
                            "attacker_steamid": _steamid(
                                row.get("attacker_steamid")
                            ),
                            "victim_steamid": _steamid(
                                row.get("user_steamid")
                            ),
                            "weapon": _optional(row.get("weapon")),
                            "headshot": _optional(row.get("headshot")),
                        },
                    )

        # The first actual sampled grenade trajectory point.
        # No future detonation/end data is attached to the launch.
        for track in grenade_tracks or []:
            append(
                track.get("start_tick"),
                "utility",
                "grenade_track_start",
                "radar_grenade_track",
                {
                    "track_id": track.get("track_id"),
                    "grenade_type": track.get("type"),
                    "thrower_steamid": _steamid(
                        track.get("thrower_steamid")
                    ),
                },
            )

        # Confirmed grenade events. Do not synthesize future
        # effects from a projectile's expected lifetime.
        for name in GRENADE_EVENTS:
            frame = (grenade_event_frames or {}).get(name)

            if not isinstance(frame, pd.DataFrame):
                continue
            if frame.empty or "tick" not in frame.columns:
                continue

            for _, row in frame.iterrows():
                append(
                    row["tick"],
                    "utility",
                    name,
                    "demo_event",
                    {
                        "user_steamid": _steamid(
                            row.get("user_steamid")
                        ),
                        "entity_id": _optional(
                            row.get("entityid")
                        ),
                        "x": _optional(row.get("x")),
                        "y": _optional(row.get("y")),
                        "z": _optional(row.get("z")),
                    },
                )

        # C4 lifecycle events are already parsed for the radar.
        for name in BOMB_EVENTS:
            frame = (bomb_event_frames or {}).get(name)

            if not isinstance(frame, pd.DataFrame):
                continue
            if frame.empty or "tick" not in frame.columns:
                continue

            for _, row in frame.iterrows():
                append(
                    row["tick"],
                    "objective",
                    name,
                    "demo_event",
                    {
                        "user_steamid": _steamid(
                            row.get("user_steamid")
                        ),
                        "site": _optional(row.get("site")),
                    },
                )

        events.sort(key=lambda event: event["tick"])

        self.events = events
        self.ticks = [event["tick"] for event in events]

    def history(self, tick, *, round_number=None, limit=100):
        """Return event observations at or before tick."""
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")

        tick = int(tick)
        end = bisect_right(self.ticks, tick)

        past = self.events[:end]

        if round_number is not None:
            past = [
                event for event in past
                if event["round"] == int(round_number)
            ]

        return deepcopy(past[-limit:])

    def all_ground_truth(self):
        """Full timeline: evaluation/replay only, not Decision Input."""
        return deepcopy(self.events)
