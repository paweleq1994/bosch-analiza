import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_plp_sitemaps import discover_players, parse_sitemap, scan, render_report


class PublicSourceSitemapTests(unittest.TestCase):
    def test_namespace_sitemap_index_and_public_profiles(self):
        index = b"""<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://podlaskaliga.pl/wp-sitemap-posts-sp_player-1.xml</loc></sitemap>
</sitemapindex>"""
        child = b"""<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://podlaskaliga.pl/zawodnik/ciborowski-julian/</loc></url>
</urlset>"""
        nested, locations = parse_sitemap(index)
        self.assertEqual(
            nested,
            ["https://podlaskaliga.pl/wp-sitemap-posts-sp_player-1.xml"],
        )
        self.assertEqual(locations, {})

        def fetch(url):
            if url.endswith("wp-sitemap.xml"):
                return 200, index
            if url.endswith("wp-sitemap-posts-sp_player-1.xml"):
                return 200, child
            return 404, b""

        found = scan(get=fetch, pause=lambda: None)
        self.assertEqual(
            list(found["pages"]),
            ["https://podlaskaliga.pl/zawodnik/ciborowski-julian/"],
        )

    def test_candidate_page_needs_exact_wordpress_post_id(self):
        index = {"pages": {
            "https://podlaskaliga.pl/zawodnik/ciborowski-julian/": [],
        }}
        players = [{"id": "10321", "name": "Ciborowski Julian", "profile_url": ""}]

        def fetch(url):
            return 200, b'<body class="single sp_player postid-10321">'

        recovered = discover_players(index, players, get=fetch)
        self.assertEqual(
            recovered["verified"]["10321"]["url"],
            "https://podlaskaliga.pl/zawodnik/ciborowski-julian/",
        )
        self.assertEqual(recovered["missing"], {})

    def test_similar_name_cannot_prove_another_player_id(self):
        index = {"pages": {
            "https://podlaskaliga.pl/zawodnik/ciborowski-julian/": [],
        }}
        players = [{"id": "10321", "name": "Ciborowski Julian", "profile_url": ""}]
        recovered = discover_players(
            index, players, get=lambda _: (200, b'<body class="postid-54321">')
        )
        self.assertEqual(recovered["verified"], {})
        self.assertIn("10321", recovered["missing"])
        report = render_report({
            "sitemaps": [], "pages": index["pages"], "truncated": False,
        }, recovered)
        self.assertIn("Ciborowski Julian", report)
        self.assertIn("Dopasowania potwierdzone numerem postu: **0**", report)


if __name__ == "__main__":
    unittest.main()
