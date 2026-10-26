
import unittest
from copy import deepcopy
from unittest.mock import Mock

from library.builder import MatchLibrary


class TestTeamKnowledgeSnapshot(unittest.TestCase):

    def setUp(self):
        self.library = MatchLibrary.__new__(MatchLibrary)

        self.state = {
            "tick": 200,
            "round": {"number": 3},
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
            "ground_truth": {
                "players": [
                    {
                        "steamid": "456",
                        "team": 3,
                        "position": {
                            "x": 900,
                            "y": 500,
                        },
                    },
                ]
            },
            "team_knowledge": {
                "visual_enemies": [],
            },
        }

        self.library.get_game_state = Mock(
            return_value=self.state
        )

    def test_hidden_enemy_not_exposed(self):
        result = self.library.get_team_knowledge_snapshot(
            200, "123"
        )

        self.assertNotIn(
            "ground_truth", result
        )
        self.assertNotIn(
            "900", str(result)
        )

    def test_missing_voice_explicit(self):
        result = self.library.get_team_knowledge_snapshot(
            200, "123"
        )

        self.assertEqual(
            result["source_coverage"]["voice"],
            "unavailable",
        )
        self.assertEqual(
            result["completeness"], "partial"
        )

    def test_snapshot_copy(self):
        result = self.library.get_team_knowledge_snapshot(
            200, "123"
        )
        result["perspective"]["team"] = 3

        self.assertEqual(
            self.state["perspective"]["team"], 2
        )


if __name__ == "__main__":
    unittest.main()
