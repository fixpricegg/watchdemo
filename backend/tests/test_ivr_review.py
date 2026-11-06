import unittest
from copy import deepcopy

import pandas as pd

from detectors.entry_death import detect_entry_deaths
from detectors.buy_mismatch import detect_buy_mismatch
from detectors.missed_trade import get_possible_missed_trades
from review_findings import build_review_findings, prioritize_reviews
from tests.test_buy_mismatch import FakeLibrary as BuyLibrary
from tests.test_missed_trade_candidates import FakeLibrary as TradeLibrary


def death(tick=150, victim="123", killer="900", round_number=1, victim_side=2, killer_side=3):
    return {"tick": tick, "round": round_number, "user_steamid": victim,
            "attacker_steamid": killer, "user_team_num": victim_side,
            "attacker_team_num": killer_side, "attacker_name": "Enemy"}


class OpeningLibrary:
    round_intervals = [(1, 1, 100, 1000), (2, 2, 1000, 2000)]
    round_results = []
    death_data_complete = True

    def get_game_state(self, tick, player):
        return {"perspective": {"steamid": "123"}, "ground_truth": {"players": []}}


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.library = OpeningLibrary()

    def detect(self, rows):
        return detect_entry_deaths(self.library, "123", pd.DataFrame(rows))

    def test_first_enemy_death_is_review_never_error(self):
        finding = self.detect([death()])[0]
        self.assertEqual(finding["status"], "review_required")
        self.assertEqual(finding["verdict"], "not_evaluated")
        self.assertIs(finding["traded_within_window"], False)

    def test_previous_enemy_death_prevents_opening_candidate(self):
        self.assertEqual(self.detect([death(140, "456"), death()]), [])

    def test_world_and_teamkill_are_not_enemy_openings(self):
        result = self.detect([death(130, "456", "0"),
                              death(140, "456", "123", victim_side=2, killer_side=2), death()])
        self.assertEqual(len(result), 1)

    def test_suicide_not_opening(self):
        self.assertEqual(self.detect([death(killer="123")]), [])

    def test_round_and_warmup_isolation(self):
        result = self.detect([death(50), death(1050, round_number=2, victim_side=3, killer_side=2)])
        self.assertEqual([f["round"] for f in result], [2])

    def test_simultaneous_opening_not_arbitrarily_ordered(self):
        result = self.detect([death(victim="456"), death()])[0]
        self.assertEqual(result["simultaneous_opening_deaths"], 2)

    def test_positive_trade_fact_does_not_establish_bad_entry(self):
        result = self.detect([death(), death(160, "900", "456", victim_side=3, killer_side=2)])[0]
        self.assertIs(result["traded_within_window"], True)
        self.assertEqual(result["verdict"], "not_evaluated")

    def test_round_end_makes_short_observation_unknown(self):
        self.library.round_results = [{"round": 1, "result_tick": 200}]
        result = self.detect([death()])[0]
        self.assertIsNone(result["traded_within_window"])

    def test_postround_death_not_opening(self):
        self.library.round_results = [{"round": 1, "result_tick": 140}]
        self.assertEqual(self.detect([death()]), [])

    def test_missing_sources_and_sides_fail_closed(self):
        self.assertEqual(self.detect([death(victim_side=None)]), [])
        self.library.death_data_complete = False
        self.assertEqual(self.detect([death()]), [])


class BuyEvidenceTests(unittest.TestCase):
    def library_with(self, change):
        library = BuyLibrary()
        original = library.get_game_state
        def state(tick, player):
            result = original(tick, player)
            change(result)
            return result
        library.get_game_state = state
        return library

    def test_exact_thresholds_and_evidence(self):
        result = detect_buy_mismatch(BuyLibrary(balance=3000, equipment=1200), "123")[0]
        self.assertEqual(result["sample_tick"], 100)
        self.assertTrue(result["limitations"])

    def test_invalid_numbers_never_become_zero(self):
        for value in [True, float("nan"), float("inf"), -1, "unknown"]:
            with self.subTest(value=value):
                self.assertEqual(detect_buy_mismatch(BuyLibrary(equipment=value), "123"), [])

    def test_future_stale_dead_or_missing_actor_rejected(self):
        for tick, alive in [(99, True), (101, True), (None, True), (100, False), (100, None)]:
            def change(state):
                actor = state["ground_truth"]["players"][0]
                actor["sample_tick"] = tick
                actor["status"]["is_alive"] = alive
            with self.subTest(tick=tick, alive=alive):
                self.assertEqual(detect_buy_mismatch(self.library_with(change), "123"), [])

    def test_missing_or_duplicate_teammate_cannot_prove_majority(self):
        def missing(state):
            state["ground_truth"]["players"][1]["economy"]["current_equip_value"] = None
        self.assertEqual(detect_buy_mismatch(self.library_with(missing), "123"), [])
        def duplicate(state):
            state["ground_truth"]["players"][2] = deepcopy(state["ground_truth"]["players"][1])
        self.assertEqual(detect_buy_mismatch(self.library_with(duplicate), "123"), [])


class TradeAndReportTests(unittest.TestCase):
    def setUp(self):
        self.library = TradeLibrary()
        self.deaths = pd.DataFrame([death(victim="456")])

    def detect(self):
        return get_possible_missed_trades("123", self.deaths, self.library)

    def test_round_end_tail_is_not_a_complete_trade_window(self):
        self.library.round_results = [{"round": 1, "result_tick": 200}]
        self.assertEqual(self.detect(), [])

    def test_simultaneous_trade_excludes_missed_trade(self):
        self.deaths = pd.DataFrame([death(victim="456"), death(victim="900", killer="789")])
        self.assertEqual(self.detect(), [])

    def test_unknown_flash_and_damage_reduce_review_priority(self):
        candidate = self.detect()[0]
        for status in ["insufficient_evidence", "player_limitations_observed", "target_damage_observed", "visibility_unverified_smoke"]:
            with self.subTest(status=status):
                candidate["decision_evidence"]["status"] = status
                finding = build_review_findings([], [candidate], [])[0]
                self.assertEqual(finding["review_priority"], 1)
                self.assertEqual(finding["verdict"], "not_evaluated")

    def test_dedup_priority_and_no_mutation(self):
        candidate = self.detect()[0]
        before = deepcopy(candidate)
        buys = detect_buy_mismatch(BuyLibrary(), "123")
        entries = detect_entry_deaths(OpeningLibrary(), "123", pd.DataFrame([death()]))
        findings = build_review_findings(entries, [candidate, candidate], buys)
        self.assertEqual(len(findings), 3)
        self.assertEqual(candidate, before)
        self.assertEqual(findings[0]["detector"], "Entry Death")
        self.assertEqual(sum(group["count"] for group in prioritize_reviews(findings)), 3)
        self.assertEqual(prioritize_reviews([]), [])

    def test_simultaneous_victims_have_unique_finding_ids(self):
        first = self.detect()[0]
        second = deepcopy(first)
        second["victim_steamid"] = "789"
        findings = build_review_findings([], [first, second], [])
        self.assertEqual(len(findings), 2)
        self.assertEqual(len({f["id"] for f in findings}), 2)

    def test_dead_at_decision_reference_is_not_presented_as_a_problem(self):
        candidate = self.detect()[0]
        candidate["decision_evidence"]["status"] = "not_applicable_actor_dead"
        self.assertEqual(build_review_findings([], [candidate], []), [])


if __name__ == "__main__":
    unittest.main()
