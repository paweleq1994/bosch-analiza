import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal


class VerifiedHistoricalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        cls.database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        cls.matches = {str(match["id"]): match for match in cls.database["matches"]}
        cls.players = {str(player["id"]): player for player in cls.database["players"]}
        cls.coverage = {str(row["sid"]): row for row in cls.database["analysis"]["player_goal_coverage"]}

    def test_every_protocol_is_linked(self):
        self.assertEqual(len(self.matches), 113)
        self.assertEqual(len([row for row in self.matches.values() if row.get("protocol")]), 113)
        self.assertTrue(all(row["protocol"]["source_url"] == row["event_link"] for row in self.matches.values()))

    def test_exact_missing_goals_are_confirmed(self):
        markowski = self.players["7282"]
        solowiej = self.players["7285"]
        kakareko = self.players["new-kakareko-kamil"]

        self.assertEqual(markowski["season_stats"]["120"]["goals"], 1)
        self.assertEqual(solowiej["season_stats"]["139"]["goals"], 2)
        self.assertEqual(solowiej["goals"], 22)
        self.assertEqual(kakareko["season_stats"]["144"]["goals"], 1)
        self.assertTrue(kakareko["stats_minimum"])
        self.assertIsNone(kakareko["apps"])
        self.assertEqual(len(kakareko["protocol_goals"]), 1)

    def test_three_own_goals_and_one_walkover(self):
        self.assertEqual(sum(row["opponent_own_goals"] for row in self.coverage.values()), 3)
        self.assertEqual(sum(row["administrative_goals"] for row in self.coverage.values()), 1)
        self.assertEqual(sum(row["unattributed_goals"] for row in self.coverage.values()), 0)

        for row in self.coverage.values():
            self.assertEqual(
                row["team_goals"],
                row["attributed_goals"] + row["opponent_own_goals"] + row["administrative_goals"],
            )

    def test_specific_goals_and_minutes(self):
        self.assertEqual(self.matches["7851"]["protocol"]["scorers"][-1]["minutes"], ["29"])
        self.assertEqual(self.matches["10157"]["protocol"]["scorers"][-1]["minutes"], ["17"])
        self.assertEqual(self.matches["10254"]["protocol"]["scorers"][-1]["minutes"], ["30"])
        self.assertEqual(self.matches["12165"]["protocol"]["scorers"][0]["minutes"], ["22"])

    def test_unreadable_vesta_marker_is_not_fabricated(self):
        self.assertFalse(self.matches["9755"]["protocol"]["complete"])
        self.assertEqual(self.matches["9755"]["protocol"]["unreadable_goal_markers"], 1)
        self.assertFalse(self.matches["9755"]["protocol"]["scorers"])

    def test_duplicate_goalkeeper_is_still_single_identity(self):
        goalkeeper = self.players["7284"]
        self.assertNotIn("13060", self.players)
        self.assertIn("13060", goalkeeper["aliases"])
        self.assertEqual((goalkeeper["apps"], goalkeeper["goals"]), (90, 2))


if __name__ == "__main__":
    unittest.main()
