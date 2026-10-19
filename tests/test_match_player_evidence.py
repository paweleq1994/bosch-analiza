import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backfill_match_player_stats import backfill_seasons
from collect_match_player_evidence import event_stat, extract_match


class MatchPlayerEvidenceTests(unittest.TestCase):
    def test_timed_sportspress_values_are_not_discarded(self):
        self.assertEqual(event_stat("2 (3', 23')"), 2)
        self.assertEqual(event_stat("1 (22')"), 1)
        self.assertEqual(event_stat(""), 0)
        self.assertIsNone(event_stat("unknown goal"))

    def test_only_confirmed_lineups_are_counted(self):
        fixture = {
            "id": "7416",
            "event_id": "7416",
            "sid": "120",
            "date": "2022-11-20",
            "event_link": "https://podlaskaliga.pl/wydarzenie/bosch-service-tech-car-vs-fc-progress-bialystok/",
        }
        payload = {
            "id": 7416,
            "date": "2022-11-20T18:40:13",
            "link": fixture["event_link"],
            "teams": [6951, 6984],
            "performance": {"6951": {
                "7275": {"status": "lineup", "goals": "2 (3', 23')", "assists": "2", "yellowcards": "1 (22')"},
                "13060": {"status": "lineup", "goals": "", "assists": "1"},
                "17777": {"status": "", "goals": "", "assists": ""},
                "0": {"goals": "2"},
            }},
        }
        result = extract_match(fixture, payload, {"13060": "7284"})
        self.assertEqual(len(result["players"]), 2)
        self.assertEqual(result["players"][0]["player_id"], "7275")
        self.assertEqual(result["players"][0]["goals"], 2)
        self.assertEqual(result["players"][0]["yellow"], 1)
        self.assertEqual(result["players"][1]["player_id"], "7284")

    def test_wrong_match_source_is_rejected(self):
        fixture = {"id": "1", "event_id": "1", "sid": "120", "date": "2022-01-01",
                   "event_link": "https://podlaskaliga.pl/wydarzenie/a/"}
        event = {"id": 1, "link": "https://example.com/wydarzenie/a/", "date": "2022-01-01",
                 "teams": [6951, 6984], "performance": {"6951": {"7275": {"status": "lineup"}}}}

        with self.assertRaises(ValueError):
            extract_match(fixture, event, {})


class BackfillPlayerEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data/match_player_evidence.json"
        cls.evidence = json.loads(path.read_text(encoding="utf-8"))
        cls.matches = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))["matches"]

    def test_full_evidence_has_113_distinct_matches_and_source_urls(self):
        matches = self.evidence["matches"]
        self.assertEqual(len(matches), 113)
        self.assertEqual(len({record["match_id"] for record in matches}), 113)
        self.assertTrue(all(record["source_url"].startswith("https://podlaskaliga.pl/wydarzenie/") for record in matches))

    def test_reconstructs_archived_player_seasons_without_guessing_career_totals(self):
        players = [
            {"id": "7282", "name": "Markowski Damian", "apps": 6, "goals": 2, "assists": 1, "motm": 0,
             "yellow": 0, "red": 0, "season_stats": {"125": {"apps": 3, "goals": 1, "assists": 1}}},
            {"id": "7285", "name": "Sołowiej Tomasz", "apps": 32, "goals": 22, "assists": 13,
             "motm": 3, "yellow": 1, "red": 0, "season_stats": {"125": {"apps": 11, "goals": 10, "assists": 3}}},
        ]
        report = backfill_seasons(players, self.matches, self.evidence)
        markowski, solowiej = players
        self.assertEqual(markowski["season_stats"]["120"]["apps"], 3)
        self.assertEqual(markowski["apps"], 6)
        self.assertEqual(solowiej["season_stats"]["120"]["apps"], 13)
        self.assertEqual(solowiej["season_stats"]["139"]["apps"], 7)
        self.assertEqual(solowiej["season_stats"]["139"]["assists"], 3)
        self.assertEqual(solowiej["apps"], 32)
        self.assertEqual(report["verified_matches"], 113)

    def test_rejects_partial_fixture_archive(self):
        with self.assertRaises(ValueError):
            backfill_seasons([], self.matches, {"matches": self.evidence["matches"][:112]})


if __name__ == "__main__":
    unittest.main()
