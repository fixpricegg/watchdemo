
import unittest
from copy import deepcopy

from library.candidate_actions import build_candidate_actions


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


if __name__ == "__main__":
    unittest.main()
