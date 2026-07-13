from demoparser2 import DemoParser

parser = DemoParser("demos/match10.dem")

for event_name in [
    "begin_new_match",
    "round_announce_match_start",
    "round_prestart",
    "round_freeze_end",
    "round_end",
    "player_death",
]:
    print(f"\n== {event_name} ==")

    try:
        df = parser.parse_event(event_name)
        print("columns:", df.columns.tolist())
        print(df.head(20).to_string())
    except Exception as error:
        print("ERROR:", error)
