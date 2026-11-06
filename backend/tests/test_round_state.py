
import unittest

from library.round_state import build_round_state


class TestRoundState(unittest.TestCase):

    def make_state(self, players, results=None, tick=150):
        return build_round_state(
            tick=tick,
            round_info={
                "number": 2,
                "live_start_tick": 100,
            },
            players=players,
            completed_results=results or [],
        )

    def test_alive_counts(self):
        players = []

        for i in range(5):
            players.append({
                "steamid": str(i),
                "team": 2,
                "status": {"is_alive": i != 0},
            })
            players.append({
                "steamid": str(i + 5),
                "team": 3,
                "status": {"is_alive": i < 3},
            })

        result = self.make_state(players)

        self.assertEqual(result["alive"]["T"], 4)
        self.assertEqual(result["alive"]["CT"], 3)

    def test_missing_player_is_unknown(self):
        result = self.make_state([
            {"team": 2, "status": {"is_alive": True}},
        ])

        self.assertIsNone(result["alive"]["T"])
        self.assertIsNone(result["alive"]["CT"])

    def test_unknown_alive_is_not_dead(self):
        players = [
            {"team": 2, "status": {}}
            for _ in range(5)
        ]

        result = self.make_state(players)
        self.assertIsNone(result["alive"]["T"])

    def test_completed_results_only(self):
        result = self.make_state(
            [],
            results=[
                {"winner": "T"},
                {"winner": "CT"},
            ],
        )

        self.assertEqual(
            result["completed_wins_by_side"],
            {"T": 1, "CT": 1},
        )

    def test_no_future_end_tick(self):
        result = self.make_state([])
        self.assertNotIn("end_tick", result)

    def test_unknown_bomb_is_not_unplanted(self):
        result = self.make_state([])
        self.assertEqual(result["bomb"]["status"], "unknown")
        self.assertIsNone(result["clock"]["remaining_seconds"])


if __name__ == "__main__":
    unittest.main()
