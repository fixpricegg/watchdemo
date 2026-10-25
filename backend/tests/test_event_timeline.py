
import unittest
import pandas as pd

from library.event_timeline import EventTimeline


class TestEventTimeline(unittest.TestCase):

    def setUp(self):
        self.timeline = EventTimeline(
            round_intervals=[
                (1, 1, 100, 300),
                (2, 2, 400, 600),
            ],
            deaths_df=pd.DataFrame([
                {
                    "tick": 180,
                    "attacker_steamid": 123,
                    "user_steamid": 456,
                    "weapon": "ak47",
                },
            ]),
            grenade_tracks=[
                {
                    "start_tick": 120,
                    "track_id": "smoke-1",
                    "type": "smoke",
                    "thrower_steamid": 123,
                    "effect_start_tick": 210,
                    "effect_end_tick": 400,
                },
            ],
            grenade_event_frames={
                "smokegrenade_detonate": pd.DataFrame([
                    {"tick": 210, "entityid": 11},
                ]),
            },
            bomb_event_frames={
                "bomb_planted": pd.DataFrame([
                    {"tick": 250, "site": "A"},
                    {"tick": 510, "site": "B"},
                ]),
            },
        )

    def test_no_future_events(self):
        history = self.timeline.history(150)
        self.assertEqual(len(history), 1)
        self.assertEqual(
            history[0]["type"], "grenade_track_start"
        )

    def test_death_event(self):
        history = self.timeline.history(190)
        self.assertEqual(history[-1]["type"], "player_death")
        self.assertEqual(
            history[-1]["data"]["attacker_steamid"], "123"
        )

    def test_round_filter(self):
        history = self.timeline.history(
            550, round_number=2
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["type"], "bomb_planted")

    def test_future_grenade_effect_not_leaked(self):
        history = self.timeline.history(150)
        text = str(history)
        self.assertNotIn("210", text)
        self.assertNotIn("400", text)
        self.assertNotIn("effect_end_tick", text)

    def test_no_event_from_warmup(self):
        timeline = EventTimeline(
            round_intervals=[(1, 1, 100, 300)],
            bomb_event_frames={
                "bomb_pickup": pd.DataFrame([
                    {"tick": 50},
                ]),
            },
        )
        self.assertEqual(timeline.history(200), [])

    def test_history_is_immutable_copy(self):
        history = self.timeline.history(250)
        history[-1]["type"] = "corrupted"

        fresh = self.timeline.history(250)
        self.assertNotEqual(fresh[-1]["type"], "corrupted")


if __name__ == "__main__":
    unittest.main()
