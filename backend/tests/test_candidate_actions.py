
import unittest
from copy import deepcopy

from library.candidate_actions import build_candidate_actions


class FakeGeometry:
    def __init__(self, connected=True):
        self.connected = connected
        self.areas = {
            1: {"id": 1, "center": {"x": 0, "y": 0, "z": 0}},
            2: {"id": 2, "center": {"x": 100, "y": 0, "z": 0}},
        }

    def find_area(self, x, y, z):
        if x == 0:
            return self.areas[1]
        if x == 100:
            return self.areas[2]
        return None

    def shortest_path(self, start_id, end_id):
        if start_id == end_id:
            return [start_id]
        if self.connected:
            return [start_id, end_id]
        return None

    def area_distance(self, a, b):
        return abs(a["center"]["x"] - b["center"]["x"])


class TestCandidateActions(unittest.TestCase):

    def setUp(self):
        self.context = {
            "tick": 150,
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
            "known_enemies": [],
            "player_utility": {
                "status": "observed",
                "counts": {
                    "flashbang": 1,
                    "smokegrenade": 0,
                },
            },
        }

        self.players = [
            {
                "steamid": "123",
                "sample_tick": 150,
                "position": {
                    "x": 0, "y": 0, "z": 0,
                },
                "status": {"is_alive": True},
            },
            {
                "steamid": "456",
                "sample_tick": 149,
                "position": {
                    "x": 100, "y": 0, "z": 0,
                },
                "status": {"is_alive": True},
            },
        ]

    def generate(self):
        return build_candidate_actions(
            self.context,
            team_players=self.players,
        )

    def test_hold_position(self):
        actions = self.generate()

        hold = next(
            a for a in actions
            if a["id"] == "hold_position"
        )

        self.assertEqual(hold["feasibility"], "available")
        self.assertIsNone(hold["score"])

    def test_regroup_requires_validation(self):
        actions = self.generate()

        regroup = next(
            a for a in actions
            if a["type"] == "regroup"
        )

        self.assertEqual(
            regroup["feasibility"],
            "requires_validation",
        )
        self.assertIsNone(regroup["parameters"]["route"])

    def test_known_utility_only(self):
        actions = self.generate()
        ids = [a["id"] for a in actions]

        self.assertIn("consider_flashbang", ids)
        self.assertNotIn("consider_smokegrenade", ids)

    def test_no_future_teammate_state(self):
        self.players[1]["sample_tick"] = 151

        actions = self.generate()

        self.assertFalse(any(
            a["type"] == "regroup"
            for a in actions
        ))

    def test_stale_player_blocks_generation(self):
        self.players[0]["sample_tick"] = 100

        self.assertEqual(self.generate(), [])

    def test_dead_player_has_no_actions(self):
        self.players[0]["status"]["is_alive"] = False

        self.assertEqual(self.generate(), [])

    def test_no_enemy_ground_truth_dependency(self):
        first = self.generate()

        changed = deepcopy(self.context)
        changed["ground_truth"] = {
            "players": [{
                "steamid": "enemy",
                "position": {
                    "x": 1,
                    "y": 1,
                    "z": 1,
                },
            }]
        }

        second = build_candidate_actions(
            changed,
            team_players=self.players,
        )

        self.assertEqual(first, second)

    def test_output_is_not_evaluation(self):
        for action in self.generate():
            self.assertIsNone(action["score"])
            self.assertIsNone(action["rank"])
            self.assertEqual(
                action["evaluation_status"],
                "not_evaluated",
            )

    def test_missing_actor(self):
        self.assertEqual(
            build_candidate_actions(
                self.context,
                team_players=[],
            ),
            [],
        )


    def test_navigation_connected(self):
        actions = build_candidate_actions(
            self.context,
            team_players=self.players,
            geometry=FakeGeometry(),
        )

        regroup = next(
            a for a in actions if a["type"] == "regroup"
        )

        nav = regroup["parameters"]["navigation"]

        self.assertEqual(nav["status"], "nav_connected")
        self.assertEqual(nav["area_path"], [1, 2])
        self.assertEqual(nav["distance_estimate"], 100.0)
        self.assertIsNone(regroup["parameters"]["route"])
        self.assertEqual(
            regroup["feasibility"],
            "requires_validation",
        )
        self.assertIsNone(regroup["score"])

    def test_navigation_disconnected(self):
        actions = build_candidate_actions(
            self.context,
            team_players=self.players,
            geometry=FakeGeometry(connected=False),
        )

        regroup = next(
            a for a in actions if a["type"] == "regroup"
        )

        nav = regroup["parameters"]["navigation"]

        self.assertEqual(nav["status"], "no_nav_path")
        self.assertIsNone(nav["area_path"])
        self.assertIsNone(regroup["parameters"]["route"])
        self.assertEqual(
            regroup["feasibility"],
            "requires_validation",
        )

    def test_navigation_unknown_area(self):
        self.players[1]["position"]["x"] = 500

        actions = build_candidate_actions(
            self.context,
            team_players=self.players,
            geometry=FakeGeometry(),
        )

        regroup = next(
            a for a in actions if a["type"] == "regroup"
        )

        self.assertEqual(
            regroup["parameters"]["navigation"]["status"],
            "area_unknown",
        )



if __name__ == "__main__":
    unittest.main()
