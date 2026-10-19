import json
import sys
import unittest
from pathlib import Path
from sync_public_player_careers import canonicalize_cached_careers

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal

class PublicCareerCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        cls.database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads((ROOT / "data/player_html_career_snapshot.json").read_text(encoding="utf-8"))

    def test_moskal_html_profile_matches_139_not_old_132(self):
        player = next(p for p in self.database["players"] if str(p["id"]) == "1960")
        career = player["career_totals"]
        self.assertEqual(career["apps"], 139)
        self.assertEqual(career["goals"], 31)
        self.assertEqual(career["assists"], 41)
        self.assertEqual(career["source_url"], "https://podlaskaliga.pl/zawodnik/moskal-pawel/")
        self.assertTrue(any(r["name"] == "2021 - Superpuchar" and r["apps"] == 3 for r in career["public_season_rows"]))
        self.assertTrue(any(r["name"] == "Superpuchar 2023" and r["apps"] == 2 for r in career["public_season_rows"]))

    def test_all_public_profile_sums_reconcile_to_season_rows(self):
        current = {str(p["id"]): p for p in self.database["players"]}
        canonical_snapshot = canonicalize_cached_careers(self.snapshot["players"], self.database["players"])
        self.assertNotIn("new-kakareko-kamil", canonical_snapshot)
        for player_id, source in canonical_snapshot.items():
            with self.subTest(player_id=player_id):
                career = current[player_id]["career_totals"]
                self.assertEqual(career["source_url"], source["source_url"])
                for stat in ("apps", "goals", "assists", "motm", "yellow", "red"):
                    if player_id == "7284":
                        self.assertGreaterEqual(career[stat], source["totals"][stat])
                    else:
                        self.assertEqual(career[stat], source["totals"][stat])
                    self.assertEqual(sum(r[stat] for r in career["public_season_rows"]), source["totals"][stat])

    def test_bosch_specific_stats_are_never_overwritten_by_whole_career(self):
        player = next(p for p in self.database["players"] if str(p["id"]) == "1960")
        self.assertEqual(player["apps"], 105)
        self.assertEqual(player["bosch_totals"]["apps"], 105)
        self.assertGreater(player["career_totals"]["apps"], player["apps"])

if __name__ == "__main__":
    unittest.main()
