
import unittest

from library.trade_contact import assess_trade_contact


class TestTradeContact(unittest.TestCase):
    def setUp(self):
        self.observations = [
            {
                "round": 11,
                "tick": 59150,
                "observer_team": 2,
                "target_steamid": "900",
                "spotters": ["456"],
            },
            {
                "round": 11,
                "tick": 59160,
                "observer_team": 2,
                "target_steamid": "900",
                "spotters": ["123"],
            },
        ]

    def evaluate(self, observations=None):
        return assess_trade_contact(
            self.observations if observations is None else observations,
            round_number=11,
            observer_team=2,
            player_steamid="123",
            killer_steamid="900",
            start_tick=59144,
            end_tick=59200,
        )

    def test_personal_contact(self):
        result = self.evaluate()

        self.assertTrue(result["personal_contact_observed"])
        self.assertEqual(
            result["first_personal_contact_tick"], 59160
        )
        self.assertEqual(result["line_of_fire"], "not_verified")
        self.assertEqual(
            result["trade_feasibility"], "not_established"
        )

    def test_teammate_only(self):
        result = self.evaluate(self.observations[:1])

        self.assertFalse(result["personal_contact_observed"])
        self.assertTrue(result["team_contact_observed"])

    def test_no_observation(self):
        result = self.evaluate([])

        self.assertFalse(result["personal_contact_observed"])
        self.assertFalse(result["team_contact_observed"])

    def test_future_observation_is_excluded(self):
        future = [{
            "round": 11,
            "tick": 59201,
            "observer_team": 2,
            "target_steamid": "900",
            "spotters": ["123"],
        }]

        self.assertFalse(
            self.evaluate(future)["personal_contact_observed"]
        )

    def test_wrong_round_is_excluded(self):
        wrong_round = [{
            "round": 12,
            "tick": 59160,
            "observer_team": 2,
            "target_steamid": "900",
            "spotters": ["123"],
        }]

        self.assertFalse(
            self.evaluate(wrong_round)["personal_contact_observed"]
        )

    def test_wrong_team_is_excluded(self):
        wrong_team = [{
            "round": 11,
            "tick": 59160,
            "observer_team": 3,
            "target_steamid": "900",
            "spotters": ["123"],
        }]

        self.assertFalse(
            self.evaluate(wrong_team)["personal_contact_observed"]
        )

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            assess_trade_contact(
                [],
                round_number=11,
                observer_team=2,
                player_steamid="123",
                killer_steamid="900",
                start_tick=59200,
                end_tick=59144,
            )


if __name__ == "__main__":
    unittest.main()
