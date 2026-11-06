import unittest
from copy import deepcopy
import pandas as pd
from library.builder import MatchLibrary
from library.economic_rewards import (
    RewardRules, WEAPON_REWARDS, build_round_kill_rewards, build_kill_reward_events,
)

A, B, C = "76561199636557537", "76561198000000002", "76561198000000003"
ROUNDS = [(1, 1, 100, 200), (2, 2, 300, 400)]


def death(tick=150, weapon="ak47", **extra):
    return dict(tick=tick, weapon=weapon, attacker_steamid=A, user_steamid=B,
                attacker_team_num=2, user_team_num=3, **extra)


def summary(rows, **kwargs):
    return build_round_kill_rewards(pd.DataFrame(rows), ROUNDS,
                                    player_ids=[A], **kwargs)[(A, 1)]


def library(rows=None, **kwargs):
    if rows is not None:
        rows = [dict(row, round=1 if row["tick"] < 200 else 2) for row in rows]
    positions = pd.DataFrame([
        dict(tick=tick, steamid=steamid, name=steamid, team_num=team,
             balance=16000, current_equip_value=2700, is_alive=True)
        for tick in (100, 199, 300, 399)
        for steamid, team in ((A, 2), (B, 3))
    ])
    return MatchLibrary(map_name="de_nuke", position_df=positions,
                        round_intervals=ROUNDS,
                        deaths_df=pd.DataFrame(rows) if rows is not None else None,
                        team_observations=[], team_spot_windows=[], **kwargs)


class TestEventRewards(unittest.TestCase):
    def test_weapon_awards_and_aliases(self):
        for weapon, amount in {
            "weapon_ak47": 300, "AK-47": 300, "M4A1-S": 300, "M4A4": 300,
            "USP-S": 300, "CZ75-Auto": 300, "P90": 300, "AWP": 100,
            "MP9": 600, "MP5-SD": 600, "MAG-7": 900, "XM1014": 600,
            "knife_stiletto": 1500, "weapon_bayonet": 1500, "Zeus x27": 100,
            "inferno": 300, "hegrenade": 300,
        }.items():
            with self.subTest(weapon=weapon):
                self.assertEqual(summary([death(weapon=weapon)])["nominal_kill_reward"], amount)

    def test_three_ak_kills_are_900_and_not_cash_income(self):
        result = summary([death(tick=t) for t in (120, 140, 160)])
        self.assertEqual(result["enemy_kills"], 3)
        self.assertEqual(result["nominal_kill_reward"], 900)
        self.assertIsNone(result["actual_income"])
        self.assertFalse(result["rules_confirmed"])

    def test_unknown_weapon_keeps_known_subtotal(self):
        result = summary([death(120), death(150, "laser")])
        self.assertIsNone(result["nominal_kill_reward"])
        self.assertEqual(result["known_nominal_kill_reward"], 300)
        self.assertEqual(result["unknown_reward_events"], 1)
        self.assertEqual(result["enemy_kills"], 2)

    def test_missing_or_future_knife_token_not_default_300(self):
        for weapon in (None, float("nan"), "knife_future", ""):
            with self.subTest(weapon=weapon):
                self.assertIsNone(summary([death(weapon=weapon)])["nominal_kill_reward"])

    def test_teamkill_penalty_is_separate(self):
        row = death()
        row["user_team_num"] = 2
        result = summary([row])
        self.assertEqual(result["enemy_kills"], 0)
        self.assertEqual(result["teamkills"], 1)
        self.assertEqual(result["nominal_kill_reward"], 0)
        self.assertEqual(result["nominal_teamkill_penalty"], -300)

    def test_suicide_world_bomb_and_assister(self):
        row = death()
        row["user_steamid"] = A
        result = summary([row])
        self.assertEqual(result["suicides"], 1)
        self.assertEqual(result["nominal_kill_reward"], 0)
        for weapon in ("world", "planted_c4"):
            row = death(weapon=weapon)
            row["assister_steamid"] = C
            result = build_round_kill_rewards(pd.DataFrame([row]), ROUNDS, player_ids=[A, C])
            self.assertEqual(result[(A, 1)]["nominal_kill_reward"], 0)
            self.assertEqual(result[(C, 1)]["nominal_kill_reward"], 0)

    def test_zero_steamid_and_unknown_attacker_are_not_positive_kills(self):
        row = death()
        row["attacker_steamid"] = "0"
        result = summary([row])
        self.assertEqual(result["unattributed_events"], 1)
        self.assertIsNone(result["nominal_kill_reward"])

    def test_bomb_deaths_without_player_attacker_do_not_poison_round(self):
        row = death(weapon="planted_c4")
        row["attacker_steamid"] = "0"
        self.assertEqual(summary([row])["nominal_kill_reward"], 0)

    def test_missing_team_does_not_guess_from_player_roster(self):
        row = death()
        row.pop("attacker_team_num")
        self.assertIsNone(summary([row])["nominal_kill_reward"])

    def test_halftime_uses_event_team_and_not_final_team(self):
        row = death(350)
        row.update(attacker_team_num=3, user_team_num=2)
        result = build_round_kill_rewards(pd.DataFrame([row]), ROUNDS, player_ids=[A])
        self.assertEqual(result[(A, 1)]["nominal_kill_reward"], 0)
        self.assertEqual(result[(A, 2)]["nominal_kill_reward"], 300)

    def test_boundaries_warmup_freeze_and_end_exclusive(self):
        result = summary([death(t) for t in (99, 100, 199, 200, 250)])
        self.assertEqual([e["tick"] for e in result["events"]], [100, 199])
        self.assertEqual(result["nominal_kill_reward"], 600)

    def test_duplicates_and_conflicting_events(self):
        row = death()
        self.assertEqual(summary([row, deepcopy(row)])["nominal_kill_reward"], 300)
        conflict = dict(row, weapon="awp")
        self.assertIsNone(summary([row, conflict])["nominal_kill_reward"])

    def test_complete_empty_dataset_is_zero_missing_dataset_is_unknown(self):
        empty = pd.DataFrame(columns=["tick", "attacker_steamid", "user_steamid"])
        self.assertEqual(build_round_kill_rewards(empty, ROUNDS, player_ids=[A])[(A, 1)]["nominal_kill_reward"], 0)
        for df in (None, pd.DataFrame(), pd.DataFrame([{"tick": 150}])):
            self.assertIsNone(build_round_kill_rewards(df, ROUNDS, player_ids=[A])[(A, 1)]["nominal_kill_reward"])

    def test_partial_data_cannot_prove_total(self):
        result = summary([death()], death_data_complete=False)
        self.assertIsNone(result["nominal_kill_reward"])
        self.assertEqual(result["known_nominal_kill_reward"], 300)

    def test_invalid_tick_does_not_crash_or_prove_zero(self):
        for tick in (None, float("inf"), "invalid", 1.5):
            with self.subTest(tick=tick):
                self.assertIsNone(summary([death(tick)])["nominal_kill_reward"])

    def test_unknown_custom_disabled_and_historical_rules(self):
        self.assertIsNone(summary([death()], rules=RewardRules(profile="unknown"))["nominal_kill_reward"])
        self.assertEqual(summary([death()], rules=RewardRules(enemy_factor=0.5))["nominal_kill_reward"], 150)
        self.assertEqual(summary([death()], rules=RewardRules(player_cash_awards=False))["nominal_kill_reward"], 0)
        legacy = dict(WEAPON_REWARDS, cz75a=100, xm1014=900, taser=0)
        self.assertEqual(summary([death(weapon="CZ75-Auto")], rules=RewardRules(
            profile="historical_pre_2024_04_25", weapon_rewards=legacy
        ))["nominal_kill_reward"], 100)
        for factor in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                RewardRules(enemy_factor=factor)

    def test_at_tick_prefix_does_not_include_future_or_next_round(self):
        rows = [death(120), death(150), death(350)]
        result = build_round_kill_rewards(pd.DataFrame(rows), ROUNDS, player_ids=[A], current_tick=120)
        self.assertEqual(list(result), [(A, 1)])
        self.assertEqual(result[(A, 1)]["nominal_kill_reward"], 300)
        self.assertEqual(result[(A, 1)]["through_tick"], 120)
        self.assertFalse(result[(A, 1)]["round_complete"])
        self.assertEqual(build_kill_reward_events(pd.DataFrame(rows), ROUNDS, current_tick=119), [])


class TestLibraryRewards(unittest.TestCase):
    def test_history_and_missing_data(self):
        history = library([death()]).get_player_economy_history(A)
        self.assertEqual(history[0]["kill_rewards"]["nominal_kill_reward"], 300)
        self.assertEqual(history[1]["kill_rewards"]["nominal_kill_reward"], 0)
        self.assertIsNone(library().get_player_economy_history(A)[0]["kill_rewards"]["nominal_kill_reward"])

    def test_engine_counter_is_never_income(self):
        lib = library([death()], kill_reward_history={(A, 1): {"observed_delta": 99999}})
        self.assertEqual(lib.get_player_economy_history(A)[0]["kill_rewards"]["nominal_kill_reward"], 300)

    def test_history_has_completed_rounds_only_and_bounds_at_end(self):
        lib = library([death(), death(350)])
        self.assertEqual(lib.get_player_economy_history(A, current_tick=199), [])
        history = lib.get_player_economy_history(A, current_tick=200)
        self.assertEqual([h["round"] for h in history], [1])
        self.assertEqual(history[0]["kill_rewards"]["nominal_kill_reward"], 300)

    def test_future_prebuy_is_rejected(self):
        lib = library([death()], prebuy_snapshots={(1, A): {"sample_tick": 350, "secret": 99999}})
        self.assertIsNone(lib.get_player_economy_history(A, current_tick=200)[0]["pre_buy"])

    def test_cash_cap_never_changes_nominal_or_claims_credited_amount(self):
        # All position balances are at $16000. No false +300 cash claim.
        result = library([death()]).get_player_economy_history(A)[0]["kill_rewards"]
        self.assertEqual(result["nominal_kill_reward"], 300)
        self.assertIsNone(result["actual_income"])

    def test_returned_history_mutation_does_not_change_next_request(self):
        lib = library([death()])
        result = lib.get_player_economic_rewards(A)
        result[0]["events"][0]["nominal_reward"] = 99999
        self.assertEqual(lib.get_player_economic_rewards(A)[0]["nominal_kill_reward"], 300)

    def test_future_mutation_does_not_change_past_rewards_history_or_decision(self):
        past, future = death(150), death(350)
        lib1 = library([past, future])
        future.update(weapon="knife", attacker_team_num=3, user_team_num=2)
        lib2 = library([past, future])
        for method, args in (("get_player_economic_rewards", (A, 199)),
                             ("get_player_economy_history", (A, 200)),
                             ("get_decision_input", (100, A))):
            self.assertEqual(getattr(lib1, method)(*args), getattr(lib2, method)(*args))

    def test_decision_has_no_hidden_enemy_rewards_or_future_round_end(self):
        lib = library([death()])
        result = lib.get_decision_input(100, A)
        self.assertNotIn("end_tick", result["round"])
        self.assertNotIn("kill_rewards", str(result))
        self.assertNotIn(B, str(result))
        self.assertNotIn("player_economy_history", result)

    def test_future_end_time_does_not_change_decision(self):
        lib = library([death()])
        before = lib.get_decision_input(100, A)
        lib.round_intervals = [(1, 1, 100, 299), ROUNDS[1]]
        self.assertEqual(before, lib.get_decision_input(100, A))

    def test_missing_player_snapshot_still_has_event_rewards(self):
        lib = library([death()])
        lib.player_streams[A] = lib.player_streams[A].query("tick >= 300")
        first = lib.get_player_economy_history(A)[0]
        self.assertEqual(first["status"], "unavailable")
        self.assertEqual(first["kill_rewards"]["nominal_kill_reward"], 300)


if __name__ == "__main__":
    unittest.main()
