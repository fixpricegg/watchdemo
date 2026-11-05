
import unittest

import pandas as pd

from detectors.missed_trade import get_possible_missed_trades


class FakeGeometry:
    def __init__(self, connected=True):
        self.connected = connected
        self.areas = {
            1: {
                "id": 1,
                "center": {"x": 0, "y": 0, "z": 0},
            },
            2: {
                "id": 2,
                "center": {"x": 100, "y": 0, "z": 0},
            },
            3: {
                "id": 3,
                "center": {"x": 0, "y": 0, "z": 300},
            },
        }

    def find_area(self, x, y, z):
        if z >= 200:
            return self.areas[3]
        if x >= 50:
            return self.areas[2]
        return self.areas[1]

    def shortest_path(self, start, end):
        if start == end:
            return [start]
        if not self.connected:
            return None
        return [start, end]

    def area_distance(self, a, b):
        first = a["center"]
        second = b["center"]
        return sum(
            (first[axis] - second[axis]) ** 2
            for axis in ("x", "y", "z")
        ) ** 0.5


class FakeLibrary:
    def __init__(self):
        self.geometry = FakeGeometry()
        self.max_state_age_ticks = 16
        self.death_data_complete = True

        self.players = [
            {
                "steamid": "123",
                "team": 2,
                "sample_tick": 150,
                "position": {"x": 0, "y": 0, "z": 0},
                "status": {"is_alive": True},
            },
            {
                "steamid": "456",
                "team": 2,
                "sample_tick": 149,
                "position": {"x": 10, "y": 0, "z": 0},
                "status": {"is_alive": False},
            },
            {
                "steamid": "900",
                "team": 3,
                "sample_tick": 150,
                "position": {"x": 100, "y": 0, "z": 0},
                "status": {"is_alive": True},
            },
        ]
        self.team_observations = []
        self.round_end = 1000

    def get_game_state(self, tick, player):
        return {
            "tick": tick,
            "round": {
                "number": 1,
                "live_start_tick": 100,
                "end_tick": self.round_end,
            },
            "perspective": {
                "steamid": "123",
                "team": 2,
            },
            "ground_truth": {
                "players": self.players,
            },
        }


class TestMissedTradeCandidates(unittest.TestCase):
    def setUp(self):
        self.library = FakeLibrary()

        self.deaths = pd.DataFrame([
            {
                "round": 1,
                "tick": 150,
                "user_steamid": 456,
                "attacker_steamid": 900,
                "user_name": "Teammate",
                "attacker_name": "Enemy",
            }
        ])

    def detect(self):
        return get_possible_missed_trades(
            "Player",
            self.deaths,
            self.library,
        )

    def test_valid_review_candidate(self):
        result = self.detect()

        self.assertEqual(len(result), 1)

        candidate = result[0]

        self.assertEqual(
            candidate["type"],
            "trade_review_candidate",
        )
        self.assertEqual(
            candidate["status"],
            "review_required",
        )
        self.assertEqual(
            candidate["evaluation_status"],
            "not_evaluated",
        )
        self.assertEqual(
            candidate["geometry"]["status"],
            "nav_connected",
        )
        self.assertEqual(
            candidate["geometry"]["trade_feasibility"],
            "not_established",
        )
        self.assertEqual(
            candidate["display_eligibility"],
            "review_only",
        )
        self.assertEqual(
            candidate["contact"]["line_of_fire"],
            "not_verified",
        )
        self.assertFalse(
            candidate["contact"]["personal_contact_observed"]
        )


    def test_wrong_team_is_rejected(self):
        self.library.players[1]["team"] = 3
        self.assertEqual(self.detect(), [])

    def test_stale_position_is_rejected(self):
        self.library.players[0]["sample_tick"] = 100
        self.assertEqual(self.detect(), [])

    def test_dead_player_is_rejected(self):
        self.library.players[0]["status"]["is_alive"] = False
        self.assertEqual(self.detect(), [])

    def test_killer_traded_within_window(self):
        self.deaths.loc[len(self.deaths)] = {
            "round": 1,
            "tick": 250,
            "user_steamid": 900,
            "attacker_steamid": 777,
            "user_name": "Enemy",
            "attacker_name": "Other Teammate",
        }

        self.assertEqual(self.detect(), [])

    def test_disconnected_navigation(self):
        self.library.geometry = FakeGeometry(False)
        self.assertEqual(self.detect(), [])

    def test_no_geometry(self):
        self.library.geometry = None
        self.assertEqual(self.detect(), [])

    def test_incomplete_observation_window(self):
        self.library.round_end = 350
        self.assertEqual(self.detect(), [])

    def test_incomplete_death_data(self):
        self.library.death_data_complete = False
        self.assertEqual(self.detect(), [])

    def test_different_floors_not_confirmed(self):
        self.library.players[2]["position"] = {
            "x": 0, "y": 0, "z": 300,
        }

        result = self.detect()

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["geometry"]["vertical_separation"],
            300,
        )
        self.assertEqual(
            result[0]["geometry"]["line_of_sight"],
            "not_checked",
        )
        self.assertEqual(
            result[0]["geometry"]["trade_feasibility"],
            "not_established",
        )

    def test_integrated_predeath_evidence(self):
        self.library.get_predeath_support_context = (
            lambda *args: {
                "status": "sampled_evidence",
                "support_timing": {
                    "reference_tick": 140,
                    "reference_source": "observed_damage_contact",
                    "actor_life_at_reference": "alive",
                    "activity": {"status": "no_weapon_event_observed"},
                    "movement": {"status": "paired_samples"},
                },
                "support_geometry": {
                    "status": "positions_observed",
                    "tick": 140,
                },
            }
        )

        result = self.detect()[0]["decision_evidence"]

        self.assertEqual(result["predeath"]["reference_tick"], 140)
        self.assertEqual(
            result["predeath"]["geometry_status"],
            "positions_observed",
        )

    def test_postdeath_target_damage(self):
        self.library.get_combat_window = lambda start, end: {
            "status": "sources_parsed",
            "parse_status": {
                "weapon_fire": "parsed",
                "player_hurt": "parsed",
            },
            "events": [{
                "tick": 160,
                "type": "player_hurt",
                "data": {
                    "actor_steamid": "123",
                    "victim_steamid": "900",
                },
            }],
        }

        evidence = self.detect()[0]["decision_evidence"]

        self.assertEqual(
            evidence["status"], "target_damage_observed"
        )
        self.assertEqual(
            evidence["postdeath"]["damage_killer_ticks"],
            [160],
        )

    def test_no_shots_not_confirmed_mistake(self):
        self.library.get_combat_window = lambda start, end: {
            "status": "sources_parsed",
            "parse_status": {
                "weapon_fire": "parsed",
                "player_hurt": "parsed",
            },
            "events": [],
        }

        evidence = self.detect()[0]["decision_evidence"]

        self.assertFalse(
            evidence["postdeath"]["weapon_event_observed"]
        )
        self.assertEqual(
            evidence["verdict"], "not_evaluated"
        )
        self.assertEqual(
            evidence["support_opportunity"], "not_established"
        )

    def test_flash_is_not_confirmed_mistake(self):
        self.library.get_player_constraints = (
            lambda tick, player: {
                "status": "limitations_observed",
                "limitations": ["flash_effect_observed"],
                "unknown_fields": [],
                "evidence": {"flash_duration": 2.0},
            }
        )

        evidence = self.detect()[0]["decision_evidence"]

        self.assertEqual(
            evidence["status"], "player_limitations_observed"
        )
        self.assertEqual(
            evidence["verdict"], "not_evaluated"
        )

    def test_missing_sources_remain_unknown(self):
        evidence = self.detect()[0]["decision_evidence"]

        self.assertIsNone(
            evidence["postdeath"]["damaged_killer"]
        )
        self.assertEqual(
            evidence["status"], "insufficient_evidence"
        )

    def test_smoke_prevents_confirmed_verdict(self):
        self.library.get_active_utility_effects = (
            lambda tick, player: {
                "status": "observed",
                "ongoing_candidates": [{
                    "type": "smoke",
                    "entity_id": 10,
                    "start_tick": 120,
                    "x": 50,
                    "y": 0,
                    "z": 0,
                }],
            }
        )

        result = self.detect()[0]["decision_evidence"]

        self.assertEqual(
            result["status"],
            "visibility_unverified_smoke",
        )
        self.assertEqual(result["verdict"], "not_evaluated")
        self.assertEqual(
            result["smoke_visibility"]["status"],
            "possible_smoke_occlusion",
        )


if __name__ == "__main__":
    unittest.main()
