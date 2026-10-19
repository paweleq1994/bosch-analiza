"""Archived PLP sources allocate known balances without inventing a career."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_portal
from plp_photo_archive import sync


class ArchivedPlayerProfilesTests(unittest.TestCase):
    def setUp(self):
        self.db = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        self.corrections = build_portal.load("player_stat_corrections.json")
        self.audit = build_portal.load("source_access_audit.json")["internet_archive"]

    def test_cup_fields_come_from_matching_source_id_and_named_css_columns(self):
        fields = {"apps": "appearances", "goals": "goals", "assists": "assists",
                  "motm": "pikarzmeczu", "yellow": "yellowcards", "red": "redcards"}
        for pid in ("7271", "7278", "7285"):
            source = next(p for p in self.audit["profiles"] if p["player_id"] == pid)
            excerpt = (ROOT / source["source_excerpt"]).read_text(encoding="utf-8")
            self.assertIn("postid-" + pid, excerpt)
            row = next(row for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", excerpt, re.S)
                       if "Superpuchar 2022" in row and "data-team" not in row)
            stat = self.corrections[pid]["seasons"]["119"]
            for field, column in fields.items():
                value = re.search(r'<td class="data-' + column + r'">(\d+)</td>', row)
                self.assertEqual(int(value.group(1)), stat[field])
            self.assertEqual(stat["source_url"], source["archive_url"])
            self.assertFalse(source["complete_current_career"])

    def test_archival_allocation_does_not_increase_totals_or_create_full_careers(self):
        original_load = build_portal.load
        def load(name, default=None):
            if name == "player_stat_corrections.json":
                return {k: v for k, v in self.corrections.items() if k not in ("7271", "7278", "7285")}
            return original_load(name, default)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.json"
            with patch.object(build_portal, "load", side_effect=load), patch.object(build_portal, "OUTPUT", target):
                build_portal.main()
            before = json.loads(target.read_text(encoding="utf-8"))
        for pid in ("7271", "7278", "7285"):
            old = next(p for p in before["players"] if p["id"] == pid)
            new = next(p for p in self.db["players"] if p["id"] == pid)
            for field in ("apps", "goals", "assists", "motm", "yellow", "red"):
                self.assertEqual(new[field], old[field])
            self.assertTrue(any(old["season_coverage"]["unassigned"].values()))
            self.assertFalse(any(new["season_coverage"]["unassigned"].values()))
            self.assertIsNone(new["bosch_totals"])
            self.assertIsNone(new["career_totals"])
            self.assertTrue(new["stats_minimum"])

    def test_verified_portraits_retain_original_profile_evidence_during_api_outage(self):
        manifest = build_portal.load("media_manifest.json")
        updated, _ = sync(manifest, ["7270", "7271", "7285"],
                          fetch=lambda *args: (_ for _ in ()).throw(RuntimeError("401")))
        for pid in ("7270", "7271", "7285"):
            source = next(p for p in self.audit["profiles"] if p["player_id"] == pid)
            excerpt = (ROOT / source["source_excerpt"]).read_text(encoding="utf-8")
            photo = next(s for s in updated["subjects"] if s["kind"] == "players" and s["id"] == pid)["photos"][0]
            self.assertIn('src="' + photo["url"] + '"', excerpt)
            self.assertEqual(photo["source_player_id"], pid)
            self.assertEqual(photo["origin"], "archived_official_player_portrait")
            self.assertNotIn("player-single-370x400", photo["url"])
            self.assertTrue((ROOT / "docs" / photo["local"]).is_file())


if __name__ == "__main__":
    unittest.main()
