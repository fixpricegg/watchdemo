
import unittest

from library.player_effects import build_player_effects


class TestPlayerEffects(unittest.TestCase):

    def player(self, steamid, flash):
        return {
            "steamid": steamid,
            "sample_tick": 100,
            "status": {
                "is_alive": True,
                "flash_duration": flash,
            },
        }

    def test_multiple_players(self):
        result = build_player_effects(
            [
                self.player("111", 2.5),
                self.player("222", 0),
                self.player("333", None),
            ],
            tick=100,
        )

        self.assertEqual(len(result["players"]), 3)
        self.assertEqual(
            result["players"][0]["flash"]["status"],
            "observed_active",
        )
        self.assertEqual(
            result["players"][1]["flash"]["status"],
            "observed_inactive",
        )
        self.assertEqual(
            result["players"][2]["flash"]["status"],
            "unknown",
        )

    def test_no_fabricated_smoke_exposure(self):
        result = build_player_effects(
            [self.player("111", 0)],
            tick=100,
            active_utility={
                "status": "observed",
                "ongoing_candidates": [{"type": "smoke"}],
            },
        )

        self.assertEqual(
            result["players"][0]["smoke_exposure"],
            "not_evaluated",
        )

    def test_no_fabricated_he_damage(self):
        result = build_player_effects(
            [self.player("111", 0)],
            tick=100,
            recent_explosions=[{"tick": 95}],
        )

        self.assertEqual(
            result["players"][0]["he_damage"],
            "not_evaluated",
        )
        self.assertEqual(
            len(result["recent_he_explosions"]), 1
        )

    def test_invalid_flash(self):
        result = build_player_effects(
            [self.player("111", float("nan"))],
            tick=100,
        )

        self.assertEqual(
            result["players"][0]["flash"]["status"],
            "unknown",
        )


class TestPlayerEffectsIntegration(unittest.TestCase):

    def test_match_library_effects(self):
        from library.builder import MatchLibrary

        class FakeLibrary:
            event_timeline = None
            get_player_effects = MatchLibrary.get_player_effects

            def get_game_state(self, tick, player):
                return {
                    "tick": tick,
                    "round": {"number": 1},
                    "ground_truth": {
                        "players": [
                            {
                                "steamid": "123",
                                "sample_tick": tick,
                                "status": {
                                    "is_alive": True,
                                    "flash_duration": 1.5,
                                },
                            }
                        ],
                    },
                }

        library = FakeLibrary()

        result = library.get_player_effects(100, "123")

        self.assertEqual(len(result["players"]), 1)
        self.assertEqual(
            result["players"][0]["flash"]["status"],
            "observed_active",
        )
        self.assertEqual(
            result["players"][0]["flash"]["remaining_duration"],
            1.5,
        )
        self.assertEqual(
            result["world_effects"]["status"],
            "unavailable",
        )


if __name__ == "__main__":
    unittest.main()
