
import unittest

from library.economy_history import build_economy_history


class TestEconomyHistory(unittest.TestCase):

    def test_excludes_current_and_future(self):
        snapshots = []

        for round_number in range(1, 9):
            snapshots.append({
                "round": round_number,
                "live_start_tick": round_number * 100,
                "status": "available",
                "teams": {
                    "T": {
                        "post_buy_equipment_value":
                            round_number * 1000,
                    }
                },
            })

        result = build_economy_history(
            snapshots,
            current_round=7,
            limit=5,
        )

        numbers = [
            entry["round"]
            for entry in result["history"]
        ]

        self.assertEqual(numbers, [2, 3, 4, 5, 6])
        self.assertEqual(result["rounds_available"], 5)

    def test_missing_data_preserved(self):
        snapshots = [
            {
                "round": 1,
                "status": "unavailable",
                "teams": None,
            },
            {
                "round": 2,
                "status": "available",
                "teams": {
                    "T": {
                        "post_buy_equipment_value": None,
                    },
                },
            },
        ]

        result = build_economy_history(
            snapshots,
            current_round=3,
        )

        self.assertIsNone(
            result["history"][0]["teams"]
        )

        self.assertIsNone(
            result["history"][1]["teams"]["T"][
                "post_buy_equipment_value"
            ]
        )


if __name__ == "__main__":
    unittest.main()
