
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


    def test_player_loadout(self):
        from library.economy import build_player_loadout

        player = {
            "team": 2,
            "inventory": [
                "Butterfly Knife",
                "Glock-18",
                "Smoke Grenade",
                "Molotov",
                "Flashbang",
                "AK-47",
                "C4 Explosive",
            ],
            "status": {
                "armor": 100,
                "has_helmet": True,
                "has_defuser": False,
            },
        }

        loadout = build_player_loadout(player)

        self.assertEqual(loadout["primary"], "AK-47")
        self.assertEqual(loadout["secondary"], "Glock-18")
        self.assertEqual(loadout["grenades"]["smoke"], 1)
        self.assertEqual(loadout["grenades"]["flash"], 1)
        self.assertTrue(loadout["has_bomb"])
        self.assertEqual(loadout["armor"], 100)
        self.assertEqual(loadout["unclassified"], [])

    def test_unknown_inventory(self):
        from library.economy import build_player_loadout

        player = {
            "team": 3,
            "inventory": None,
            "status": {"armor": 50},
        }

        loadout = build_player_loadout(player)

        self.assertEqual(loadout["status"], "unknown")
        self.assertIsNone(loadout["grenades"])
        self.assertIsNone(loadout["has_bomb"])
        self.assertEqual(loadout["armor"], 50)



if __name__ == "__main__":
    unittest.main()
