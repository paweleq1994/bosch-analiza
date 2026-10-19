import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_stat_sources import audit, render


class PlayerProvenanceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )

    def test_report_identifies_all_players_and_preserves_uncertainty(self):
        report = audit(self.database)
        self.assertEqual(report["total_players"], 45)
        self.assertGreaterEqual(report["total_matches"], 113)
        markup = render(report)
        self.assertIn("Nieznana liczba i potwierdzone zero", markup)
        self.assertIn("Niespójności wymagające wyjaśnienia", markup)
        self.assertIn("Nieprzypisane do sezonu", markup)

    def test_source_match_rejects_impossible_season_total(self):
        row = next(
            player for player in self.database["players"] if str(player["id"]) == "1960"
        )
        sample = {
            **row,
            "season_stats": {"139": {"apps": 0, "goals": 0}},
        }
        fixture = next(
            match for match in self.database["matches"]
            if match["sid"] == "139"
            and any(str(entry["player_id"]) == "1960"
                    for entry in match["player_performance"])
        )
        result = audit({"players": [sample], "matches": [fixture]})
        findings = [
            item for item in result["contradictions"]
            if item["id"] == "1960" and item["stat"] == "apps"
        ]
        self.assertTrue(findings)
        self.assertGreater(findings[0]["minimum"], findings[0]["recorded"])
        self.assertIn("https://podlaskaliga.pl/", findings[0]["urls"][0])

    def test_no_missing_career_is_falsely_reported_as_exact_zero(self):
        record = {
            "id": "none", "name": "Player Without Published Profile",
            "season_stats": {}, "career_totals": None, "stats_minimum": True,
        }
        result = audit({"players": [record], "matches": []})
        self.assertFalse(result["coverage"][0]["has_career"])
        self.assertEqual(result["contradictions"], [])


if __name__ == "__main__":
    unittest.main()
