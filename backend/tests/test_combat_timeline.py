
import unittest
import pandas as pd

from library.event_timeline import EventTimeline
from library.builder import MatchLibrary


class TestCombatTimeline(unittest.TestCase):

    def setUp(self):
        self.rounds = [
            (1, 1, 100, 300),
            (2, 2, 400, 600),
        ]

        self.timeline = EventTimeline(
            round_intervals=self.rounds,
            deaths_df=pd.DataFrame([
                {
                    "tick": 150,
                    "attacker_steamid": 900,
                    "user_steamid": 456,
                    "weapon": "ak47",
                }
            ]),
            combat_event_frames={
                "weapon_fire": pd.DataFrame([
                    {"tick": 90, "user_steamid": 123},
                    {"tick": 140, "user_steamid": 123},
                    {"tick": 450, "user_steamid": 123},
                ]),
                "player_hurt": pd.DataFrame([
                    {
                        "tick": 145,
                        "attacker_steamid": 123,
                        "user_steamid": 900,
                        "dmg_health": 30,
                    }
                ]),
            },
        )

    def test_weapon_fire(self):
        events = self.timeline.history(140)
        shots = [
            e for e in events
            if e["type"] == "weapon_fire"
        ]

        self.assertEqual(len(shots), 1)
        self.assertEqual(
            shots[0]["data"]["actor_steamid"], "123"
        )

    def test_player_hurt(self):
        events = self.timeline.history(145)
        hits = [
            e for e in events
            if e["type"] == "player_hurt"
        ]

        self.assertEqual(len(hits), 1)
        self.assertEqual(
            hits[0]["data"]["victim_steamid"], "900"
        )
        self.assertEqual(
            hits[0]["data"]["damage_health"], 30
        )

    def test_no_future_leakage(self):
        events = self.timeline.history(140)

        self.assertFalse(any(
            e["tick"] > 140 for e in events
        ))

    def test_warmup_excluded(self):
        events = self.timeline.all_ground_truth()

        self.assertFalse(any(
            e["tick"] == 90 for e in events
        ))

    def test_round_isolation(self):
        events = self.timeline.history(
            500, round_number=2
        )

        self.assertEqual(
            [e["tick"] for e in events],
            [450],
        )

    def test_missing_source_is_not_no_events(self):
        timeline = EventTimeline(
            round_intervals=self.rounds,
            combat_event_frames={
                "weapon_fire": None,
                "player_hurt": pd.DataFrame(),
            },
        )

        self.assertEqual(
            timeline.combat_parse_status["weapon_fire"],
            "unavailable",
        )

    def test_match_library_window(self):
        class FakeLibrary:
            get_combat_window = MatchLibrary.get_combat_window

        library = FakeLibrary()
        library.round_intervals = self.rounds
        library.event_timeline = self.timeline

        result = library.get_combat_window(140, 150)

        self.assertEqual(
            result["status"], "sources_parsed"
        )
        self.assertEqual(
            [e["type"] for e in result["events"]],
            ["weapon_fire", "player_hurt", "player_death"],
        )

        with self.assertRaises(ValueError):
            library.get_combat_window(290, 410)


if __name__ == "__main__":
    unittest.main()
