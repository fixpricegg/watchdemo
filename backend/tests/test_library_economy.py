
import unittest
from unittest.mock import patch

import pandas as pd

from library.builder import MatchLibrary


class TestLibraryEconomy(unittest.TestCase):

    def setUp(self):
        self.t_id = "76561198000000001"
        self.ct_id = "76561198000000002"

        positions = pd.DataFrame([
            {
                "tick": 100,
                "steamid": self.t_id,
                "name": "T_Player",
                "team_num": 2,
                "X": 100,
                "Y": 200,
                "Z": 0,
                "is_alive": True,
                "balance": 1000,
                "current_equip_value": 3000,
            },
            {
                "tick": 100,
                "steamid": self.ct_id,
                "name": "CT_Player",
                "team_num": 3,
                "X": 900,
                "Y": 800,
                "Z": 0,
                "is_alive": True,
                "balance": 5000,
                "current_equip_value": 7000,
            },
            {
                "tick": 120,
                "steamid": self.ct_id,
                "name": "CT_Player",
                "team_num": 3,
                "X": 950,
                "Y": 850,
                "Z": 0,
                "is_alive": True,
                "balance": 8000,
                "current_equip_value": 9000,
            },
        ])

        # Isolate the library from the real observation builder.
        # Nobody is known to have spotted an enemy in this fixture.
        self.visual_patch = patch(
            "library.builder.information.get_team_visual_state_at_tick",
            return_value=[],
        )
        self.visual_patch.start()
        self.addCleanup(self.visual_patch.stop)

        self.library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 90, 200)],
            team_observations={},
            team_spot_windows={},
        )

    def test_ground_truth_economy(self):
        state = self.library.get_game_state(
            100, self.t_id
        )

        self.assertEqual(
            state["economy"]["T"]["total_balance"],
            1000,
        )
        self.assertEqual(
            state["economy"]["CT"]["total_balance"],
            5000,
        )

    def test_team_economy_projection(self):
        t_input = self.library.get_decision_input(
            100, self.t_id
        )
        ct_input = self.library.get_decision_input(
            100, self.ct_id
        )

        self.assertEqual(
            t_input["team_economy"]["total_balance"],
            1000,
        )
        self.assertEqual(
            ct_input["team_economy"]["total_balance"],
            5000,
        )

        self.assertEqual(
            t_input["team_economy"]["team"], 2
        )
        self.assertEqual(
            ct_input["team_economy"]["team"], 3
        )

    def test_hidden_enemy_not_leaked(self):
        t_input = self.library.get_decision_input(
            100, self.t_id
        )

        self.assertNotIn("ground_truth", t_input)
        self.assertNotIn("economy", t_input)

        self.assertEqual(
            len(t_input["known_enemies"]), 0
        )
        self.assertEqual(
            len(t_input["team_players"]), 1
        )

        # The enemy's hidden snapshot must not be present.
        self.assertNotIn(
            self.ct_id, str(t_input)
        )

    def test_no_future_economy(self):
        state = self.library.get_game_state(
            110, self.t_id
        )

        # Tick 120 must not affect a request at tick 110.
        self.assertEqual(
            state["economy"]["CT"]["total_balance"],
            5000,
        )

    def test_loadout_projection(self):
        t_input = self.library.get_decision_input(
            100, self.t_id
        )

        ct_input = self.library.get_decision_input(
            100, self.ct_id
        )

        self.assertEqual(
            t_input["team_loadout"]["team"], 2
        )
        self.assertEqual(
            ct_input["team_loadout"]["team"], 3
        )

        self.assertNotIn("loadout", t_input)
        self.assertNotIn("ground_truth", t_input)

        self.assertNotIn(
            self.ct_id, str(t_input)
        )

    def test_round_start_snapshot(self):
        result = self.library.get_round_start_economy(
            100, self.t_id
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["live_start_tick"], 90)
        self.assertIsNone(result["teams"])

    def test_available_round_start_snapshot(self):
        import pandas as pd

        positions = pd.DataFrame([
            {
                "tick": 90,
                "steamid": self.t_id,
                "name": "T_Player",
                "team_num": 2,
                "X": 100,
                "Y": 200,
                "Z": 0,
                "round_start_equip_value": 4000,
            },
            {
                "tick": 90,
                "steamid": self.ct_id,
                "name": "CT_Player",
                "team_num": 3,
                "X": 900,
                "Y": 800,
                "Z": 0,
                "round_start_equip_value": 5000,
            },
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 90, 200)],
            team_observations={},
            team_spot_windows={},
        )

        result = library.get_round_start_economy(
            90, self.t_id
        )

        self.assertEqual(result["status"], "available")
        self.assertEqual(
            result["teams"]["T"]["observed_equipment_value"],
            4000,
        )
        self.assertEqual(
            result["teams"]["CT"]["observed_equipment_value"],
            5000,
        )

        # Two observed players do not constitute full teams.
        self.assertFalse(result["teams"]["T"]["complete"])
        self.assertFalse(result["teams"]["CT"]["complete"])


    def test_round_start_loadout(self):
        import pandas as pd

        positions = pd.DataFrame([
            {
                "tick": 90,
                "steamid": self.t_id,
                "name": "T_Player",
                "team_num": 2,
                "X": 100,
                "Y": 200,
                "Z": 0,
                "inventory": [
                    "AK-47",
                    "Glock-18",
                    "Smoke Grenade",
                    "Flashbang",
                ],
            },
            {
                "tick": 90,
                "steamid": self.ct_id,
                "name": "CT_Player",
                "team_num": 3,
                "X": 900,
                "Y": 800,
                "Z": 0,
                "inventory": [
                    "AWP",
                    "USP-S",
                    "Flashbang",
                ],
            },
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[(1, 1, 90, 200)],
            team_observations={},
            team_spot_windows={},
        )

        result = library.get_round_start_loadout(
            90, self.t_id
        )

        self.assertEqual(result["status"], "available")

        self.assertEqual(
            result["teams"]["T"]["primary_weapons"],
            ["AK-47"],
        )

        self.assertEqual(
            result["teams"]["CT"]["primary_weapons"],
            ["AWP"],
        )

        self.assertEqual(
            result["teams"]["T"]["grenades"]["smoke"],
            1,
        )


    def test_economy_history_first_round(self):
        result = self.library.get_economy_history(
            100, self.t_id
        )

        self.assertEqual(result["current_round"], 1)
        self.assertEqual(result["rounds_available"], 0)
        self.assertEqual(result["history"], [])

    def test_economy_history_no_future(self):
        import pandas as pd

        positions = pd.DataFrame([
            {
                "tick": tick,
                "steamid": steamid,
                "name": name,
                "team_num": team,
                "X": 100,
                "Y": 200,
                "Z": 0,
                "round_start_equip_value": value,
            }
            for tick, value in (
                (90, 200),
                (210, 4000),
                (410, 5000),
            )
            for steamid, name, team in (
                (self.t_id, "T_Player", 2),
                (self.ct_id, "CT_Player", 3),
            )
        ])

        library = MatchLibrary(
            map_name="de_nuke",
            position_df=positions,
            round_intervals=[
                (1, 1, 90, 200),
                (2, 2, 210, 350),
                (3, 3, 410, 550),
            ],
            team_observations={},
            team_spot_windows={},
        )

        result = library.get_economy_history(
            210, self.t_id
        )

        self.assertEqual(result["current_round"], 2)

        rounds = [
            entry["round"]
            for entry in result["history"]
        ]

        self.assertEqual(rounds, [1])

        self.assertEqual(
            result["history"][0]["teams"]["T"][
                "observed_equipment_value"
            ],
            200,
        )



if __name__ == "__main__":
    unittest.main()
