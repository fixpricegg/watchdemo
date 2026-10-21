
import unittest

from library.economic_rewards import (
    calculate_reward_delta,
    build_kill_reward_history,
)


class TestEconomicRewards(unittest.TestCase):

    def test_reward_delta(self):
        self.assertEqual(
            calculate_reward_delta(300, 600),
            300,
        )

    def test_no_change(self):
        self.assertEqual(
            calculate_reward_delta(600, 600),
            0,
        )

    def test_counter_reset(self):
        self.assertIsNone(
            calculate_reward_delta(900, 0)
        )

    def test_missing_value(self):
        self.assertIsNone(
            calculate_reward_delta(None, 300)
        )

    def test_history(self):
        observations = [
            {"tick": 100, "round": 1, "kill_reward": 300},
            {"tick": 200, "round": 2, "kill_reward": 600},
            {"tick": 300, "round": 3, "kill_reward": 600},
        ]

        history = build_kill_reward_history(observations)

        self.assertIsNone(
            history[0]["delta_since_previous_sample"]
        )
        self.assertIsNone(
            history[1]["delta_since_previous_sample"],
        )
        self.assertIsNone(
            history[2]["delta_since_previous_sample"],
        )


if __name__ == "__main__":
    unittest.main()
