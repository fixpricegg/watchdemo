from demoparser2 import DemoParser

demo_path = "demos/match6.dem"
parser = DemoParser(demo_path)

print("== GAME EVENTS ==")
try:
    events = parser.list_game_events()
    for event in events:
        print(event)
except Exception as e:
    print("list_game_events ERROR:", e)

print("\n== TRY COMMON EVENTS ==")
possible_events = [
    "player_death",
    "round_freeze_end",
    "round_start",
    "round_end",
    "round_officially_ended",
    "bomb_planted",
    "bomb_defused",
]

for event in possible_events:
    try:
        df = parser.parse_event(event)
        print(f"{event}: OK, rows = {len(df)}")
        print(df.head())
    except Exception as e:
        print(f"{event}: ERROR -> {e}")