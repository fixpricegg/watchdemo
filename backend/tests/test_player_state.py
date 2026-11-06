import unittest
import pandas as pd

from library.game_state import player_from_row


class TestPlayerState(unittest.TestCase):

    def setUp(self):
        self.row = {
            "tick": 43682,
            "steamid": "76561199636557537",
            "name": "wesiqe",
            "team_num": 2,
            "X": 100.0,
            "Y": 200.0,
            "Z": -50.0,
            "yaw": 90.0,
            "pitch": -12.5,
            "velocity": 245.0,
            "velocity_X": 100.0,
            "velocity_Y": 200.0,
            "velocity_Z": 0.0,
            "is_walking": False,
            "is_airborne": False,
            "in_crouch": True,
            "duck_amount": 0.8,
            "health": 78,
            "armor": 92,
            "has_helmet": True,
            "is_alive": True,
            "balance": 1800,
            "current_equip_value": 4200,
            "active_weapon_name": "ak47",
            "active_weapon_ammo": 21,
            "total_ammo_left": 60,
            "is_in_reload": False,
            "is_scoped": False,
            "inventory": ["ak47", "flashbang"],
        }

    def test_player_state(self):
        player = player_from_row(self.row)

        self.assertEqual(player["position"]["x"], 100.0)
        self.assertEqual(player["view"]["pitch"], -12.5)
        self.assertEqual(player["movement"]["duck_amount"], 0.8)
        self.assertEqual(player["status"]["health"], 78)
        self.assertEqual(player["economy"]["balance"], 1800)
        self.assertEqual(player["weapon"]["clip_ammo"], 21)

    def test_missing_fields(self):
        row = self.row.copy()
        row["balance"] = pd.NA
        row["pitch"] = None

        player = player_from_row(row)

        self.assertIsNone(player["economy"]["balance"])
        self.assertIsNone(player["view"]["pitch"])


if __name__ == "__main__":
    unittest.main()