import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import audit_player_coverage
import build_portal


class PlayerCoverageAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        cls.database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))

    def test_all_historical_players_covered_by_audit(self):
        report = audit_player_coverage.build_report(self.database)
        self.assertIn(f"Zawodnicy: **{len(self.database['players'])}**", report)
        self.assertIn("Oficjalne protokoły bramkowe: **113**", report)
        self.assertIn("Bramki drużyny: **293**, nierozliczone: **0**", report)
        self.assertIn("Samobóje Boscha: **6**", report)
        self.assertIn("Występy", report)
        self.assertIn("Asysty", report)
        self.assertIn("Żółte kartki", report)
        self.assertIn("Czerwone kartki", report)

    def test_missing_data_is_explicit_and_no_identity_is_inferred_from_team_photos(self):
        report = audit_player_coverage.build_report(self.database)
        self.assertIn("Dawid Daniluk (PLP ID 2204)", report)
        self.assertIn("Sołowiej Tomasz (PLP ID 7285)", report)
        self.assertIn("Pietruczuk Paweł (PLP ID 12286)", report)
        self.assertIn("zdjęcia drużynowe nie potwierdzają tożsamości osoby".casefold().replace("zdjęcia", "Zdjęcia"), report)

    def test_duplicate_goalkeeper_has_canonical_photo_subject(self):
        subjects = self.database.get("media", {}).get("subjects") or []
        goalkeeper_galleries = [
            item
            for item in subjects
            if item.get("kind") == "players" and str(item.get("id")) in ("7284", "13060")
        ]
        self.assertEqual(len(goalkeeper_galleries), 1)
        self.assertEqual(str(goalkeeper_galleries[0]["id"]), "7284")
        self.assertGreaterEqual(len(goalkeeper_galleries[0]["photos"]), 4)


if __name__ == "__main__":
    unittest.main()
