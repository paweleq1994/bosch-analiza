import importlib.util
from pathlib import Path
import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("vid",Path(__file__).resolve().parents[1]/"src/sync_videos.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Videos(unittest.TestCase):
    def test_existing_archive_metadata_is_refreshed_without_changing_binding(self):
        old={"videos":[{"id":"tllBiVSXg4o","title":"Known","date":"","match_id":"orlik26-14","status":"matched_manual"}],"manual_bindings":{"tllBiVSXg4o":{"match_id":"orlik26-14"}}}
        result, added, warnings=mod.sync([{"name":"Marta"}],old,{"videos":old["videos"],"matches":[]},lambda _: [{"id":"tllBiVSXg4o","date":"20261011"}])
        self.assertEqual(result["videos"][0]["date"],"2026-10-11")
        self.assertEqual(result["videos"][0]["match_id"],"orlik26-14")
        self.assertEqual(added,0)
        self.assertFalse(warnings)

    def test_detail_metadata_failure_preserves_archive(self):
        previous={"videos":[{"id":"tllBiVSXg4o","date":"","match_id":"orlik26-14"}],"manual_bindings":{}}
        result,warnings=mod.refresh_metadata(previous,{},lambda _: (_ for _ in ()).throw(ValueError("No date")))
        self.assertEqual(result,previous)
        self.assertEqual(len(warnings),1)
        result,warnings=mod.refresh_metadata(previous,{},lambda _: {"date":"20261011","length_seconds":1190})
        self.assertEqual(result["videos"][0]["date"],"2026-10-11")
        self.assertEqual(result["videos"][0]["length_seconds"],1190)
        self.assertFalse(warnings)
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
    def test_official_channel_reads_live_archive_by_verified_id_and_filters_other_teams(self):
        source={"name":"Podlaska Liga Piłkarska","channel_id":"UCd0p73Dp5Eya7c4tQ8EoLZA",
                "tab":"streams","title_contains":"Bosch"}
        payload={"entries":[{"id":"3A0-Z_98lKQ","title":"APTEL vs BOSCH SERVICE TECH-CAR"},
                            {"id":"35diG4RKe0M","title":"Turbo Podlasiak"}]}
        with patch.object(mod.subprocess,"run",return_value=SimpleNamespace(returncode=0,stdout=json.dumps(payload))) as run:
            videos=mod.list_channel(source)
        self.assertEqual([v["id"] for v in videos],["3A0-Z_98lKQ"])
        self.assertEqual(run.call_args.args[0][-1],"https://www.youtube.com/channel/UCd0p73Dp5Eya7c4tQ8EoLZA/streams")
        self.assertIsNone(videos[0]["match_id"])
        self.assertEqual(videos[0]["status"],"needs_review")
if __name__=="__main__":unittest.main()
