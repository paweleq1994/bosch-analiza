import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from player_identity import has_bosch_season, legacy_player_id, match_public_profile, person_key
from player_totals import career_from_profile
import build_portal
from resolve_current_players import candidate_slugs, find_profile, resolve


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

    def test_resolves_accented_new_player_from_verified_wordpress_page(self):
        name = "Adam Malesiński"
        self.assertEqual(candidate_slugs(name), ["malesinski-adam"])
        payload = {
            "id": 999,
            "title": {"rendered": "Malesiński Adam"},
            "link": "https://podlaskaliga.pl/zawodnik/malesinski-adam/",
            "statistics": {
                "league": {
                    "148": {
                        "team": '<a href="/druzyna/bosch-service-tech-car/">Bosch</a>',
                        "appearances": "0",
                    }
                }
            },
        }

        def fetch(url):
            return [] if "players?search=" in url else payload

        def fetch_page(url):
            self.assertEqual(url, "https://podlaskaliga.pl/zawodnik/malesinski-adam/")
            return (
                "<html><title>Malesiński Adam – Podlaska Liga</title>"
                '<link rel="shortlink" href="https://podlaskaliga.pl/?p=999">'
                "</html>"
            )

        resolved = find_profile(name, fetch=fetch, fetch_page=fetch_page)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0], "999")
        self.assertEqual(resolved[1]["source"], "verified_current_roster")

        profiles, warnings = resolve(
            {},
            [{"name": name}],
            find=lambda value: resolved,
        )
        self.assertFalse(warnings)
        self.assertEqual(profiles["999"]["resolved_name"], "Malesiński Adam")

    def test_refuses_unverified_or_ambiguous_public_identity(self):
        payload = {
            "id": 456,
            "title": {"rendered": "Inny Zawodnik"},
            "link": "https://podlaskaliga.pl/zawodnik/rogon-damian/",
            "statistics": {
                "league": {
                    "148": {
                        "team": '<a href="/druzyna/bosch-service-tech-car/">Bosch</a>',
                        "appearances": "5",
                    }
                }
            },
        }
        resolved = find_profile(
            "Damian Rogon",
            fetch=lambda url: [] if "players?search=" in url else payload,
            fetch_page=lambda url: '<title>Rogon Damian – Podlaska Liga</title><body class="postid-456">',
        )
        self.assertIsNone(resolved)

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
        corrections = json.loads((ROOT / "data" / "player_stat_corrections.json").read_text(encoding="utf-8"))

        for player in data["players"]:
            expected = {
                str(season_id)
                for season_id, stats in updates.get(str(player["id"]), {}).items()
                if str(season_id) in {"119", "127", "140", "145"} and (stats.get("apps") or 0) > 0
            }
            expected.update(
                str(season_id)
                for season_id, stats in (corrections.get(str(player["id"])) or {}).get("seasons", {}).items()
                if str(season_id) in {"119", "127", "140", "145"} and (stats.get("apps") or 0) > 0
            )
            observed = {
                str(record["sid"])
                for record in player.get("season_history", [])
                if str(record["sid"]) in {"119", "127", "140", "145"}
            }
            self.assertEqual(observed, expected, player["name"])


    def test_jurkowicz_all_career_plp_supercups_are_reconciled(self):
        build_portal.main()
        database = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
        player = next(person for person in database["players"] if person["id"] == "7275")
        self.assertEqual((player["apps"], player["goals"], player["assists"]), (69, 30, 20))
        self.assertEqual(
            (player["career_totals"]["apps"], player["career_totals"]["goals"]),
            (69, 30),
        )
        supercups = {str(row["sid"]): row for row in player["season_history"] if str(row["sid"]) in {"127", "140"}}
        self.assertEqual(supercups["127"]["goals"], 1)
        self.assertEqual(supercups["140"]["apps"], 1)


if __name__ == "__main__":
    unittest.main()
