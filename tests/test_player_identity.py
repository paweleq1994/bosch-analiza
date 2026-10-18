import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from player_identity import has_bosch_season, legacy_player_id, match_public_profile, person_key
from player_totals import career_from_profile
import build_portal


class PlayerIdentityTests(unittest.TestCase):
    def test_name_order_and_polish_characters(self):
        self.assertEqual(person_key("Dawid Daniluk"), person_key("Daniluk Dawid"))
        self.assertEqual(person_key("Filip Szparło"), person_key("Szparło Filip"))
        self.assertEqual(legacy_player_id("Filip Szparło"), "new-filip-szpar-o")

    def test_matches_only_unique_public_profile(self):
        profiles = {
            "2204": {"resolved_name": "Daniluk Dawid", "public": True},
            "42": {"resolved_name": "Daniluk Dawid", "public": False},
        }
        self.assertEqual(match_public_profile("Dawid Daniluk", profiles)[0], "2204")
        profiles["42"]["public"] = True
        self.assertIsNone(match_public_profile("Dawid Daniluk", profiles))

    def test_verifies_bosch_membership(self):
        self.assertTrue(has_bosch_season({
            "statistics": {
                "142": {"148": {"team": '<a href="/druzyna/bosch-service-tech-car/">Bosch</a>', "appearances": "4"}}
            }
        }))
        self.assertFalse(has_bosch_season({
            "statistics": {"142": {"148": {"team": '<a href="/druzyna/other/">Other</a>'}}}
        }))

    def test_duplicate_zero_appearance_does_not_hide_real_season(self):
        profile = {"statistics": {
            "league_1": {
                "55": {"team": '<a href="/druzyna/znienacka/">Znienacka</a>', "appearances": "8", "goals": "3", "assists": "2"}
            },
            "league_2": {
                "55": {"team": '<a href="/druzyna/znienacka/">Znienacka</a>', "appearances": "0", "goals": "0", "assists": "0"}
            },
        }}
        total = career_from_profile(profile, lambda value: int(value) if str(value).isdigit() else None)
        self.assertEqual((total["apps"], total["goals"], total["assists"]), (8, 3, 2))

    def test_daniluk_is_canonical_and_old_link_remains_supported(self):
        build_portal.main()
        data = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
        matches = [player for player in data["players"] if person_key(player["name"]) == person_key("Dawid Daniluk")]

        self.assertEqual(len(matches), 1)
        player = matches[0]
        self.assertEqual(player["id"], "2204")
        self.assertIn("new-dawid-daniluk", player["aliases"])
        self.assertEqual(player["profile_url"], "https://podlaskaliga.pl/zawodnik/daniluk-dawid/")
        self.assertEqual(
            (player["orlik2026"]["apps"], player["orlik2026"]["goals"], player["orlik2026"]["assists"]),
            (12, 16, 6),
        )

    def test_supercup_participation_comes_from_each_players_own_data(self):
        build_portal.main()
        data = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
        updates = json.loads((ROOT / "data" / "player_season_updates.json").read_text(encoding="utf-8"))

        for player in data["players"]:
            expected = {
                str(season_id)
                for season_id, stats in updates.get(str(player["id"]), {}).items()
                if str(season_id) in {"119", "127", "140", "145"} and (stats.get("apps") or 0) > 0
            }
            observed = {
                str(record["sid"])
                for record in player.get("season_history", [])
                if str(record["sid"]) in {"119", "127", "140", "145"}
            }
            self.assertEqual(observed, expected, player["name"])


if __name__ == "__main__":
    unittest.main()
