
import unittest
import pandas as pd

from library.predeath_support import build_predeath_support
from library.builder import MatchLibrary


class FakeLibrary:
    def __init__(self):
        self.max_state_age_ticks = 16
        self.team_observations = []

        self.player_streams = {
            "123": pd.DataFrame([
                self.row(110, "123", 0),
                self.row(120, "123", 10),
                self.row(140, "123", 20),
                self.row(160, "123", 30),
            ]),
            "456": pd.DataFrame([
                self.row(108, "456", 40),
                self.row(120, "456", 45),
                self.row(130, "456", 55),
                self.row(155, "456", 60),
            ]),
        }

        self.events = [
            self.event(115, "weapon_fire", "456"),
            self.event(125, "player_hurt", "900", "456"),
            self.event(130, "player_hurt", "123", "900"),
            self.event(145, "weapon_fire", "123"),
            self.event(151, "player_hurt", "900", "123"),
        ]

    def row(self, tick, steamid, x):
        return {
            "tick": tick,
            "steamid": steamid,
            "team_num": 2,
            "name": steamid,
            "X": x,
            "Y": 0,
            "Z": 0,
            "is_alive": True,
            "flash_duration": 0,
            "active_weapon_name": "ak47",
            "active_weapon_ammo": 20,
            "is_in_reload": False,
        }

    def event(self, tick, event_type, actor, victim=None):
        return {
            "tick": tick,
            "type": event_type,
            "kind": "combat",
            "data": {
                "actor_steamid": actor,
                "victim_steamid": victim,
            },
        }

    def get_combat_window(self, start, end):
        return {
            "status": "sources_parsed",
            "parse_status": {
                "weapon_fire": "parsed",
                "player_hurt": "parsed",
            },
            "events": [
                e for e in self.events
                if start <= e["tick"] <= end
            ],
        }

    def get_game_state(self, tick, player):
        return {
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
            "round": {
                "number": 1,
                "live_start_tick": 100,
                "end_tick": 300,
            },
        }


class TestPredeathSupport(unittest.TestCase):
    def setUp(self):
        self.library = FakeLibrary()

    def assess(self, **changes):
        values = {
            "player_id": "123",
            "teammate_id": "456",
            "killer_id": "900",
            "observer_team": 2,
            "round_number": 1,
            "round_start_tick": 100,
            "death_tick": 150,
            "lookback_ticks": 50,
        }
        values.update(changes)
        return build_predeath_support(self.library, **values)

    def test_aligned_samples(self):
        result = self.assess()
        samples = result["position_samples"]

        self.assertEqual(
            [s["tick"] for s in samples],
            [110, 120, 140],
        )
        self.assertEqual(
            [s["teammate_sample_tick"] for s in samples],
            [108, 120, 130],
        )

    def test_no_future_samples(self):
        result = self.assess()

        self.assertTrue(all(
            s["tick"] < 150
            and s["teammate_sample_tick"] <= s["tick"]
            for s in result["position_samples"]
        ))

    def test_combat_evidence(self):
        combat = self.assess()["combat"]

        self.assertTrue(combat["player_damaged_killer"])
        self.assertTrue(combat["killer_damaged_teammate"])
        self.assertEqual(
            combat["player_hurt_killer_ticks"], [130]
        )

    def test_after_death_excluded(self):
        combat = self.assess()["combat"]

        self.assertNotIn(
            151, combat["killer_hurt_teammate_ticks"]
        )

    def test_stale_teammate_sample_rejected(self):
        self.library.player_streams["456"] = (
            self.library.player_streams["456"].iloc[:1]
        )

        samples = self.assess()["position_samples"]

        self.assertEqual(
            [s["tick"] for s in samples], [110, 120]
        )

    def test_missing_combat_is_unknown(self):
        self.library.get_combat_window = None

        combat = self.assess()["combat"]

        self.assertIsNone(combat["player_damaged_killer"])
        self.assertIsNone(
            combat["player_weapon_event_observed"]
        )

    def test_no_error_verdict(self):
        result = self.assess()

        self.assertEqual(
            result["evaluation_status"], "not_evaluated"
        )
        self.assertEqual(result["status"], "sampled_evidence")

    def test_match_library_api(self):
        class IntegratedLibrary(FakeLibrary):
            get_predeath_support_context = (
                MatchLibrary.get_predeath_support_context
            )

        result = IntegratedLibrary().get_predeath_support_context(
            150, "123", "456", "900", lookback_ticks=50
        )

        self.assertEqual(result["player_steamid"], "123")
        self.assertEqual(result["death_tick"], 150)


if __name__ == "__main__":
    unittest.main()
