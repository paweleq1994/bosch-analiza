import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from media_identity import canonicalize_player_media


class CanonicalPhotoGalleryTests(unittest.TestCase):
    def test_preserves_distinct_photos_and_their_original_source(self):
        manifest = {
            "subjects": [
                {"kind": "players", "id": "7284", "photos": [{"id": "100", "url": "https://podlaskaliga.pl/one.jpg"}]},
                {"kind": "players", "id": "13060", "photos": [
                    {"id": "100", "url": "https://podlaskaliga.pl/one.jpg"},
                    {"id": "200", "url": "https://podlaskaliga.pl/two.jpg"},
                ]},
                {"kind": "teams", "id": "13060", "photos": [{"id": "300", "url": "https://podlaskaliga.pl/team.jpg"}]},
            ]
        }
        merged = canonicalize_player_media(manifest, {"13060": "7284"})
        goalkeeper = next(row for row in merged["subjects"] if row["kind"] == "players")

        self.assertEqual(goalkeeper["id"], "7284")
        self.assertEqual([photo["id"] for photo in goalkeeper["photos"]], ["100", "200"])
        self.assertEqual(goalkeeper["photos"][1]["source_player_id"], "13060")
        self.assertEqual(next(row for row in merged["subjects"] if row["kind"] == "teams")["id"], "13060")

    def test_real_archive_has_one_rutkowski_gallery_without_losing_photos(self):
        manifest = json.loads((ROOT / "data" / "media_manifest.json").read_text(encoding="utf-8"))
        source = [
            subject
            for subject in manifest["subjects"]
            if subject["kind"] == "players" and str(subject["id"]) in {"7284", "13060"}
        ]
        merged = canonicalize_player_media(manifest, {"13060": "7284"})
        records = [
            subject
            for subject in merged["subjects"]
            if subject["kind"] == "players" and str(subject["id"]) in {"7284", "13060"}
        ]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "7284")
        self.assertEqual(
            {photo["id"] for row in source for photo in row["photos"]},
            {photo["id"] for photo in records[0]["photos"]},
        )


if __name__ == "__main__":
    unittest.main()
