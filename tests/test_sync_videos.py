import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("vid",Path(__file__).resolve().parents[1]/"src/sync_videos.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Videos(unittest.TestCase):
    def setUp(self):
        self.matches=[
          {"id":"orlik26-1","sid":"orlik-2026","opponent":"IST Trade","gf":1,"ga":1},
          {"id":"orlik26-13","sid":"orlik-2026","opponent":"UNIBEP S.A.","gf":5,"ga":0},
          {"id":"orlik26-14","sid":"orlik-2026","opponent":"FC Progress Białystok","gf":4,"ga":1}]
    def test_actual_channel_titles(self):
        examples=[
          ("tllBiVSXg4o","FC PROGRESS BIAŁYSTOK 1:4 BOSCH SERVICE TECH-CAR | II POŁOWA","orlik26-14"),
          ("rJg795Aer3A","UNIBEP S.A. 0:5 BOSCH SERVICE TECH-CAR | II POŁOWA","orlik26-13"),
          ("gqBY10ItvgA","IST TRADE 1 - 1 BOSCH SERVICE TECH-CAR | II POŁOWA (ZOOM 200%)","orlik26-1")]
        for id,title,match_id in examples:
            with self.subTest(id=id):self.assertEqual(mod.match_video({"title":title},self.matches),match_id)
    def test_does_not_misidentify_old_match(self):
        self.assertIsNone(mod.match_video({"title":"Bosch Service Tech-Car 1:2 Progress"},self.matches))
    def test_sync_keeps_archive_and_matches(self):
        videos=[{"id":"tllBiVSXg4o","title":"FC PROGRESS BIAŁYSTOK 1:4 BOSCH SERVICE TECH-CAR | II POŁOWA"},
                {"id":"UvrBdNIANlM","title":"Bosch Service Tech-Car 3:2 FC Grubassy | II połowa"}]
        result,added,warnings=mod.sync([{"handle":"martawnuszynska9993","name":"Marta Wnuszynska"}],
            {"videos":[],"manual_bindings":{}},{"videos":[{"id":"UvrBdNIANlM"}],"matches":self.matches},
            lambda _:videos)
        self.assertEqual(added,1)
        self.assertEqual(result["videos"][0]["match_id"],"orlik26-14")
        self.assertEqual(result["videos"][0]["status"],"matched_auto")
        self.assertFalse(warnings)
    def test_youtube_outage_keeps_previous(self):
        prev={"videos":[{"id":"tllBiVSXg4o","match_id":"orlik26-14","status":"matched_auto"}],"manual_bindings":{}}
        new,added,warnings=mod.sync([{"handle":"martawnuszynska9993","name":"Marta Wnuszynska"}],
          prev,{"matches":self.matches,"videos":[]},
          lambda _: (_ for _ in ()).throw(RuntimeError("rate limit")))
        self.assertEqual(new,prev)
        self.assertEqual(added,0)
        self.assertEqual(len(warnings),1)
if __name__=="__main__":unittest.main()
