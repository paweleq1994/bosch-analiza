import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from resolve_current_players import roster_season, refresh_rosters


class OfficialRosters(unittest.TestCase):
    def test_zero_appearance_member_keeps_official_identity_and_source(self):
        source = {"seasons": [148], "leagues": [123],
                  "link": "https://podlaskaliga.pl/lista/roster/",
                  "data": {"99": {"name": "Nowy Zawodnik", "team": "6951", "appearances": "0"},
                           "100": {"name": "Inny Klub", "team": "1", "appearances": "0"}}}
        season = {"id": "orlik-2026", "plp_id": "148", "league_ids": ["123"]}
        roster = roster_season(season, [source])
        self.assertEqual(set(roster["members"]), {"99"})
        self.assertEqual(roster["members"]["99"]["listed_apps"], 0)
        self.assertEqual(roster["members"]["99"]["source_urls"], [source["link"]])

    def test_other_division_zero_does_not_hide_real_appearances(self):
        season = {"id": "146", "league_ids": ["123"]}
        wrong = {"seasons": [146], "leagues": [122], "data": {"99": {"name": "Test", "team": "6951", "appearances": "0"}}}
        with self.assertRaises(ValueError):
            roster_season(season, [wrong])
        previous = {"146": {"members": {"99": {"listed_apps": 4}}}}
        updated, warnings = refresh_rosters([season], previous, lambda _: [wrong])
        self.assertEqual(updated, previous)
        self.assertTrue(warnings)

    def test_live_archive_preserves_zero_member_and_separate_card_types(self):
        db = json.loads((ROOT / "docs/assets/data.json").read_text("utf-8"))
        player = next(p for p in db["players"] if p["id"] == "12288")
        self.assertEqual(player["season_stats"]["144"]["apps"], 0)
        self.assertFalse(any(p["player_id"] == "12288" for m in db["matches"] for p in m.get("player_performance", [])))
        doubles = [(m, p) for m in db["matches"] for p in m.get("player_performance", []) if p.get("yellow") == 2]
        self.assertEqual(len(doubles), 7)
        for match, entry in doubles:
            self.assertEqual(entry["red"], 0)
            self.assertEqual(entry["second_yellow"], 1)
            self.assertEqual(entry["dismissals"], 1)
