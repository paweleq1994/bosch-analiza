import json
import copy
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
        self.assertIn("cała kariera plp", content.lower())

    def test_moskal_difference_is_fully_located_in_supercups(self):
        row = next(r for r in self.report["career_source_differences"]
                   if r["id"] == "1960" and r["field"] == "apps")
        self.assertEqual(row["status"], "explained_supercup_scope")
        self.assertEqual(sum(r["difference"] for r in row["season_breakdown"]), 7)
        self.assertTrue(all("superpuchar" in r["season"].lower() for r in row["season_breakdown"]))

    def test_verified_goalkeeper_alias_explains_canonical_career_difference(self):
        rows = [r for r in self.report["career_source_differences"]
                if r["id"] == "7284" and r["type"] == "displayed_career_disagrees_with_html"]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["status"], "explained_verified_identity_merge")
            self.assertEqual(row["identity_contributions"][0]["id"], "13060")
            self.assertEqual(row["html"] + row["identity_contributions"][0]["value"], row["rest"])

    def test_non_supercup_source_variance_is_not_claimed_as_resolved(self):
        row = next(r for r in self.report["career_source_differences"]
                   if r["id"] == "1594" and r["field"] == "goals")
        self.assertEqual(row["status"], "source_variance_requires_review")
        self.assertTrue(any(r["reason"] == "same_season_source_variance" for r in row["season_breakdown"]))

    def test_goalkeeper_rest_zero_is_explained_by_independent_appearance(self):
        row = next(r for r in self.report["career_source_differences"]
                   if r["id"] == "7223" and r["field"] == "apps")
        self.assertEqual(row["status"], "explained_source_rows_and_match_evidence")
        match = next(r for r in row["season_breakdown"] if r["season_ids"] == ["126"])
        self.assertEqual((match["html"], match["rest"], match["match_minimum"]), (1, 0, 1))
        self.assertTrue(match["match_source_urls"])

    def test_all_remaining_variances_are_explained_by_complete_protocol_sets(self):
        extra=json.loads((ROOT / "data/career_competition_evidence.json").read_text(encoding="utf-8"))
        before=copy.deepcopy(self.db)
        report=audit(self.db,self.rest,self.html,self.evidence,extra)
        self.assertFalse(any(r["status"].endswith("requires_review") for r in report["career_source_differences"]))
        rows=[r for r in report["career_season_differences"] if r["reason"]=="events_without_league_taxonomy"]
        self.assertEqual(len(rows),5)
        self.assertEqual({r["id"] for r in rows},{"4577","2204","1594"})
        for row in rows:
            self.assertEqual(row["protocol_total"],row["html"])
            self.assertEqual(row["protocol_tagged_total"],row["rest"])
            self.assertTrue(row["match_source_urls"])
        self.assertEqual(self.db,before)  # The other clubs' games never enter Bosch totals.

    def test_missing_or_changed_competition_evidence_cannot_explain_the_delta(self):
        extra=json.loads((ROOT / "data/career_competition_evidence.json").read_text(encoding="utf-8"))
        row=next(r for r in extra["records"] if r["player_id"]=="1594")
        for event in row["events"]:
            if not event["leagues"]:
                event["leagues"]=[101]
        report=audit(self.db,self.rest,self.html,self.evidence,extra)
        goal=next(r for r in report["career_source_differences"] if r["id"]=="1594" and r["field"]=="goals")
        self.assertEqual(goal["status"],"source_variance_requires_review")


if __name__ == "__main__":
    unittest.main()
