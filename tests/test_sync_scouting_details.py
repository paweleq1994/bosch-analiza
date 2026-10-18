import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("details",Path(__file__).resolve().parents[1]/"src/sync_scouting_details.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def event(goals=2):
    return {"id":99,"date":"2026-01-09","title":{"rendered":"Test vs Rival"},"teams":[10,20],
    "results":{"10":{"goals":str(goals)},"20":{"goals":"1"}},
    "performance":{"10":{"101":{"status":"lineup","goals":str(goals),"assists":"1"}}}}
class DetailTests(unittest.TestCase):
    def test_extract(self):
        matches,players,complete=mod.detail([event()],10)
        self.assertTrue(complete);self.assertEqual(matches[0]["gf"],2)
        self.assertEqual(players[0]["goals"],2)
    def test_reject_mismatch(self):
        snap={"season_ids":{"hala_2025_26_h1":"146"},"tables":{"hala_2025_26_h1":[{"name":"Test","team_id":"10","matches":1,"gf":4,"ga":1}]}}
        result,warnings=mod.collect(snap,{"teams":{}},lambda sid,tid:[event()])
        self.assertFalse(result["teams"]);self.assertTrue(warnings)
    def test_keep_previous(self):
        snap={"season_ids":{"hala_2025_26_h1":"146"},"tables":{"hala_2025_26_h1":[{"name":"Test","team_id":"10","matches":1,"gf":2,"ga":1}]}}
        old={"teams":{"hala_2025_26_h1:10":{"source":"validated previous"}}}
        result,warnings=mod.collect(snap,old,lambda sid,tid: (_ for _ in ()).throw(RuntimeError("offline")))
        self.assertEqual(result,old)
if __name__=="__main__":unittest.main()
