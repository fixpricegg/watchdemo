
import unittest

from library.active_utility import build_active_utility


def event(tick, event_type, entity_id):
    return {
        "tick": tick,
        "kind": "utility",
        "type": event_type,
        "data": {
            "entity_id": entity_id,
            "x": 100,
            "y": 200,
            "z": 0,
        },
    }


class TestActiveUtility(unittest.TestCase):

    def setUp(self):
        self.events = [
            event(100, "smokegrenade_detonate", 10),
            event(200, "inferno_startburn", 20),
            event(300, "smokegrenade_expired", 10),
            event(350, "inferno_expire", 20),
        ]

    def test_before_start(self):
        result = build_active_utility(self.events, 90)
        self.assertEqual(result["ongoing_candidates"], [])

    def test_smoke_started(self):
        result = build_active_utility(self.events, 150)
        self.assertEqual(
            result["ongoing_candidates"][0]["type"],
            "smoke",
        )

    def test_two_effects(self):
        result = build_active_utility(self.events, 250)
        self.assertEqual(len(result["ongoing_candidates"]), 2)

    def test_smoke_ended(self):
        result = build_active_utility(self.events, 320)
        self.assertEqual(len(result["ongoing_candidates"]), 1)
        self.assertEqual(result["ended"][0]["end_tick"], 300)

    def test_no_future_leakage(self):
        result = build_active_utility(self.events, 150)
        self.assertIsNone(
            result["ongoing_candidates"][0]["end_tick"]
        )

    def test_missing_entity_id(self):
        result = build_active_utility(
            [event(100, "smokegrenade_detonate", None)],
            150,
        )
        self.assertEqual(result["ongoing_candidates"], [])

    def test_unknown_end(self):
        result = build_active_utility(
            [event(100, "smokegrenade_detonate", 10)],
            1000,
        )
        self.assertEqual(
            result["ongoing_candidates"][0]["status"],
            "end_unconfirmed",
        )


if __name__ == "__main__":
    unittest.main()
