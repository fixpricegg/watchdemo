"""Check the real entity coordinate path on a demo without loading analysis-core."""
import argparse
import sys
from collections import Counter
from pathlib import Path

import orjson
from demoparser2 import DemoParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import bomb_entities
import radar


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("demo", type=Path)
    args.add_argument("--output", type=Path, default=Path("c4-entity-check.json"))
    args.add_argument("--tick", type=int)
    options = args.parse_args()
    parser = DemoParser(str(options.demo))
    stream = bomb_entities.parse_bomb_entities(options.demo)
    positions = parser.parse_ticks([
        "X", "Y", "Z", "inventory", "is_alive",
        "is_bomb_planted", "is_bomb_dropped",
    ])
    event_frames = dict(parser.parse_events(list(radar.BOMB_STATE_EVENTS)))
    resets = parser.parse_event("round_prestart")["tick"].tolist()
    states, events = radar.build_bomb_timeline(
        positions[positions.tick % radar.RADAR_TICK_STEP == 0],
        event_frames, resets, bomb_entity_stream=stream,
    )
    missing = Counter(s["state"] for s in states if s["x"] is None or s["y"] is None)
    print("Coordinate source: CC4/CPlantedC4")
    print("Entity samples:", len(stream["samples"]))
    print("States:", dict(Counter(s["state"] for s in states)))
    print("States without coordinates:", dict(missing))
    result = {"map": parser.parse_header().get("map_name"),
              "entity_parser": stream["parser"], "missing_coordinates": dict(missing),
              "states": states, "events": events}
    if options.tick is not None:
        result["focus_entities"] = [s for s in stream["samples"]
                                    if abs(s["tick"] - options.tick) <= 64]
    options.output.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2))
    print("Check saved:", options.output)


if __name__ == "__main__":
    main()
