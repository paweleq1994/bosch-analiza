import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("sync_plp", Path(__file__).resolve().parents[1] / "src/sync_plp.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

def table(m,w,d,l,gf,ga,pts):
    return [{"title":{"rendered":"II Liga – Orlik 2026"},"slug":"ii-liga-orlik-2026","data":{"6951":{"pos":"2","pkt":str(pts),"m":str(m),"w":str(w),"r":str(d),"p":str(l),"g":str(gf),"s":str(ga)}}}]

def match(mid,day,gf,ga):
    return {"id":mid,"date":day,"title":{"rendered":"Bosch Service Tech-Car vs VESTA"},"teams":[6951,11],"results":{"6951":{"goals":str(gf)},"11":{"goals":str(ga)}},"performance":{"6951":{"123":{"status":"lineup","goals":str(gf),"assists":"0"}}}}

KNOWN=[{"id":"orlik-2026","name":"Orlik 2026"}]
LEGACY=[{"id":"orlik26-1","sid":"orlik-2026","date":"2026-04-19","opponent":"VESTA"}]

class SynchronizationTests(unittest.TestCase):
    def test_existing_season_receives_new_match_and_correction(self):
        old,valid,err=sync.synchronize({"seasons":[234]},lambda _:table(1,1,0,0,2,1,3),lambda _:[match(901,"2026-04-19",2,1)],{},KNOWN,LEGACY,{})
        self.assertEqual(len(valid),1)
        self.assertEqual(old["matches"][0]["id"],"orlik26-1")
        newer,valid,err=sync.synchronize({"seasons":[234]},lambda _:table(2,1,0,1,3,2,3),lambda _:[match(901,"2026-04-19",3,1),match(902,"2026-05-19",0,1)],old,KNOWN,LEGACY,{})
        self.assertEqual([x["gf"] for x in newer["matches"]],[3,0])
        self.assertEqual(newer["season_rows"][0]["matches"],2)
        self.assertEqual(newer["player_seasons"][0]["goals"],3)
        self.assertEqual(newer["matches"][0]["id"],"orlik26-1")
        self.assertFalse(err)
    def test_mismatch_retains_snapshot(self):
        previous,_,_=sync.synchronize({"seasons":[234]},lambda _:table(1,1,0,0,2,1,3),lambda _:[match(901,"2026-04-19",2,1)],{},KNOWN,LEGACY,{})
        after,valid,errors=sync.synchronize({"seasons":[234]},lambda _:table(2,2,0,0,5,2,6),lambda _:[match(901,"2026-04-19",2,1)],previous,KNOWN,LEGACY,{})
        self.assertEqual(previous,after)
        self.assertFalse(valid)
        self.assertTrue(errors)
    def test_future_fixture_not_scored(self):
        fixture=match(901,"2099-04-19","","")
        self.assertIsNone(sync.parse_event(fixture,234,"orlik-2026","Orlik 2026",LEGACY,{}))
    def test_repeat_is_idempotent(self):
        args=({"seasons":[234]},lambda _:table(1,1,0,0,2,1,3),lambda _:[match(901,"2026-04-19",2,1)])
        first,_,_=sync.synchronize(*args,{},KNOWN,LEGACY,{})
        again,_,_=sync.synchronize(*args,first,KNOWN,LEGACY,{})
        self.assertEqual(first,again)

if __name__=="__main__": unittest.main()
