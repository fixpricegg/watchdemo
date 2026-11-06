"""C4 coordinates from CC4 / CPlantedC4, not from dropper/planter positions."""
import bisect
import math
import os
import platform
import subprocess
from collections import defaultdict
from pathlib import Path

import orjson

INVALID_OWNER_HANDLE = (1 << 24) - 1
LOCKED = {"planted", "defused", "exploded"}
TERMINAL = {"defused", "exploded"}


def parse_bomb_entities(demo_path):
    override = os.environ.get("WATCHDEMO_C4_EXTRACTOR")
    if override:
        executable = Path(override).expanduser().resolve()
    else:
        system = platform.system().lower()
        machine = platform.machine().lower()
        architecture = {"amd64": "amd64", "x86_64": "amd64"}.get(machine)
        if system not in {"windows", "linux"} or architecture is None:
            raise RuntimeError("C4 entity extractor requires Windows/Linux x64, or WATCHDEMO_C4_EXTRACTOR.")
        name = f"c4-extractor-{system}-{architecture}" + (".exe" if system == "windows" else "")
        executable = Path(__file__).resolve().parents[1] / "tools" / "c4_extractor" / "bin" / name
    if not executable.is_file():
        raise RuntimeError(f"C4 entity extractor missing: {executable}. Copy tools/c4_extractor from the fix archive.")
    try:
        completed = subprocess.run(
            [str(executable), "-demo", str(Path(demo_path).resolve())],
            check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"").decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"Cannot read C4 entities from demo. {detail}") from exc
    try:
        stream = orjson.loads(completed.stdout)
    except orjson.JSONDecodeError as exc:
        raise RuntimeError("C4 extractor returned invalid JSON") from exc
    if (stream.get("schema") != 1 or not stream.get("samples")
            or not any(s.get("class") in {"CC4", "CPlantedC4"} for s in stream["samples"])):
        raise RuntimeError("C4 extractor returned no supported entity samples")
    return stream


def _point(sample):
    if not sample or not sample.get("position_valid"):
        return None
    values = tuple(sample.get(axis) for axis in ("X", "Y", "Z"))
    if any(value is None or not math.isfinite(float(value)) for value in values):
        return None
    return tuple(float(value) for value in values)


def _key(sample):
    return sample["entity_id"], sample["serial"]


class EntityFrames:
    def __init__(self, stream):
        frames = defaultdict(dict)
        for sample in stream["samples"]:
            # Multiple demo packets may have the same tick. Keep final state per entity.
            frames[int(sample["tick"])][_key(sample)] = sample
        self.frames = {tick: list(samples.values()) for tick, samples in frames.items()}
        self.ticks = sorted(self.frames)

    def at(self, tick, reset_tick):
        index = bisect.bisect_right(self.ticks, tick) - 1
        if index < 0 or self.ticks[index] < reset_tick:
            return None, []
        sample_tick = self.ticks[index]
        return sample_tick, self.frames[sample_tick]


def build_bomb_timeline(positions, stream, events):
    """Keep event lifecycle, resolve physical coordinates from entities each frame."""
    if positions.empty:
        return [], events
    frames = EntityFrames(stream)
    ticks = sorted(set(int(tick) for tick in positions["tick"].dropna()))
    player_positions = {}
    for row in positions.itertuples(index=False):
        if row.steamid is None:
            continue
        try:
            key = (int(row.tick), int(row.steamid))
        except (TypeError, ValueError):
            continue
        try:
            coords = tuple(float(value) for value in (row.X, row.Y, row.Z))
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(value) for value in coords):
            player_positions[key] = coords
    state = "unavailable"
    since = None
    reset_tick = -1
    carrier_id = carrier_name = site = None
    planted_key = None
    planted_position = None
    event_index = 0
    states = []
    for tick in ticks:
        while event_index < len(events) and events[event_index]["tick"] <= tick:
            event = events[event_index]
            name = event["event"]
            event_tick = event["tick"]
            if name == "round_reset":
                state, since, reset_tick = "unavailable", event_tick, event_tick
                carrier_id = carrier_name = site = planted_key = planted_position = None
            elif state not in TERMINAL:
                if name in {"bomb_dropped", "bomb_pickup"} and state not in LOCKED:
                    state = "dropped" if name == "bomb_dropped" else "carried"
                    since = event_tick
                    carrier_id = event.get("player_steamid") if state == "carried" else None
                    carrier_name = event.get("player_name") if state == "carried" else None
                elif name == "bomb_planted" and state not in LOCKED:
                    state, since = "planted", event_tick
                    carrier_id = carrier_name = None
                elif name in {"bomb_defused", "bomb_exploded"}:
                    state, since = name.removeprefix("bomb_"), event_tick
                    carrier_id = carrier_name = None
            event_index += 1

        sample_tick, samples = frames.at(tick, reset_tick)
        planted = [s for s in samples if s["class"] == "CPlantedC4"
                   and s.get("created_tick", -1) >= reset_tick]
        # Serial numbers prevent a reused entity ID from reviving a previous C4.
        if planted_key is not None:
            planted = [s for s in planted if _key(s) == planted_key]
        if state not in LOCKED:
            planted = [s for s in planted if s.get("ticking") is True]
        if len(planted) > 1:
            raise RuntimeError(f"Multiple planted C4 entities at tick {tick}; refusing to guess")
        plant = planted[0] if planted else None
        c4s = [s for s in samples if s["class"] == "CC4"]
        c4s = [s for s in c4s if s.get("carrier_steamid")
               or (s.get("owner_handle") == INVALID_OWNER_HANDLE and _point(s) is not None)]
        if len(c4s) > 1 and plant is None and state not in LOCKED:
            raise RuntimeError(f"Multiple active C4 entities at tick {tick}; refusing to guess")
        c4 = c4s[0] if c4s else None
        if plant is not None:
            if state not in LOCKED:
                state, since = "planted", int(plant["created_tick"])
            if plant.get("defused") is True and state not in TERMINAL:
                state, since = "defused", sample_tick
            elif plant.get("ticking") is False and state == "planted":
                state, since = "exploded", sample_tick
            carrier_id = carrier_name = None
            planted_key = _key(plant)
            if _point(plant) is not None:
                planted_position = _point(plant)
            site = {0: "A", 1: "B"}.get(plant.get("site"), site)
        elif state not in LOCKED and c4 is not None:
            next_id = int(c4["carrier_steamid"]) if c4.get("carrier_steamid") else None
            next_state = "carried" if next_id is not None else "dropped"
            if state != next_state or carrier_id != next_id:
                since = sample_tick
            state, carrier_id = next_state, next_id
            carrier_name = c4.get("carrier_name") if state == "carried" else None

        point = None
        entity = None
        accuracy = "unknown"
        if state in LOCKED:
            point = planted_position
            entity = plant
            if point is not None:
                accuracy = "entity_position"
        elif state == "dropped" and c4 is not None and not c4.get("carrier_steamid"):
            point, entity = _point(c4), c4
            if point is not None:
                accuracy = "entity_position"
        elif state == "carried" and c4 is not None and c4.get("carrier_steamid"):
            point = player_positions.get((tick, carrier_id))
            entity = c4
            if point is not None:
                accuracy = "carrier_position"
        x, y, z = point if point is not None else (None, None, None)
        states.append({
            "tick": tick, "state": state, "state_since_tick": since,
            "carrier_steamid": carrier_id, "carrier_name": carrier_name,
            "x": x, "y": y, "z": z, "site": site,
            "position_accuracy": accuracy, "source": "c4_entities",
            "entity_id": entity["entity_id"] if entity else (planted_key[0] if planted_key else None),
            "entity_serial": entity["serial"] if entity else (planted_key[1] if planted_key else None),
            "entity_sample_tick": sample_tick,
        })
    return states, events
