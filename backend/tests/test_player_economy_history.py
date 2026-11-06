
import unittest
import pandas as pd

from library.player_economy_history import (
    build_player_economy_history,
)


class TestPlayerEconomyHistory(unittest.TestCase):

    def setUp(self):
        self.stream = pd.DataFrame([
            {
                "tick": 100,
                "steamid": "76561198000000001",
                "team_num": 2,
                "balance": 1000,
                "current_equip_value": 4000,
                "inventory": ["AK-47", "Glock-18"],
                "is_alive": True,
            },
            {
                "tick": 150,
                "steamid": "76561198000000001",
                "team_num": 2,
                "balance": 1000,
                "current_equip_value": 4000,
                "inventory": ["AK-47", "Glock-18"],
                "is_alive": False,
            },
            {
                "tick": 300,
                "steamid": "76561198000000001",
                "team_num": 2,
                "balance": 2500,
                "current_equip_value": 700,
                "inventory": ["Desert Eagle"],
                "is_alive": True,
            },
        ])

        self.rounds = [
            (1, 1, 100, 200),
            (2, 2, 300, 400),
        ]

    def test_history(self):
        history = build_player_economy_history(
            self.stream, self.rounds
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(
            history[0]["post_buy"]["economy"]["balance"],
            1000,
        )
        self.assertEqual(
            history[0]["last_observed"]["sample_tick"],
            150,
        )

        self.assertIsNone(
            history[0]["carried_equipment"]
        )

    def test_no_future_rounds(self):
        history = build_player_economy_history(
            self.stream,
            self.rounds,
            current_tick=200,
        )

        self.assertEqual(len(history), 1)

    def test_missing_start_snapshot(self):
        stream = self.stream[
            self.stream["tick"] != 100
        ]

        history = build_player_economy_history(
            stream, self.rounds
        )

        self.assertIsNone(history[0]["post_buy"])
        self.assertEqual(
            history[0]["first_observed_tick"],
            150,
        )

    def test_equipment_status(self):
        history = build_player_economy_history(
            self.stream,
            self.rounds,
        )

        equipment = history[0]["post_buy"]["equipment_status"]

        self.assertIn("armor", equipment)
        self.assertIn("has_helmet", equipment)
        self.assertIn("has_defuser", equipment)


    def test_confirmed_death(self):
        from library.player_economy_history import (
            get_round_survival,
        )

        result = get_round_survival(
            player_death_ticks=[150, 350],
            live_start_tick=100,
            end_tick=200,
            death_data_complete=True,
        )

        self.assertEqual(result["status"], "died")
        self.assertFalse(result["survived"])
        self.assertEqual(result["death_tick"], 150)

    def test_confirmed_survival(self):
        from library.player_economy_history import (
            get_round_survival,
        )

        result = get_round_survival(
            player_death_ticks=[350],
            live_start_tick=100,
            end_tick=200,
            death_data_complete=True,
        )

        self.assertEqual(result["status"], "survived")
        self.assertTrue(result["survived"])

    def test_incomplete_death_information(self):
        from library.player_economy_history import (
            get_round_survival,
        )

        result = get_round_survival(
            player_death_ticks=[],
            live_start_tick=100,
            end_tick=200,
            death_data_complete=False,
        )

        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["survived"])



    def test_library_round_survival(self):
        from library.builder import MatchLibrary

        steamid = "76561198000000001"

        positions = pd.DataFrame([
            {
                "tick": 100,
                "steamid": steamid,
                "name": "TestPlayer",
                "team_num": 2,
            },
            {
                "tick": 300,
                "steamid": steamid,
                "name": "TestPlayer",
                "team_num": 2,
            },
        ])

        deaths = pd.DataFrame([
            {
                "tick": 150,
                "user_steamid": steamid,
                "attacker_steamid": "76561198000000002",
            },
            {
                "tick": 320,
                "user_steamid": "76561198000000002",
                "attacker_steamid": steamid,
            },
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[
                (1, 1, 100, 200),
                (2, 2, 300, 400),
            ],
            deaths_df=deaths,
            team_observations={},
            team_spot_windows={},
        )

        history = library.get_player_economy_history(steamid)

        self.assertEqual(
            history[0]["survival"]["status"],
            "died",
        )
        self.assertEqual(
            history[0]["survival"]["death_tick"],
            150,
        )

        self.assertEqual(
            history[1]["survival"]["status"],
            "survived",
        )
        self.assertTrue(
            history[1]["survival"]["survived"]
        )


    def test_saved_equipment_survivor(self):
        from library.player_economy_history import (
            get_saved_equipment_candidate,
        )

        record = {
            "end_tick": 200,
            "survival": {"status": "survived"},
            "last_observed": {
                "sample_tick": 195,
                "is_alive": True,
                "inventory": ["AK-47", "Smoke Grenade"],
                "equipment_status": {
                    "armor": 72,
                    "has_helmet": True,
                    "has_defuser": False,
                },
            },
        }

        result = get_saved_equipment_candidate(record)

        self.assertEqual(
            result["status"], "observed_near_end"
        )
        self.assertEqual(result["age_ticks"], 4)
        self.assertIn("AK-47", result["inventory"])
        self.assertEqual(
            result["equipment_status"]["armor"], 72
        )

    def test_saved_equipment_died(self):
        from library.player_economy_history import (
            get_saved_equipment_candidate,
        )

        record = {
            "end_tick": 200,
            "survival": {"status": "died"},
            "last_observed": {
                "sample_tick": 195,
                "is_alive": False,
                "inventory": ["AWP"],
            },
        }

        result = get_saved_equipment_candidate(record)

        self.assertEqual(result["status"], "died")
        self.assertIsNone(result["inventory"])

    def test_saved_equipment_stale(self):
        from library.player_economy_history import (
            get_saved_equipment_candidate,
        )

        record = {
            "end_tick": 200,
            "survival": {"status": "survived"},
            "last_observed": {
                "sample_tick": 150,
                "is_alive": True,
                "inventory": ["AWP"],
            },
        }

        result = get_saved_equipment_candidate(record)

        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["inventory"])


    def test_prebuy_integration(self):
        from library.builder import MatchLibrary

        steamid = "76561198000000001"

        positions = pd.DataFrame([{
            "tick": 100,
            "steamid": steamid,
            "name": "Player",
            "team_num": 2,
        }])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 100, 200)],
            prebuy_snapshots={
                (1, steamid): {
                    "inventory": ["AK-47"],
                    "economy": {
                        "balance": 5000,
                        "cash_spent_this_round": 0,
                    },
                },
            },
            team_observations={},
            team_spot_windows={},
        )

        history = library.get_player_economy_history(
            steamid
        )

        self.assertEqual(
            history[0]["pre_buy"]["inventory"],
            ["AK-47"],
        )

    def test_missing_prebuy(self):
        from library.builder import MatchLibrary

        steamid = "76561198000000001"

        positions = pd.DataFrame([{
            "tick": 100,
            "steamid": steamid,
            "name": "Player",
            "team_num": 2,
        }])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 100, 200)],
            team_observations={},
            team_spot_windows={},
        )

        history = library.get_player_economy_history(
            steamid
        )

        self.assertIsNone(history[0]["pre_buy"])



if __name__ == "__main__":
    unittest.main()
