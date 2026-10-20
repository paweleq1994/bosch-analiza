import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal
from merge_player_identities import merge_player_identities


class DuplicateGoalkeeperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        cls.database = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))

    def test_single_rutkowski_profile_and_both_source_ids(self):
        players = self.database["players"]
        goalkeepers = [player for player in players if "rutkowski mateusz" in player["name"].lower()]

        self.assertEqual(len(goalkeepers), 1)
        self.assertEqual(goalkeepers[0]["id"], "7284")
        self.assertIn("13060", goalkeepers[0]["aliases"])
        self.assertEqual(len(goalkeepers[0]["merged_source_profiles"]), 2)
        self.assertTrue(goalkeepers[0]["name"].endswith("(GK)"))

    def test_career_totals_and_hala_2025_26(self):
        player = next(p for p in self.database["players"] if p["id"] == "7284")
        self.assertEqual((player["apps"], player["goals"], player["assists"]), (94, 2, 7))
        self.assertEqual((player["motm"], player["yellow"], player["red"]), (10, 5, 2))
        self.assertEqual((player["bosch_totals"]["apps"], player["bosch_totals"]["goals"]), (94, 2))
        self.assertEqual((player["career_totals"]["apps"], player["career_totals"]["goals"]), (94, 2))

        season = player["season_stats"]["146"]
        self.assertEqual((season["apps"], season["goals"], season["assists"]), (8, 1, 0))
        self.assertEqual((player["hala2526"]["apps"], player["hala2526"]["goals"]), (8, 1))
        self.assertEqual((player["season_coverage"]["unassigned"]["apps"], player["season_coverage"]["unassigned"]["goals"]), (0, 0))
        self.assertEqual(len([entry for entry in player["season_history"] if entry["sid"] == "146"]), 1)

    def test_unchanged_2026_results_and_no_double_counting(self):
        player = next(p for p in self.database["players"] if p["id"] == "7284")
        self.assertEqual((player["orlik2026"]["apps"], player["orlik2026"]["assists"]), (14, 5))
        season = self.database["analysis"]["player_goal_coverage"]
        hala = next(record for record in season if record["sid"] == "146")
        self.assertEqual(hala["attributed_goals"], 31)
        self.assertEqual(hala["unattributed_goals"], 0)

    def test_identity_guard_does_not_merge_other_people(self):
        primary = {"id": "7284", "name": "Rutkowski Mateusz (GK)", "season_stats": {}}
        duplicate = {"id": "13060", "name": "Nowak Tomasz", "season_stats": {}}

        with self.assertRaises(ValueError):
            merge_player_identities(
                [primary, duplicate],
                {"7284": {"duplicate_ids": ["13060"]}},
            )


if __name__ == "__main__":
    unittest.main()
