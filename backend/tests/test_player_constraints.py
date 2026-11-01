
import unittest

from library.player_constraints import assess_player_constraints


class TestPlayerConstraints(unittest.TestCase):

    def player(self, **changes):
        result = {
            "sample_tick": 100,
            "status": {
                "is_alive": True,
                "flash_duration": 0,
            },
            "weapon": {
                "active": "ak47",
                "clip_ammo": 20,
                "is_reloading": False,
            },
        }

        for key, value in changes.items():
            if key in result["status"]:
                result["status"][key] = value
            elif key in result["weapon"]:
                result["weapon"][key] = value

        return result

    def test_normal_state(self):
        result = assess_player_constraints(
            self.player(), tick=100
        )
        self.assertEqual(
            result["status"], "no_observed_limitation"
        )
        self.assertEqual(
            result["shooting_feasibility"], "not_established"
        )

    def test_flash(self):
        result = assess_player_constraints(
            self.player(flash_duration=2.0), tick=100
        )
        self.assertIn(
            "flash_effect_observed", result["limitations"]
        )

    def test_reload(self):
        result = assess_player_constraints(
            self.player(is_reloading=True), tick=100
        )
        self.assertIn("reloading", result["limitations"])

    def test_empty_magazine(self):
        result = assess_player_constraints(
            self.player(clip_ammo=0), tick=100
        )
        self.assertIn(
            "magazine_empty", result["limitations"]
        )

    def test_missing_information(self):
        result = assess_player_constraints(
            self.player(is_reloading=None), tick=100
        )
        self.assertEqual(result["status"], "partial")
        self.assertIn(
            "is_reloading", result["unknown_fields"]
        )

    def test_stale_state(self):
        result = assess_player_constraints(
            self.player(), tick=120, max_age_ticks=16
        )
        self.assertEqual(result["status"], "unknown")
        self.assertIn(
            "stale_player_state", result["limitations"]
        )

    def test_future_sample_rejected(self):
        result = assess_player_constraints(
            self.player(), tick=99
        )
        self.assertEqual(result["status"], "unknown")

    def test_dead_player(self):
        result = assess_player_constraints(
            self.player(is_alive=False), tick=100
        )
        self.assertEqual(result["status"], "unavailable")

    def test_invalid_flash(self):
        result = assess_player_constraints(
            self.player(flash_duration=float("nan")),
            tick=100,
        )
        self.assertIn(
            "flash_duration", result["unknown_fields"]
        )


if __name__ == "__main__":
    unittest.main()
