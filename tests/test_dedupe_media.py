import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dedupe_portal import dedupe
from plp_photo_archive import identify

class PortalDeduplication(unittest.TestCase):
    def test_duplicate_fixture_preserves_separate_half_videos(self):
        doc={"seasons":[],"matches":[{"sid":"1","date":"2026-04-01","opponent":"Rywale","id":"a","gf":2,"ga":1,"videos":[{"video_id":"first"}]},{"sid":"1","date":"2026-04-01","opponent":"Rywale","id":"b","gf":2,"ga":1,"videos":[{"video_id":"second"}]}],"videos":[],"players":[],"analysis":{"scouting":[]},"meta":{}}
        result,warnings=dedupe(doc)
        self.assertEqual(len(result["matches"]),1)
        self.assertEqual(len(result["matches"][0]["videos"]),2)
        self.assertTrue(warnings)
    def test_conflicting_fixture_not_silently_merged(self):
        doc={"seasons":[],"matches":[{"sid":"1","date":"2026-04-01","opponent":"X","id":"a","gf":2,"ga":1},{"sid":"1","date":"2026-04-01","opponent":"X","id":"b","gf":3,"ga":1}],"videos":[],"players":[],"analysis":{},"meta":{}}
        with self.assertRaises(ValueError):dedupe(doc)
    def test_synthetic_player_dedup(self):
        real={"id":"1960","name":"Moskal Paweł","season_history":[]}
        ghost={"id":"new-moskal-pawel","name":"Moskal Paweł","orlik2026":{"goals":0},"season_history":[{"sid":"orlik-2026"}]}
        doc={"seasons":[],"matches":[],"videos":[],"players":[real,ghost],"analysis":{},"meta":{}}
        result,_=dedupe(doc)
        self.assertEqual(len(result["players"]),1)
        self.assertEqual(len(result["players"][0]["season_history"]),1)
    def test_public_media_requires_real_media_id(self):
        def fetch(path,params=None):
            if "/players/1960" in path:return {"featured_media":444}
            if path=="wp/v2/media/444":return {"id":444,"mime_type":"image/jpeg","source_url":"https://podlaskaliga.pl/wp-content/uploads/photo.jpg","date":"2024-04-01"}
            if path=="wp/v2/media":return []
            raise RuntimeError(path)
        self.assertEqual(len(identify("players","1960",fetch)),1)

if __name__=="__main__":unittest.main()
