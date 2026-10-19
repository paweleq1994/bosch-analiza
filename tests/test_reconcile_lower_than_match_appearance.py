import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backfill_match_player_stats import backfill_seasons
from build_portal import main


class ReconciledMinimumSeasonCountsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )
        cls.evidence = json.loads(
            (ROOT / "data/match_player_evidence.json").read_text(encoding="utf-8")
        )

    def test_official_goalkeeper_appearance_fixes_wrong_zero_season_row(self):
        players = [{
            "id": "7223", "name": "Grabowski Jakub (GK)",
            "apps": 1, "goals": 0, "assists": 0,
            "motm": 0, "yellow": 0, "red": 0,
            "season_stats": {"126": {"apps": 0, "goals": 0}},
        }]
        report = backfill_seasons(players, self.database["matches"], self.evidence)
        season = players[0]["season_stats"]["126"]
        self.assertEqual(season["apps"], 1)
        self.assertTrue(season["match_performance_verified"])
        self.assertEqual(season["corrected_from_lower_season_values"]["apps"], 0)
        corrections = [item for item in report["filled"] if item["field"] == "apps"]
        self.assertTrue(any(item["player_id"] == "7223" and item["value"] == 1 for item in corrections))

    def test_never_decreases_larger_verified_season_total(self):
        players = [{
            "id": "7223", "name": "Grabowski Jakub (GK)",
            "apps": 3, "goals": 0, "assists": 0,
            "motm": 0, "yellow": 0, "red": 0,
            "season_stats": {"126": {"apps": 3}},
        }]
        report = backfill_seasons(players, self.database["matches"], self.evidence)
        self.assertEqual(players[0]["season_stats"]["126"]["apps"], 3)
        self.assertTrue(any(
            item["player_id"] == "7223"
            and item["reason"] == "season_total_exceeds_known_match_performance"
            for item in report["conflicts"]
        ))

    def test_portal_preserves_historic_team_goal_attribution(self):
        main()
        result = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )
        keeper = next(player for player in result["players"] if player["id"] == "7223")
        self.assertEqual(keeper["season_stats"]["126"]["apps"], 1, msg={
            "keeper": keeper,
            "source_audit": [item for item in result["analysis"]["match_player_backfill"]["conflicts"] if item["player_id"]=="7223"],
            "filled": [item for item in result["analysis"]["match_player_backfill"]["filled"] if item["player_id"]=="7223"],
        })
        self.assertEqual(keeper["season_coverage"]["unassigned"]["apps"], 0)
        self.assertEqual(
            sum(row["unattributed_goals"] for row in result["analysis"]["player_goal_coverage"]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
