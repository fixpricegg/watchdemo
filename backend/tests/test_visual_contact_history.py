
import unittest

from library.visual_contact_history import (
    build_visual_contact_history,
)


class TestVisualContactHistory(unittest.TestCase):

    def setUp(self):
        self.observations = [
            {
                "round": 1,
                "tick": 100,
                "observer_team": 2,
                "target_steamid": "enemy1",
                "position": {"x": 10, "y": 20, "z": 0},
                "spotters": ["ally1"],
            },
            {
                "round": 1,
                "tick": 140,
                "observer_team": 2,
                "target_steamid": "enemy1",
                "position": {"x": 50, "y": 60, "z": 0},
                "spotters": ["ally2"],
            },
            {
                "round": 1,
                "tick": 180,
                "observer_team": 2,
                "target_steamid": "enemy1",
                "position": {"x": 900, "y": 900, "z": 0},
                "spotters": ["ally2"],
            },
            {
                "round": 1,
                "tick": 120,
                "observer_team": 3,
                "target_steamid": "ally1",
                "position": {"x": 500, "y": 500, "z": 0},
                "spotters": ["enemy1"],
            },
        ]

    def query(self, tick):
        return build_visual_contact_history(
            self.observations,
            round_number=1,
            observer_team=2,
            tick=tick,
        )

    def test_no_future_position(self):
        result = self.query(150)
        self.assertEqual(
            result[0]["last_seen_position"]["x"], 50
        )
        self.assertNotIn("900", str(result))

    def test_contact_age(self):
        result = self.query(150)
        self.assertEqual(result[0]["age_ticks"], 10)
        self.assertEqual(result[0]["status"], "last_known")

    def test_exact_observation(self):
        result = self.query(140)
        self.assertEqual(
            result[0]["status"], "observed_at_tick"
        )

    def test_enemy_team_isolation(self):
        result = self.query(150)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["target_steamid"], "enemy1"
        )

    def test_history_copy(self):
        result = self.query(150)
        result[0]["history"][0]["position"]["x"] = -999
        fresh = self.query(150)
        self.assertEqual(
            fresh[0]["history"][0]["position"]["x"], 10
        )

    def test_round_isolation(self):
        result = build_visual_contact_history(
            self.observations,
            round_number=2,
            observer_team=2,
            tick=200,
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
