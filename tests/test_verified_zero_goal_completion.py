import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_portal import main
from complete_verified_goal_zeros import complete_protocol_goal_fields

CONFIRMED_ZERO_SEASONS = {
    ("10321", "139"),
    ("7271", "120"),
    ("7271", "139"),
    ("7270", "120"),
    ("7270", "126"),
    ("7278", "120"),
    ("8916", "139"),
    ("10604", "139"),
}


class ZeroGoalsSourceCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main()
        cls.db = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )

    def test_eight_historically_unknown_season_goal_fields_are_verified_zero(self):
        by_id = {str(player["id"]): player for player in self.db["players"]}
        for player_id, season_id in CONFIRMED_ZERO_SEASONS:
            with self.subTest(id=player_id, sid=season_id):
                player = by_id[player_id]
                stats = player["season_stats"][season_id]
                self.assertEqual(stats["goals"], 0)
                self.assertTrue(stats["goals_verified_by_protocol"])

    def test_filling_zeros_cannot_change_team_total_or_goal_scorers(self):
        goals = self.db["analysis"]["player_goal_coverage"]
        self.assertEqual(sum(item["team_goals"] for item in goals), 293)
        self.assertEqual(sum(item["unattributed_goals"] for item in goals), 0)
        self.assertEqual(sum(item["attributed_goals"] for item in goals), 289)

    def test_partial_season_does_not_get_fabricated_zero(self):
        players = [{
            "id": "1995", "name": "Unknown Person",
            "season_stats": {"demo": {"apps": 1, "goals": None}},
        }]
        matches = [{
            "id": "1", "sid": "demo", "event_link": "https://podlaskaliga.pl/wydarzenie/demo/",
            "goal_protocol": {"verified": False, "scorers": []},
        }]
        self.assertEqual(complete_protocol_goal_fields(players, matches), [])
        self.assertIsNone(players[0]["season_stats"]["demo"]["goals"])


if __name__ == "__main__":
    unittest.main()
