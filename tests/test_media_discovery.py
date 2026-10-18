import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plp_media_discovery import classify_media, scan_media
from plp_photo_archive import sync


class MediaDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.players = [
            {"id": "2204", "name": "Dawid Daniluk", "has_photos": False},
            {"id": "1960", "name": "Moskal Paweł", "has_photos": True},
        ]

    def media(self, filename, media_id=900):
        return {
            "id": media_id,
            "source_url": "https://podlaskaliga.pl/wp-content/uploads/1995/01/" + filename,
            "mime_type": "image/jpeg",
            "post": 0,
            "title": {"rendered": "Archive"},
            "slug": "archive",
            "alt_text": "",
            "description": {"rendered": ""},
            "caption": {"rendered": ""},
        }

    def test_detached_filename_identifies_player_with_provenance(self):
        result, potential = classify_media(
            self.media("Daniluk-Dawid-2.jpg"),
            self.players,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["player_id"], "2204")
        self.assertEqual(result[0]["evidence"], "filename")
        self.assertFalse(potential)

    def test_surname_only_and_group_caption_do_not_auto_attach(self):
        result, _ = classify_media(self.media("Daniluk.jpg"), self.players)
        self.assertEqual(result, [])

        photo = self.media("zespol-bosch.jpg")
        photo["caption"] = {"rendered": "Dawid Daniluk i Paweł Moskal podczas meczu"}
        matched, candidates = classify_media(photo, self.players)
        self.assertEqual(matched, [])
        self.assertEqual(len(candidates), 2)

    def test_parent_matches_even_when_filename_is_generic(self):
        photo = self.media("6KT2782.jpg")
        photo["post"] = 2204
        matches, candidates = classify_media(photo, self.players)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["evidence"], "wordpress_parent")
        self.assertFalse(candidates)

    def test_rejects_invalid_media_and_untrusted_hosts(self):
        wrong = self.media("Daniluk-Dawid.jpg")
        wrong["source_url"] = "https://example.org/photo.jpg"
        self.assertEqual(classify_media(wrong, self.players), ([], []))
        wrong["source_url"] = "https://podlaskaliga.pl/media/photo.php"
        wrong["mime_type"] = "application/pdf"
        self.assertEqual(classify_media(wrong, self.players), ([], []))

    def test_scan_searches_and_paginates_without_double_counting(self):
        photo = self.media("Daniluk-Dawid.jpg")

        def fetch(path, params=None):
            self.assertEqual(path, "wp/v2/media")

            if "search" in params:
                return [photo] if params["search"] == "daniluk" else []

            if params["page"] == 1:
                return [photo]

            return []

        result, warnings = scan_media(
            self.players,
            {},
            fetch=fetch,
            max_pages=2,
            current_day="2026-10-18",
        )
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["scanned_media"], 0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["scanned_pages"], 1)
        self.assertFalse(warnings)
        repeated, warnings = scan_media(
            self.players,
            result,
            fetch=lambda path, params: self.fail("Same-day scan should be skipped"),
            current_day="2026-10-18",
        )
        self.assertEqual(repeated, result)
        self.assertFalse(warnings)

    def test_archiver_attaches_only_confirmed_discovery(self):
        def fetch(path, params=None):
            if path == "sportspress/v2/players/2204":
                return {"featured_media": 0}

            if path == "sportspress/v2/teams/6951":
                return {"featured_media": 0}

            if path == "wp/v2/media":
                return []

            raise AssertionError(path)

        discovered = {
            "matches": [{
                "player_id": "2204",
                "evidence": "filename",
                "photo": {
                    "id": "900",
                    "url": "https://podlaskaliga.pl/wp-content/uploads/Daniluk-Dawid.jpg",
                    "published": "2025-12-11",
                    "alt": "Daniluk Dawid",
                },
            }],
            "candidates": [{
                "player_id": "2204",
                "media_id": "901",
                "url": "https://podlaskaliga.pl/wp-content/uploads/team-photo.jpg",
            }],
        }

        def download(photo, folder):
            photo["local"] = "media/verified.jpg"

        output, warnings = sync({}, ["2204"], fetch=fetch, downloader=download, discovered=discovered)
        subject = next(row for row in output["subjects"] if row["id"] == "2204")
        self.assertEqual(len(subject["photos"]), 1)
        self.assertEqual(subject["photos"][0]["origin"], "public_archive_exact_metadata")
        self.assertEqual(subject["photos"][0]["local"], "media/verified.jpg")
        self.assertFalse(warnings)


if __name__ == "__main__":
    unittest.main()
