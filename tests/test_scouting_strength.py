import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scouting_strength import season_strength, team_strength
from build_scouting import historical_players, head_to_head
from sync_scouting_players import read_team_players, integer


class ScoutingStrengthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standings = json.loads((ROOT / "data" / "scouting_updates.json").read_text(encoding="utf-8"))
        cls.overrides = json.loads((ROOT / "data" / "scouting_player_overrides.json").read_text(encoding="utf-8"))
        cls.promotions = json.loads((ROOT / "data" / "promoted_teams_analysis.json").read_text(encoding="utf-8"))

    def team(self, division, name):
        return next(
            (row for row in self.standings["tables"][division] if row["name"] == name),
            None,
        )

    def test_first_league_runner_up_outscores_second_league_champion(self):
        high_hall = self.team("hala_2025_26_h1", "4Technology")
        high_orlik = self.team("orlik_2026_h1", "4Technology")
        lower = self.team("orlik_2026_h2", "Biuro Serwis-Kopiarki")
        self.assertEqual(high_orlik["position"], 2)
        self.assertEqual(lower["position"], 1)
        self.assertGreater(team_strength(high_hall, high_orlik), team_strength(None, lower))
        self.assertGreater(team_strength(high_hall, high_orlik) - team_strength(None, lower), 10)

    def test_match_archive_keeps_renames_and_rejects_same_name_different_club(self):
        matches = [
            {"id": "1", "date": "2025-01-01", "opponent": "Aptel", "opponent_id": 1574},
            {"id": "2", "date": "2026-01-01", "opponent": "Soccer Auto Wygoda", "opponent_id": 1574},
            {"id": "3", "date": "2026-02-01", "opponent": "Soccer Auto Wygoda", "opponent_id": 999},
            {"id": "4", "date": "2024-01-01", "opponent": "Aptel", "opponent_id": None},
            {"id": "5", "date": "2024-02-01", "opponent": "Soccer Auto Wygoda", "opponent_id": None},
        ]
        self.assertEqual([m["id"] for m in head_to_head(matches, "Soccer Auto Wygoda", "1574")], ["2", "1", "4"])
        self.assertEqual(head_to_head(matches, "Soccer Auto Wygoda", None), [])

    def test_scouting_archive_includes_all_official_opponent_ids_and_seasons(self):
        portal = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        scouting = json.loads((ROOT / "docs/assets/scouting.json").read_text(encoding="utf-8"))
        for team in scouting["teams"]:
            with self.subTest(team=team["name"]):
                expected = [m for m in portal["matches"] if str(m.get("opponent_id")) == team["plp_team_id"]]
                history = team["h2h"]
                self.assertEqual({m["id"] for m in history["matches"]}, {m["id"] for m in expected})
                self.assertEqual(history["games"], len(expected))
                self.assertEqual(history["wins"] + history["draws"] + history["losses"], len(expected))
                self.assertEqual((history["gf"], history["ga"]), (sum(m["gf"] for m in expected), sum(m["ga"] for m in expected)))
                self.assertTrue(all(m["season"] and m["opponent"] and m["event_link"] for m in history["matches"]))

    def test_league_tier_and_sample_size_are_material(self):
        first = self.team("orlik_2026_h1", "4Technology")
        equivalent_second = {**first, "tier": 2}
        self.assertGreater(season_strength(first), season_strength(equivalent_second))

        small_sample = {**first, "matches": 2, "points": 5, "gf": 11, "ga": 3}
        self.assertIsNotNone(season_strength(small_sample))

    def test_dudko_and_previous_league_players_are_named_not_anonymous(self):
        high = historical_players("4Technology", "1576", {}, [], [], {}, self.overrides, {})
        self.assertEqual(high[0]["name"], "Dudko Jakub")
        self.assertEqual((high[0]["goals"], high[0]["assists"]), (35, 10))
        self.assertEqual(high[0]["source_season"], "Orlik 2026")
        self.assertTrue(high[0]["source_url"].startswith("https://podlaskaliga.pl/"))

        historical = historical_players(
            "PROSTAL",
            "12343",
            {},
            [],
            self.promotions["player_rows"],
            {},
            {},
            {},
        )
        self.assertTrue(any(row["name"] == "Mackiewicz Karol" for row in historical))
        self.assertTrue(all(not row["name"].startswith("Zawodnik #") for row in historical))

    def test_zero_goals_are_valid_and_team_must_match(self):
        self.assertEqual(integer(0), 0)
        payload = [{
            "id": 400,
            "title": {"rendered": "Example Scorer"},
            "link": "https://podlaskaliga.pl/zawodnik/example-scorer/",
            "statistics": {
                "league": {
                    "148": {
                        "team": '<a href="/druzyna/4technology/">4Technology</a>',
                        "appearances": "8",
                        "goals": "0",
                        "assists": "3",
                        "pikarzmeczu": "0",
                    },
                    "146": {
                        "team": '<a href="/druzyna/unrelated/">Unrelated</a>',
                        "appearances": "10",
                        "goals": "25",
                        "assists": "0",
                    },
                }
            },
        }]
        result = read_team_players(
            {"team_id": 1576, "name": "4Technology"},
            fetch=lambda url: payload,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["goals"], 0)
        self.assertEqual(result[0]["assists"], 3)


if __name__ == "__main__":
    unittest.main()
