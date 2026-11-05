
import unittest

from detectors.buy_mismatch import detect_buy_mismatch


class FakeLibrary:
    round_intervals = [(2, 2, 100, 200)]

    def __init__(self, balance=4000, equipment=650):
        self.balance = balance
        self.equipment = equipment

    def get_game_state(self, tick, player):
        values = [self.equipment, 3500, 3800, 4200, 900]

        players = []

        for i, value in enumerate(values):
            players.append({
                "steamid": str(123 + i),
                "team": 3,
                "economy": {
                    "current_equip_value": value,
                    "balance": self.balance if i == 0 else 500,
                },
            })

        return {
            "perspective": {
                "steamid": "123",
                "team": 3,
            },
            "ground_truth": {"players": players},
        }


class TestBuyMismatch(unittest.TestCase):

    def test_mismatch_candidate(self):
        result = detect_buy_mismatch(FakeLibrary(), "123")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["round"], 2)
        self.assertEqual(result[0]["tick"], 100)
        self.assertEqual(result[0]["status"], "review_required")

    def test_no_money(self):
        result = detect_buy_mismatch(
            FakeLibrary(balance=300), "123"
        )
        self.assertEqual(result, [])

    def test_equipped_player(self):
        result = detect_buy_mismatch(
            FakeLibrary(equipment=3600), "123"
        )
        self.assertEqual(result, [])

    def test_missing_equipment(self):
        result = detect_buy_mismatch(
            FakeLibrary(equipment=None), "123"
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
