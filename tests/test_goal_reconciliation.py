import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal
from goal_reconciliation import (
    add_verified_players,
    administrative_goals_by_season,
    resolve_identity,
    validate_goal_evidence,
)


class GoalAttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((ROOT / "data" / "goal_evidence.json").read_text(encoding="utf-8"))
        build_portal.main()
        cls.portal = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
        cls.seasons = cls.portal["seasons"]
        cls.matches = cls.portal["matches"]
        cls.players = cls.portal["players"]

    def test_documented_new_scorers_are_present_and_distinct(self):
        wojciuk = [player for player in self.players if "wojciuk" in player["name"].lower()]
        pietruczuk = [player for player in self.players if "pietruczuk" in player["name"].lower()]

        self.assertEqual(len(wojciuk), 1)
        self.assertEqual(len(pietruczuk), 1)
        self.assertEqual(pietruczuk[0]["id"], "12286")
        self.assertEqual(
            (wojciuk[0]["apps"], wojciuk[0]["goals"], wojciuk[0]["assists"]),
            (5, 2, 2),
        )
        self.assertEqual(pietruczuk[0]["goals"], 1)
        self.assertTrue(pietruczuk[0]["stats_minimum"])

    def test_official_player_and_match_evidence_stays_with_original_seasons(self):
        wojciuk = next(player for player in self.players if "wojciuk" in player["name"].lower())
        pietruczuk = next(player for player in self.players if "pietruczuk" in player["name"].lower())
        official = next(row for row in wojciuk["season_history"] if row["sid"] == "orlik-2026")
        minimum = next(row for row in pietruczuk["season_history"] if row["sid"] == "144")

        self.assertEqual((official["apps"], official["goals"], official["assists"]), (5, 2, 2))
        self.assertEqual(minimum["goals"], 1)
        self.assertEqual(minimum["apps"], 1)
        self.assertEqual(minimum["assists"], 0)
        self.assertIn(minimum["origin"], {"plp_match_minimum", "plp_match_protocols"})

    def test_final_reconciliation_separates_awarded_goals_from_scorers(self):
        coverage = {str(row["sid"]): row for row in self.portal["analysis"]["player_goal_coverage"]}
        self.assertEqual(
            (coverage["orlik-2026"]["attributed_goals"], coverage["orlik-2026"]["unattributed_goals"]),
            (59, 0),
        )
        self.assertEqual(
            (coverage["144"]["attributed_goals"], coverage["144"]["unattributed_goals"]),
            (36, 0),
        )
        self.assertEqual(
            (
                coverage["146"]["attributed_goals"],
                coverage["146"]["administrative_goals"],
                coverage["146"]["unattributed_goals"],
            ),
            (31, 1, 0),
        )
        self.assertEqual(sum(row["unattributed_goals"] for row in coverage.values()), 0)
        self.assertEqual(sum(row["administrative_goals"] for row in coverage.values()), 1)

        for row in coverage.values():
            self.assertEqual(
                row["team_goals"],
                row["attributed_goals"] + row["administrative_goals"] + row["opponent_own_goals"] + row["unattributed_goals"],
                row["season"],
            )

    def test_verified_match_references_and_administrative_score(self):
        validate_goal_evidence(self.evidence, self.seasons, self.matches)
        adjustments = administrative_goals_by_season(self.evidence)

        self.assertEqual(adjustments["146"]["goals"], 1)
        self.assertEqual(adjustments["146"]["events"][0]["match_id"], "12656")

    def test_unverified_fixture_or_wrong_team_cannot_be_credited(self):
        wrong_event = copy.deepcopy(self.evidence)
        wrong_event["players"][1]["match_event_id"] = "invalid"

        with self.assertRaises(ValueError):
            validate_goal_evidence(wrong_event, self.seasons, self.matches)

        wrong_score = copy.deepcopy(self.evidence)
        wrong_score["administrative_adjustments"][0]["awarded_goals"] = 4

        with self.assertRaises(ValueError):
            validate_goal_evidence(wrong_score, self.seasons, self.matches)

        bad_source = copy.deepcopy(self.evidence)
        bad_source["players"][0]["source_url"] = "https://example.org/wojciuk"

        with self.assertRaises(ValueError):
            validate_goal_evidence(bad_source, self.seasons, self.matches)

    def test_verified_stats_are_not_added_twice(self):
        players = []
        profiles = {
            "777": {
                "public": True,
                "resolved_name": "Wojciuk Piotr",
                "profile_url": "https://podlaskaliga.pl/zawodnik/wojciuk-piotr/",
            },
        }
        season_details = {}
        evidence = {"players": [self.evidence["players"][0]]}

        add_verified_players(players, profiles, evidence, season_details)
        self.assertEqual(season_details["777"]["148"]["goals"], 2)
        self.assertEqual(len(players), 1)

        add_verified_players(players, profiles, evidence, season_details)
        self.assertEqual(season_details["777"]["148"]["goals"], 2)
        self.assertEqual(len(players), 1)

        different = copy.deepcopy(evidence)
        different["players"][0]["goals"] = 4

        with self.assertRaises(ValueError):
            add_verified_players(players, profiles, different, season_details)

    def test_existing_player_name_must_match_verified_id(self):
        with self.assertRaises(ValueError):
            resolve_identity(
                {"name": "Piotr Wojciuk", "player_id": "12286"},
                {"12286": {"resolved_name": "Pietruczuk Paweł"}},
            )

    def test_historical_goals_remain_unassigned_without_independent_evidence(self):
        coverage = {str(row["sid"]): row for row in self.portal["analysis"]["player_goal_coverage"]}
        self.assertEqual(coverage["120"]["unattributed_goals"], 0)
        self.assertEqual(coverage["125"]["unattributed_goals"], 0)
        self.assertEqual(coverage["139"]["unattributed_goals"], 0)
        self.assertEqual(coverage["144"]["unattributed_goals"], 0)
        self.assertEqual(coverage["146"]["unattributed_goals"], 0)


if __name__ == "__main__":
    unittest.main()
