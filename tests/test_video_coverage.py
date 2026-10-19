import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_video_coverage import build_report
from sync_videos import match_video


class VideoCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )

    def test_historic_opponent_names_are_used_only_for_same_plp_team_id(self):
        matches = [
            {"id": "1", "date": "2024-03-10", "gf": 2, "ga": 1, "opponent": "Paka", "opponent_id": 1566},
            {"id": "2", "date": "2024-04-20", "gf": 3, "ga": 0, "opponent": "IST Trade", "opponent_id": 1566},
        ]
        clip = {"title": "BOSCH SERVICE TECH CAR 3:0 Paka", "date": "2024-04-20"}
        self.assertEqual(match_video(clip, matches), "2")

    def test_same_name_distinct_teams_are_not_automatically_conflated(self):
        matches = [
            {"id": "1", "date": "2024-03-10", "gf": 1, "ga": 0, "opponent": "ZPS Biaform SA", "opponent_id": 4643},
            {"id": "2", "date": "2025-03-10", "gf": 1, "ga": 0, "opponent": "ZPS Biaform SA", "opponent_id": 11756},
        ]
        self.assertIsNone(match_video(
            {"title": "BOSCH 1:0 ZPS Biaform SA", "date": ""}, matches
        ))

    def test_precise_upload_date_disambiguates_only_existing_club_and_score_candidates(self):
        matches = [
            {"id": "1", "date": "2024-03-10", "gf": 1, "ga": 0, "opponent": "Paka", "opponent_id": 1566},
            {"id": "2", "date": "2025-06-11", "gf": 1, "ga": 0, "opponent": "Paka", "opponent_id": 1566},
        ]
        self.assertEqual(match_video(
            {"title": "Bosch 1:0 Paka", "date": "20250612"}, matches
        ), "2")
        self.assertIsNone(match_video(
            {"title": "Bosch 1:0 Paka", "date": ""}, matches
        ))

    def test_missing_footage_report_has_source_links_for_every_gap(self):
        db = self.database
        rendered = build_report(db)
        linked = sum(bool(match.get("videos")) for match in db["matches"])
        unlinked = [match for match in db["matches"] if not match.get("videos")]
        self.assertIn(f"{linked} / {len(db['matches'])}", rendered)
        self.assertIn(f"**{len(unlinked)}**", rendered)
        for fixture in unlinked:
            self.assertIn(str(fixture["event_link"]), rendered)
        self.assertIn("bez potwierdzonego przesunięcia", rendered)


if __name__ == "__main__":
    unittest.main()
