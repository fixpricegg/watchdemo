
import unittest
import pandas as pd

from library.predeath_support import (
    build_predeath_support,
    assess_support_timing,
)
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

    def test_v2_damage_contact_reference(self):
        context = self.assess()
        result = assess_support_timing(context)

        self.assertEqual(result["reference_tick"], 125)
        self.assertEqual(
            result["reference_source"],
            "observed_damage_contact",
        )
        self.assertEqual(
            result["activity"]["status"],
            "damage_on_killer_observed",
        )
        self.assertEqual(
            result["activity"]["nearest_damage_delta_ticks"],
            5,
        )

    def test_v2_weapon_activity_timing(self):
        context = self.assess()
        context["combat"]["player_hurt_killer_ticks"] = []

        result = assess_support_timing(context)

        self.assertEqual(
            result["activity"]["status"],
            "weapon_activity_target_unknown",
        )
        self.assertEqual(
            result["activity"]["nearest_weapon_event_delta_ticks"],
            20,
        )

    def test_v2_no_action_is_not_missed_support(self):
        context = self.assess()
        context["combat"]["player_hurt_killer_ticks"] = []
        context["combat"]["player_weapon_fire_ticks"] = []

        result = assess_support_timing(context)

        self.assertEqual(
            result["activity"]["status"],
            "no_weapon_event_observed",
        )
        self.assertEqual(
            result["support_opportunity"],
            "not_established",
        )
        self.assertEqual(
            result["evaluation_status"],
            "not_evaluated",
        )

    def test_v2_instant_death_reference(self):
        context = self.assess()
        context["combat"]["teammate_hurt_killer_ticks"] = []
        context["combat"]["killer_hurt_teammate_ticks"] = []

        result = assess_support_timing(context)

        self.assertEqual(result["reference_tick"], 150)
        self.assertEqual(
            result["reference_source"],
            "death_tick_fallback",
        )

    def test_v2_movement_alignment(self):
        context = self.assess()

        result = assess_support_timing(
            context,
            movement_lookback_ticks=10,
        )

        movement = result["movement"]

        self.assertEqual(
            movement["status"], "paired_samples"
        )
        self.assertEqual(
            movement["before_tick"], 110
        )
        self.assertEqual(
            movement["reference_sample_tick"], 120
        )
        self.assertEqual(
            movement["separation_change_2d"], -5.0
        )

    def test_v2_stale_position_rejected(self):
        context = self.assess()

        result = assess_support_timing(
            context,
            movement_lookback_ticks=10,
            max_sample_age_ticks=3,
        )

        self.assertEqual(
            result["movement"]["status"],
            "insufficient_aligned_samples",
        )

    def test_v2_future_damage_excluded(self):
        context = self.assess()
        context["combat"]["player_hurt_killer_ticks"] = [151]
        context["combat"]["player_weapon_fire_ticks"] = []

        result = assess_support_timing(context)

        self.assertEqual(
            result["activity"]["damage_killer_ticks"], []
        )
        self.assertEqual(
            result["activity"]["status"],
            "no_weapon_event_observed",
        )

    def test_v2_library_integration(self):
        class IntegratedLibrary(FakeLibrary):
            get_predeath_support_context = (
                MatchLibrary.get_predeath_support_context
            )

        result = IntegratedLibrary().get_predeath_support_context(
            150, "123", "456", "900", lookback_ticks=50
        )

        self.assertEqual(
            result["schema_version"],
            "predeath_support_v2",
        )
        self.assertEqual(
            result["support_timing"]["reference_tick"],
            125,
        )

    def test_v2_movement_preroll(self):
        extra = pd.DataFrame([
            self.library.row(140, "456", 65)
        ])

        self.library.player_streams["456"] = pd.concat(
            [self.library.player_streams["456"], extra],
            ignore_index=True,
        )

        context = self.assess(lookback_ticks=20)
        timing = assess_support_timing(context)

        self.assertEqual(context["window_start_tick"], 130)
        self.assertEqual(
            context["position_window_start_tick"], 100
        )
        self.assertIn(
            110,
            [s["tick"] for s in context["position_samples"]],
        )
        self.assertEqual(
            context["combat"]["teammate_hurt_killer_ticks"], []
        )
        self.assertEqual(
            timing["movement"]["status"], "paired_samples"
        )

    def life_library(self, alive):
        class LifeLibrary(FakeLibrary):
            get_predeath_support_context = (
                MatchLibrary.get_predeath_support_context
            )
            get_player_constraints = (
                MatchLibrary.get_player_constraints
            )

            def get_game_state(self, tick, player):
                state = super().get_game_state(tick, player)
                state["tick"] = tick
                state["ground_truth"] = {
                    "players": [{
                        "steamid": "123",
                        "sample_tick": tick,
                        "status": {"is_alive": alive},
                    }]
                }
                return state

        return LifeLibrary()

    def test_v2_dead_actor_not_applicable(self):
        library = self.life_library(False)

        result = library.get_predeath_support_context(
            150, "123", "456", "900", lookback_ticks=50
        )

        timing = result["support_timing"]

        self.assertEqual(result["status"], "not_applicable")
        self.assertEqual(
            timing["actor_life_at_reference"], "dead"
        )
        self.assertEqual(
            timing["support_opportunity"], "not_applicable"
        )

    def test_v2_unknown_actor_not_confirmed(self):
        library = self.life_library(None)

        result = library.get_predeath_support_context(
            150, "123", "456", "900", lookback_ticks=50
        )

        timing = result["support_timing"]

        self.assertEqual(
            timing["status"], "insufficient_evidence"
        )
        self.assertEqual(
            timing["support_opportunity"], "not_established"
        )

    def test_v2_alive_actor_keeps_analysis(self):
        library = self.life_library(True)

        result = library.get_predeath_support_context(
            150, "123", "456", "900", lookback_ticks=50
        )

        timing = result["support_timing"]

        self.assertEqual(
            timing["actor_life_at_reference"], "alive"
        )
        self.assertEqual(
            timing["status"], "observations_available"
        )
        self.assertEqual(
            timing["evaluation_status"], "not_evaluated"
        )




if __name__ == "__main__":
    unittest.main()
