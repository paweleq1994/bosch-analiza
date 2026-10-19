import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_portal import main


class HistoricTeamPhotoEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main()
        cls.db = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))

    def test_daniluk_has_historic_team_photo_leads_but_no_invented_portrait(self):
        links = [
            item for item in self.db["analysis"]["historical_team_media_candidates"]
            if item["player_id"] == "2204"
        ]
        self.assertGreaterEqual(len(links), 10)
        self.assertTrue(any(item["team"] == "Znienacka" for item in links))
        self.assertTrue(all(item["evidence"] == "historical_team_archive_unverified_person"
                            for item in links))
        confirmed = [
            item for item in (self.db.get("media") or {}).get("subjects") or []
            if item.get("kind") == "players"
            and str(item.get("id")) == "2204"
            and item.get("photos")
        ]
        self.assertEqual(confirmed, [])

    def test_all_photo_leads_are_official_plp_attachments(self):
        for item in self.db["analysis"]["historical_team_media_candidates"]:
            self.assertTrue(item["url"].startswith(
                "https://podlaskaliga.pl/wp-content/uploads/"
            ))
            self.assertTrue(item["player_id"].isdigit())


if __name__ == "__main__":
    unittest.main()
