
import unittest

import pandas as pd

from library.loss_bonus import (
    CT_LOSS_FIELD,
    T_LOSS_FIELD,
    build_loss_counter_timeline,
    get_loss_counters_at_tick,
)


class TestLossBonus(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame([
            {
                "tick": 14350,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 2,
            },
            {
                "tick": 14350,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 2,
            },
            {
                "tick": 14351,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 3,
            },
            {
                "tick": 25413,
                CT_LOSS_FIELD: 1,
                T_LOSS_FIELD: 2,
            },
        ])

    def test_timeline(self):
        timeline = build_loss_counter_timeline(self.df)

        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[1]["T"], 3)

    def test_before_round_end(self):
        timeline = build_loss_counter_timeline(self.df)

        state = get_loss_counters_at_tick(
            timeline, 14350
        )

        self.assertEqual(state["T"], 2)
        self.assertEqual(state["CT"], 0)

    def test_after_round_end(self):
        timeline = build_loss_counter_timeline(self.df)

        state = get_loss_counters_at_tick(
            timeline, 14351
        )

        self.assertEqual(state["T"], 3)

    def test_no_future_data(self):
        timeline = build_loss_counter_timeline(self.df)

        state = get_loss_counters_at_tick(
            timeline, 10000
        )

        self.assertEqual(state["status"], "unavailable")
        self.assertIsNone(state["T"])

    def test_inconsistent_counters(self):
        df = pd.DataFrame([
            {
                "tick": 100,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 2,
            },
            {
                "tick": 100,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 3,
            },
        ])

        with self.assertRaises(ValueError):
            build_loss_counter_timeline(df)


if __name__ == "__main__":
    unittest.main()
