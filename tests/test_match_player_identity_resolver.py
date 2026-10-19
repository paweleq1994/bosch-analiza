import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from resolve_match_player_identities import (
    PlayerAnchorParser,
    resolve,
    update_profile_map,
)


class SourceVerifiedPlayerIdentityTests(unittest.TestCase):
    def test_unpublished_id_is_recovered_from_official_match_anchor(self):
        parser = PlayerAnchorParser()
        parser.feed(
            '<td class="data-name"><a href="https://podlaskaliga.pl/'
            '?post_type=sp_player&amp;p=10321">Ciborowski Julian</a></td>'
        )
        self.assertEqual(parser.anchors, [("10321", "Ciborowski Julian")])

    def test_private_source_identity_is_preserved_without_fabricating_public_profile(self):
        fixture_url = "https://podlaskaliga.pl/wydarzenie/vesta-vs-bosch-service-tech-car/"
        archive = {
            "matches": [{
                "source_url": fixture_url,
                "players": [{"player_id": "10321"}],
            }]
        }

        def fetch(url, json_only=False):
            if "sportspress" in url:
                raise HTTPError(url, 401, "Unauthorized", {}, None)
            self.assertEqual(url, fixture_url)
            return (
                '<tr><td class="data-name"><a href="https://podlaskaliga.pl/'
                '?post_type=sp_player&amp;p=10321">Ciborowski Julian</a></td></tr>'
            )

        result = resolve(archive, {}, {"players": {}}, get=fetch)
        player = result["players"]["10321"]
        self.assertEqual(player["name"], "Ciborowski Julian")
        self.assertEqual(player["public_url"], "")
        self.assertEqual(player["source"], "plp_official_match_page_linked_id")
        self.assertEqual(player["evidence_urls"], [fixture_url])
        updated = update_profile_map(result, {})
        self.assertFalse(updated["10321"]["public"])
        self.assertEqual(updated["10321"]["resolved_name"], "Ciborowski Julian")

    def test_existing_conflicting_name_is_not_silently_reassigned(self):
        resolved = {"players": {
            "10321": {
                "name": "Ciborowski Julian",
                "public_url": "",
                "source": "plp_official_match_page_linked_id",
                "evidence_urls": ["https://podlaskaliga.pl/wydarzenie/vesta-vs-bosch-service-tech-car/"],
                "verified": True,
            }
        }}
        with self.assertRaises(ValueError):
            update_profile_map(resolved, {
                "10321": {"resolved_name": "Kowalski Jan"}
            })

    def test_unresolved_record_is_not_published_as_player(self):
        archive = {
            "matches": [{
                "source_url": "https://podlaskaliga.pl/wydarzenie/unknown/",
                "players": [{"player_id": "99999"}],
            }]
        }

        def fetch(url, json_only=False):
            if "sportspress" in url:
                raise HTTPError(url, 404, "Not Found", {}, None)
            return '<table><tr><td>Brak profilu</td></tr></table>'

        result = resolve(archive, {}, {"players": {}}, get=fetch)
        self.assertEqual(result["players"], {})
        self.assertIn("99999", result["unresolved"])


if __name__ == "__main__":
    unittest.main()
