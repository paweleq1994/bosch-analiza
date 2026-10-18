import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal
from protocol_goals import enrich_from_protocols


class FullPLPMatchProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        cls.database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        cls.players = {str(player["id"]): player for player in cls.database["players"]}
        cls.matches = {str(match["id"]): match for match in cls.database["matches"]}
        cls.seasons = {str(row["sid"]): row for row in cls.database["analysis"]["player_goal_coverage"]}

    def test_all_113_matches_reconcile_goals(self):
        self.assertEqual(len(self.matches), 113)
        self.assertEqual(sum(row["team_goals"] for row in self.seasons.values()), 293)
        self.assertEqual(sum(row["attributed_goals"] for row in self.seasons.values()), 289)
        self.assertEqual(sum(row["opponent_own_goals"] for row in self.seasons.values()), 3)
        self.assertEqual(sum(row["administrative_goals"] for row in self.seasons.values()), 1)
        self.assertEqual(sum(row["unattributed_goals"] for row in self.seasons.values()), 0)
        self.assertEqual(self.database["analysis"]["match_protocol_audit"]["total_own_goals_conceded"], 6)

        for match in self.matches.values():
            with self.subTest(match=match["id"]):
                protocol = match.get("goal_protocol")
                self.assertIsNotNone(protocol)
                self.assertTrue(protocol["verified"])
                self.assertTrue(protocol["source_url"].startswith("https://podlaskaliga.pl/"))
                self.assertEqual(
                    match["gf"],
                    protocol["player_goals"] + protocol["own_goals"] + protocol["administrative_goals"],
                )
                self.assertEqual(
                    protocol["player_goals"],
                    sum(row["goals"] for row in protocol["scorers"]),
                )

    def test_all_seven_formerly_missing_goals_have_direct_sources(self):
        missing_scorers = {
            ("7851", "7282"): 1,
            ("10157", "7285"): 1,
            ("10254", "7285"): 1,
        }

        for (match_id, player_id), goals in missing_scorers.items():
            with self.subTest(match=match_id):
                self.assertEqual(
                    next(row["goals"] for row in self.matches[match_id]["goal_protocol"]["scorers"] if row["player_id"] == player_id),
                    goals,
                )

        self.assertEqual(self.matches["12165"]["goal_protocol"]["player_goals"], 1)
        self.assertEqual(self.matches["12165"]["goal_protocol"]["scorers"][0]["name"], "Kakareko Kamil")
        self.assertEqual(self.matches["7788"]["goal_protocol"]["own_goals"], 1)
        self.assertEqual(self.matches["8366"]["goal_protocol"]["own_goals"], 1)
        self.assertEqual(self.matches["12617"]["goal_protocol"]["own_goals"], 1)
        self.assertEqual(self.matches["12656"]["goal_protocol"]["administrative_goals"], 1)

    def test_vesta_player_goal_with_unknown_minute_is_not_discarded(self):
        record = self.matches["9755"]["goal_protocol"]
        self.assertEqual(record["player_goals"], 1)
        self.assertEqual(record["minute_uncertainties"], 1)
        self.assertEqual(record["scorers"][0]["player_id"], "7277")
        self.assertEqual(record["scorers"][0]["minutes"], [])
        self.assertTrue(record["scorers"][0]["minute_uncertain"])
        self.assertEqual(self.players["7277"]["season_stats"]["126"]["goals"], 2)

    def test_rutkowski_has_single_profile_and_both_source_goals(self):
        self.assertIn("7284", self.players)
        self.assertNotIn("13060", self.players)
        rutkowski = self.players["7284"]
        self.assertIn("13060", rutkowski["aliases"])
        self.assertEqual((rutkowski["apps"], rutkowski["goals"], rutkowski["assists"]), (90, 2, 7))
        self.assertEqual((rutkowski["career_totals"]["apps"], rutkowski["career_totals"]["goals"]), (90, 2))
        self.assertEqual(
            (rutkowski["season_stats"]["146"]["apps"], rutkowski["season_stats"]["146"]["goals"]),
            (8, 1),
        )
        self.assertEqual(rutkowski["season_stats"]["141"]["goals"], 1)
        self.assertEqual(len(rutkowski["goal_matches"]), 2)
        self.assertEqual(
            {row["match_id"] for row in rutkowski["goal_matches"]},
            {"11412", "12633"},
        )
        self.assertTrue(any("rutkowski-mateusz-2" in url for url in rutkowski["alternate_profile_urls"]))

    def test_new_kakareko_profile_and_historical_goals(self):
        kakareko = [player for player in self.players.values() if player["name"] == "Kakareko Kamil"]
        self.assertEqual(len(kakareko), 1)
        self.assertEqual(kakareko[0]["goals"], 1)
        self.assertIsNone(kakareko[0]["apps"])
        self.assertTrue(kakareko[0]["stats_minimum"])
        self.assertEqual(kakareko[0]["season_stats"]["144"]["goals"], 1)
        self.assertEqual(self.players["7282"]["season_stats"]["120"]["goals"], 1)
        self.assertEqual(self.players["7285"]["season_stats"]["139"]["goals"], 2)
        self.assertEqual(self.players["7285"]["season_coverage"]["unassigned"]["goals"], 0)

    def test_separate_six_bosch_own_goals_without_inflating_offensive_stats(self):
        self.assertEqual(self.players["1960"]["own_goals_conceded"], 4)
        self.assertEqual(self.players["1970"]["own_goals_conceded"], 1)
        self.assertEqual(self.players["7277"]["own_goals_conceded"], 1)
        self.assertEqual(self.matches["7839"]["goal_protocol"]["own_goals_conceded"], 1)
        self.assertEqual(self.matches["7839"]["goal_protocol"]["own_goals_conceded_scorers"][0]["player_id"], "1960")
        self.assertEqual(sum(player["own_goals_conceded"] for player in self.players.values()), 6)

    def test_no_duplicate_player_scorers_in_any_match(self):
        for match in self.matches.values():
            protocol = match["goal_protocol"]
            scorer_ids = [row["player_id"] for row in protocol["scorers"]]
            self.assertEqual(len(scorer_ids), len(set(scorer_ids)), match["id"])
            self.assertTrue(all(player_id in self.players for player_id in scorer_ids))

    def test_malicious_or_incomplete_protocols_are_rejected(self):
        source = json.loads((ROOT / "data" / "match_protocol_audit_index.json").read_text(encoding="utf-8"))
        duplicate = {"matches": source["matches"][:112]}
        matches = copy.deepcopy(self.database["matches"])
        players = copy.deepcopy(self.database["players"])
        profiles = json.loads((ROOT / "data" / "player_profile_map.json").read_text(encoding="utf-8"))

        with self.assertRaises(ValueError):
            enrich_from_protocols(matches, players, profiles, duplicate, {"13060": "7284"})

        wrong_url = copy.deepcopy(source)
        wrong_url["matches"][0]["event_url"] = "https://example.org/stolen"

        with self.assertRaises(ValueError):
            enrich_from_protocols(matches, players, profiles, wrong_url, {"13060": "7284"})

        corrupt = copy.deepcopy(source)
        corrupt["matches"][0]["official_team_goals"] += 1

        with self.assertRaises(ValueError):
            enrich_from_protocols(matches, players, profiles, corrupt, {"13060": "7284"})


if __name__ == "__main__":
    unittest.main()
