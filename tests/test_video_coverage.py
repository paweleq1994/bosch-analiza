import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_video_coverage import build_report
from sync_videos import match_video, validate_fixture_dates


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

    def test_manual_rejection_removes_an_original_archive_link(self):
        import build_portal
        original_load = build_portal.load
        settings = original_load("video_updates.json")
        settings["manual_bindings"]["hcfb9Ttmswo"] = {
            "match_id": None, "review_reason": "Reviewed venue contradicts the indoor fixture",
            "reviewed_at": "2026-10-19",
        }
        def load(name, default=None):
            return deepcopy(settings) if name == "video_updates.json" else original_load(name, default)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "data.json"
            with patch.object(build_portal, "load", side_effect=load), patch.object(build_portal, "OUTPUT", output):
                build_portal.main()
            db = json.loads(output.read_text(encoding="utf-8"))
        video = next(v for v in db["videos"] if v["id"] == "hcfb9Ttmswo")
        self.assertIsNone(video["match_id"])
        self.assertEqual(video["status"], "rejected")
        self.assertTrue(video["review_reason"])
        self.assertFalse(any(v["video_id"] == video["id"] for m in db["matches"] for v in m["videos"]))

    def test_upload_date_rejects_even_a_unique_wrong_season_score_match(self):
        matches = [{"id": "1", "date": "2023-02-26", "gf": 2, "ga": 1, "opponent": "VESTA"}]
        self.assertIsNone(match_video({"title": "Bosch - VESTA 2:1", "date": "2023-08-26"}, matches))
        self.assertIsNone(match_video({"title": "Bosch - VESTA 2:1", "date": "2023-02-01"}, matches))

    def test_official_broadcasts_have_exact_dated_source_bindings_and_keep_format(self):
        expected={"PWnZ2yifLNI":"8255", "YTZTrjLc5Nw":"9486", "3A0-Z_98lKQ":"9805",
                  "jbsK8wBM8UM":"10145", "s3iMR88rCKE":"10990", "RVOIr5BF1pw":"11397",
                  "8mVCFD11ZGo":"11798"}
        for video_id, match_id in expected.items():
            video=next(v for v in self.database["videos"] if v["id"]==video_id)
            match=next(m for m in self.database["matches"] if m["id"]==match_id)
            self.assertEqual(video["date"],match["date"])
            self.assertEqual(video["match_id"],match_id)
            self.assertEqual(video["segment"],"Transmisja meczu")
            self.assertIn(match["event_link"],video["verification_source"])
            self.assertTrue(any(v["video_id"]==video_id for v in match["videos"]))
        cup=next(v for v in self.database["videos"] if v["id"]=="Sglay1fT-00")
        self.assertIsNone(cup["match_id"])
        self.assertEqual(cup["review_category"],"outside_league_archive")

    def test_legacy_films_are_reconciled_by_date_venue_and_half_score(self):
        videos = {v["id"]: v for v in self.database["videos"]}
        expected = {"bQ3De8L7mnA": "8373", "RkV8q7Vfy4g": "10990", "uby5J-1mtDs": "10990"}
        for vid, event_id in expected.items():
            self.assertEqual(videos[vid]["match_id"], event_id)
            self.assertTrue(videos[vid]["verification_source"])
        self.assertIsNone(videos["Qc0s7ZjnInM"]["match_id"])
        self.assertEqual(videos["Qc0s7ZjnInM"]["status"], "rejected")
        for match in self.database["matches"]:
            if match["id"] in {"8276", "9721"}:
                self.assertFalse(match["videos"])

    def test_recordings_cannot_predate_their_fixture_even_when_legacy_or_manual(self):
        match = [{"id": "1", "date": "2024-02-10"}]
        validate_fixture_dates([{"id": "ok", "match_id": "1", "date": "2024-02-09"}], match)
        validate_fixture_dates([{"id": "delayed", "match_id": "1", "date": "2025-02-10"}], match)
        for status in ("matched_archive", "matched_manual", "matched_auto"):
            with self.assertRaisesRegex(ValueError, "published before fixture"):
                validate_fixture_dates([{"id": "wrong", "match_id": "1", "date": "2023-08-26", "status": status}], match)
        validate_fixture_dates(self.database["videos"], self.database["matches"])

    def test_user_classified_tournaments_cannot_be_matched_to_league_fixtures(self):
        excluded = {"mRNWenMq9DA", "jYIcEGA7gns", "O3mBzeS-9VY", "PDHzxceI8wU"}
        probable = {"ip4f5qE7-Cs", "2TgTJHeWd4o", "o4tWJ0ngczs"}
        for video in self.database["videos"]:
            if video["id"] not in excluded | probable:
                continue
            self.assertIsNone(video["match_id"])
            self.assertEqual(video["status"], "ignored" if video["id"] in excluded else "needs_review")
            self.assertTrue(video["verification_source"])
            candidate = {"id": "future", "date": video["date"], "gf": 1, "ga": 2, "opponent": "Test"}
            self.assertIsNone(match_video({**video, "title": "Bosch 1:2 Test"}, [candidate]))
        report = build_report(self.database)
        pending = report.split("## Nieprzypisane materiały")[1].split("## Filmy poza PLP")[0]
        self.assertNotIn("Medgal", pending)
        self.assertIn("Rambo", pending)
        self.assertIn("nie jest pewne", pending)


if __name__ == "__main__":
    unittest.main()
