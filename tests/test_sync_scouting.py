"""Regression checks for PLP scouting table ingestion."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("scouting_sync",Path(__file__).resolve().parents[1]/"src/sync_scouting.py")
sync=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

def fixture(points=4, broken=False):
    data={}
    for index in range(1,10):
        won,drawn,lost=(1,1,0) if index==1 else (1,0,1)
        if broken and index==1:points=99
        data[str(index)]={"name":f"Team {index}","pos":str(index),"m":"2","w":str(won),"r":str(drawn),"p":str(lost),"pkt":str(points if index==1 else 3),"g":"2","s":"2"}
    return {"title":{"rendered":"I LIGA – Hala’26/27"},"slug":"i-liga-hala26-27","data":data}

class ScoutingSyncTests(unittest.TestCase):
    def test_valid_table(self):
        result=sync.parse_table(fixture())
        self.assertEqual(result[0],"hala_2026_27_h1")
        self.assertEqual(len(result[1]),9)
    def test_rejects_wrong_points(self):
        self.assertIsNone(sync.parse_table(fixture(broken=True)))
    def test_preserve_snapshot_on_bad_table(self):
        old={"tables":{"hala_2025_26_h1":[{"name":"Old"}]},"season_ids":{}}
        new,warnings=sync.collect({"seasons":[160]},lambda sid:[fixture(broken=True)],old)
        self.assertEqual(new["tables"],old["tables"])
    def test_valid_edition_alias(self):
        self.assertEqual(sync.edition("II LIGA – Orlik’26"),"orlik_2026")
if __name__=="__main__":unittest.main()
