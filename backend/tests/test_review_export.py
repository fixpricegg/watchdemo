from datetime import datetime, timezone
import unittest

from report_export import export_report


class ReviewExportTests(unittest.TestCase):
    def row(self, findings):
        return {"id": "report", "match_id": "match", "created_at": datetime.now(timezone.utc),
                "result": {"report": {"summary": {}, "review_findings": findings}}}

    def test_public_tick_and_facts_survive_without_internal_context(self):
        response = export_report(self.row([{
            "id": "entry:1:150", "type": "entry_death_candidate", "round": 1,
            "tick": 150, "status": "review_required", "review_priority": 3,
            "facts": ["Observed fact", {"token": "SECRET"}], "limitations": ["Not a verdict"],
            "evidence": {"password": "SECRET"}, "token": "SECRET",
        }]))
        finding = response["report"]["review_findings"][0]
        self.assertEqual(finding["tick"], 150)
        self.assertEqual(finding["facts"], ["Observed fact"])
        self.assertNotIn("SECRET", str(response))

    def test_nested_objects_are_not_accepted_as_scalar_public_fields(self):
        response = export_report(self.row([None, {"tick": {"token": "SECRET"},
            "round": True, "description": {"token": "SECRET"}, "limitations": {"token": "SECRET"}}]))
        self.assertEqual(response["report"]["review_findings"], [{"facts": [], "limitations": []}])
        self.assertEqual(export_report(self.row(None))["report"]["review_findings"], [])
