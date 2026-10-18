
import unittest

from library.economy import build_round_economy


class TestEconomy(unittest.TestCase):

    def test_team_economy(self):
        players = [
            {
                "team": 2,
                "status": {"is_alive": True},
                "economy": {
                    "balance": 1800,
                    "current_equip_value": 4200,
                },
            },
            {
                "team": 2,
                "status": {"is_alive": False},
                "economy": {
                    "balance": 400,
                    "current_equip_value": 800,
                },
            },
        ]

        result = build_round_economy(players)

        self.assertEqual(
            result["T"]["total_balance"],
            2200,
        )

        self.assertEqual(
            result["T"]["total_equipment_value"],
            5000,
        )

        self.assertEqual(
            result["T"]["alive_count"],
            1,
        )

    def test_missing_money(self):
        players = [
            {
                "team": 3,
                "status": {"is_alive": True},
                "economy": {"balance": None},
            },
        ]

        result = build_round_economy(players)

        self.assertIsNone(
            result["CT"]["total_balance"]
        )


if __name__ == "__main__":
    unittest.main()
