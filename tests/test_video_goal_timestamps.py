import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from video_goal_evidence import validate, report


class VerifiedVideoCueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )

    def example(self):
        fixture = next(
            match for match in self.db["matches"]
            if match.get("videos")
            and (match.get("goal_protocol") or {}).get("scorers")
            and any(item.get("minutes") for item in match["goal_protocol"]["scorers"])
        )
        goal = next(
            item for item in fixture["goal_protocol"]["scorers"]
            if item.get("minutes")
        )
        video = fixture["videos"][0]
        return {
            "match_id": str(fixture["id"]),
            "player_id": str(goal["player_id"]),
            "minute": str(goal["minutes"][0]),
            "video_id": video["video_id"],
            "timestamp_seconds": 1,
            "verification_source": "observed_video_frame",
            "verified_by": "PLP source reviewer",
            "verified_at": "2026-10-19",
        }

    def test_official_game_match_and_verified_seconds_are_required(self):
        cue = self.example()
        matches = validate(self.db, {"entries": [cue]})
        self.assertEqual(len(matches), 1)
        self.assertIn("&t=1s", matches[0]["url"])
        self.assertTrue(matches[0]["source_url"].startswith("https://podlaskaliga.pl/wydarzenie/"))

    def test_refuse_to_infer_minute_as_video_second(self):
        cue = self.example()
        cue["verification_source"] = ""
        with self.assertRaisesRegex(ValueError, "review method"):
            validate(self.db, {"entries": [cue]})
        self.assertEqual(validate(self.db, {"entries": []}), [])

    def test_refuse_video_from_other_match_and_duplicate(self):
        cue = self.example()
        altered = dict(cue, match_id="not-a-real-game")
        with self.assertRaises(ValueError):
            validate(self.db, {"entries": [altered]})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate(self.db, {"entries": [cue, cue]})

    def test_pending_queue_has_real_proven_source_urls(self):
        content = report(self.db, [])
        self.assertIn("nie są równoważne", content)
        self.assertIn("https://podlaskaliga.pl/wydarzenie/", content)
        self.assertIn("https://www.youtube.com/watch?v=", content)
        self.assertIn("QXRjrPldpi0", content)

    def test_saved_reviews_match_real_protocols_and_do_not_use_match_minutes(self):
        source = json.loads((ROOT / "data/video_goal_evidence.json").read_text(encoding="utf-8"))
        cues = validate(self.db, source)
        self.assertGreaterEqual(len(cues), 2)
        for cue in cues:
            self.assertIn(cue["verification_source"], {"observed_video_frame", "broadcast_commentary_captions"})
            self.assertNotEqual(cue["timestamp_seconds"], int(cue["minute"]) * 60)
        self.assertTrue(all(row.get("review_notes") for row in source["entries"]))

    def test_commentary_cannot_be_used_for_unofficial_video_or_without_caption(self):
        cue = self.example()
        cue["verification_source"] = "broadcast_commentary_captions"
        with self.assertRaisesRegex(ValueError, "caption evidence"):
            validate(self.db, {"entries": [cue]})
        saved = json.loads((ROOT / "data/video_goal_evidence.json").read_text(encoding="utf-8"))
        caption = copy.deepcopy(next(r for r in saved["entries"] if r["verification_source"] == "broadcast_commentary_captions"))
        caption["subtitle_evidence"]["at_seconds"] += 1
        with self.assertRaisesRegex(ValueError, "caption evidence"):
            validate(self.db, {"entries": [caption]})


if __name__ == "__main__":
    unittest.main()
