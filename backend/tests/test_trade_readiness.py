
import unittest

from library.trade_readiness import assess_trade_readiness


class TestTradeReadiness(unittest.TestCase):

    def make_player(self, flash=0, reload=False, ammo=20):
        return {
            "status": {
                "is_alive": True,
                "flash_duration": flash,
            },
            "weapon": {
                "is_reloading": reload,
                "clip_ammo": ammo,
            },
        }

    def test_ready(self):
        result = assess_trade_readiness(self.make_player())
        self.assertEqual(
            result["status"], "no_observed_limitation"
        )

    def test_flash(self):
        result = assess_trade_readiness(
            self.make_player(flash=2.5)
        )
        self.assertEqual(result["status"], "limited")
        self.assertIn(
            "flash_effect_active", result["reasons"]
        )

    def test_reload(self):
        result = assess_trade_readiness(
            self.make_player(reload=True)
        )
        self.assertIn("reloading", result["reasons"])

    def test_empty_magazine(self):
        result = assess_trade_readiness(
            self.make_player(ammo=0)
        )
        self.assertIn(
            "magazine_empty", result["reasons"]
        )

    def test_dead(self):
        player = self.make_player()
        player["status"]["is_alive"] = False

        result = assess_trade_readiness(player)
        self.assertEqual(result["status"], "unavailable")

    def test_missing_player(self):
        result = assess_trade_readiness(None)
        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
