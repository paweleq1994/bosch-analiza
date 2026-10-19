import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_source_reconciliation import audit, markdown


class CareerSourceReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        cls.rest = json.loads((ROOT / "data/player_career_updates.json").read_text(encoding="utf-8"))
        cls.html = json.loads((ROOT / "data/player_html_career_snapshot.json").read_text(encoding="utf-8"))
        cls.evidence = json.loads((ROOT / "data/match_player_evidence.json").read_text(encoding="utf-8"))
        cls.report = audit(cls.db, cls.rest, cls.html, cls.evidence)

    def test_all_45_players_and_verified_goals_are_audited(self):
        self.assertEqual(self.report["all_players"], len(self.db["players"]))
        self.assertEqual(self.report["verified_goal_matches"], 113)
        self.assertEqual(self.report["unattributed_team_goals"], 0)
        self.assertEqual(
            len(self.report["missing_full_careers"]),
            len([p for p in self.db["players"] if not p.get("career_totals")]),
        )

    def test_moskal_official_html_api_difference_is_visible_not_silently_added_to_bosch(self):
        records = {
            record["field"]: record
            for record in self.report["career_source_differences"]
            if record["id"] == "1960" and record["type"] == "official_html_versus_sportspress_api"
        }
        self.assertIn("apps", records)
        self.assertEqual(records["apps"]["html"], 139)
        self.assertEqual(records["apps"]["rest"], 132)
        self.assertEqual(records["apps"]["difference"], 7)
        self.assertIn("moskal-pawel", records["apps"]["url"])

    def test_report_cites_public_urls_and_separates_uncertain_values(self):
        content = markdown(self.report)
        self.assertIn("Moskal Paweł", content)
        self.assertIn("139", content)
        self.assertIn("132", content)
        self.assertIn("Kariera", content.replace("kariera", "Kariera"))
        self.assertIn("https://podlaskaliga.pl/", content)
        self.assertIn("cała kariera PLP", content.lower())


if __name__ == "__main__":
    unittest.main()
