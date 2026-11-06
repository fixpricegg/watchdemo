import unittest

from library.utility_state import (
    normalize_grenade_name,
    build_player_utility_from_inventory,
    build_team_utility,
    build_round_utility_timeline,
)


class TestUtilityState(unittest.TestCase):
    def test_normalize_grenade_name(self):
        self.assertEqual(normalize_grenade_name("Smoke Grenade"), "smoke")
        self.assertEqual(normalize_grenade_name("Flashbang"), "flash")
        self.assertEqual(normalize_grenade_name("HE Grenade"), "he")
        self.assertEqual(normalize_grenade_name("High Explosive Grenade"), "he")
        self.assertEqual(normalize_grenade_name("Molotov"), "molotov")
        self.assertEqual(normalize_grenade_name("Incendiary Grenade"), "incendiary")
        self.assertEqual(normalize_grenade_name("Decoy Grenade"), "decoy")
        self.assertIsNone(normalize_grenade_name("AK-47"))

    def test_build_player_utility_from_inventory(self):
        player = {
            "inventory": [
                "AK-47",
                "Smoke Grenade",
                "Flashbang",
                "Flashbang",
                "Molotov",
            ]
        }
        result = build_player_utility_from_inventory(player)
        self.assertEqual(result["smoke"], 1)
        self.assertEqual(result["flash"], 2)
        self.assertEqual(result["molotov"], 1)
        self.assertEqual(result["total"], 4)

    def test_build_team_utility(self):
        players = [
            {"inventory": ["Smoke Grenade", "Flashbang"]},
            {"inventory": ["Flashbang", "HE Grenade"]},
        ]
        result = build_team_utility(players)
        self.assertEqual(result["smoke"], 1)
        self.assertEqual(result["flash"], 2)
        self.assertEqual(result["he"], 1)
        self.assertEqual(result["total"], 4)

    def test_round_utility_timeline(self):
        rows = [
            {"tick": 110, "type": "smoke", "thrower": "a"},
            {"tick": 150, "type": "flash", "thrower": "b"},
            {"tick": 250, "type": "he", "thrower": "c"},
        ]
        rounds = [
            (1, 1, 100, 200),
            (2, 2, 200, 300),
        ]
        result = build_round_utility_timeline(rows, rounds)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]["events"]), 2)
        self.assertEqual(len(result[1]["events"]), 1)

    def test_no_future_leakage(self):
        rows = [
            {"tick": 110, "type": "smoke"},
            {"tick": 150, "type": "flash"},
            {"tick": 250, "type": "he"},
        ]
        rounds = [
            (1, 1, 100, 200),
            (2, 2, 200, 300),
        ]
        result = build_round_utility_timeline(rows, rounds, current_tick=160)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["events"]), 2)