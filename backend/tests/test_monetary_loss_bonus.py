
import unittest
import pandas as pd

from library.builder import MatchLibrary
from library.loss_bonus import (
    CT_LOSS_FIELD,
    T_LOSS_FIELD,
    counter_to_loss_reward,
    build_loss_counter_timeline,
    get_next_loss_reward,
    get_loss_reward_for_round,
)


class TestMonetaryLossBonus(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame([
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
                "tick": 25412,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 4,
            },
            {
                "tick": 25413,
                CT_LOSS_FIELD: 1,
                T_LOSS_FIELD: 2,
            },
        ])

        self.timeline = build_loss_counter_timeline(
            self.df
        )

    def test_reward_scale(self):
        expected = {
            0: 1400,
            1: 1900,
            2: 2400,
            3: 2900,
            4: 3400,
            5: 3400,
        }

        for counter, reward in expected.items():
            self.assertEqual(
                counter_to_loss_reward(counter),
                reward,
            )

        self.assertIsNone(counter_to_loss_reward(None))
        self.assertIsNone(counter_to_loss_reward(-1))

    def test_reward_before_round_end(self):
        result = get_loss_reward_for_round(
            self.timeline,
            {
                "round": 2,
                "result_tick": 14351,
                "winner_side": "CT",
                "loser_side": "T",
            },
        )

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["base_loss_reward"], 2400)
        self.assertEqual(result["counter_before_result"], 2)
        self.assertEqual(result["counter_after_result"], 3)

    def test_ct_reward(self):
        result = get_loss_reward_for_round(
            self.timeline,
            {
                "round": 4,
                "result_tick": 25413,
                "winner_side": "T",
                "loser_side": "CT",
            },
        )

        self.assertEqual(result["base_loss_reward"], 1400)

    def test_missing_exact_sample(self):
        result = get_loss_reward_for_round(
            self.timeline,
            {
                "round": 3,
                "result_tick": 19323,
                "winner_side": "CT",
                "loser_side": "T",
            },
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["base_loss_reward"])

    def test_no_stale_reward(self):
        result = get_next_loss_reward(
            self.timeline, 14352
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(
            result["base_reward_if_lost_now"]["T"]
        )

    def test_economy_history_integration(self):
        t_id = "76561198000000001"
        ct_id = "76561198000000002"

        positions = pd.DataFrame([
            {
                "tick": tick,
                "steamid": steamid,
                "name": name,
                "team_num": team,
                "X": 100,
                "Y": 200,
                "Z": 0,
                "round_start_equip_value": 200,
                "current_equip_value": 3000,
            }
            for tick in (90, 210)
            for steamid, name, team in (
                (t_id, "T_Player", 2),
                (ct_id, "CT_Player", 3),
            )
        ])

        counters = pd.DataFrame([
            {
                "tick": 179,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 1,
            },
            {
                "tick": 180,
                CT_LOSS_FIELD: 0,
                T_LOSS_FIELD: 2,
            },
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[
                (1, 1, 90, 200),
                (2, 2, 210, 350),
            ],
            round_ends=pd.DataFrame([
                {"tick": 180, "winner": "CT"},
            ]),
            loss_counter_df=counters,
            team_observations={},
            team_spot_windows={},
        )

        history = library.get_economy_history(
            210, t_id
        )

        self.assertEqual(history["rounds_available"], 1)

        record = history["history"][0]

        self.assertEqual(
            record["round_result"]["winner_side"],
            "CT",
        )

        self.assertEqual(
            record["loss_bonus"]["base_loss_reward"],
            1900,
        )

        self.assertEqual(
            record["loss_bonus"]["status"],
            "available",
        )


if __name__ == "__main__":
    unittest.main()
