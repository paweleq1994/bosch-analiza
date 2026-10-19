import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from player_totals import bosch_totals, career_from_profile, confirm_bosch_totals

class PlayerTotalsTests(unittest.TestCase):
    def test_moskal_all_bosch_seasons_including_cup(self):
        # Verified PLP fixture values, not legacy archive 95/25/28.
        import json
        data=json.loads((Path(__file__).resolve().parents[1]/"data/player_season_updates.json").read_text())
        result=bosch_totals(data["1960"])
        self.assertEqual((result["apps"],result["goals"],result["assists"],result["motm"]),(105,23,33,4))
    def test_preserves_transfer_and_deduplicates_league_tables(self):
        bosch={"team":'<a href="https://podlaskaliga.pl/druzyna/bosch-service-tech-car/">Bosch</a>',"appearances":"12","goals":"3","assists":"5"}
        santos={"team":'<a href="https://podlaskaliga.pl/druzyna/santos/">Santos</a>',"appearances":"5","goals":"1","assists":"0"}
        profile={"statistics":{"a":{"120":bosch,"118":santos},"b":{"120":bosch}}}
        total=career_from_profile(profile,lambda x:int(x) if str(x).isdigit() else None)
        self.assertEqual((total["apps"],total["goals"],total["assists"]),(17,4,5))
        self.assertEqual(total["teams"],2)
    def test_does_not_double_count_alias_or_partial_data(self):
        same={"148":{"apps":2,"goals":1,"assists":0,"motm":0,"yellow":0,"red":0},"orlik-2026":{"apps":2,"goals":1,"assists":0,"motm":0,"yellow":0,"red":0}}
        self.assertEqual(bosch_totals(same)["apps"],2)
        incomplete={"146":{"apps":7,"goals":None,"assists":1,"motm":0,"yellow":0,"red":0}}
        self.assertIsNone(bosch_totals(incomplete)["goals"])
    def test_conflicting_alias_rejected(self):
        with self.assertRaises(ValueError):
            bosch_totals({"148":{"apps":1},"orlik-2026":{"apps":2}})

    def test_old_minimum_flags_require_independent_public_season_confirmation(self):
        import copy,json
        portal=json.loads((Path(__file__).resolve().parents[1]/"docs/assets/data.json").read_text(encoding="utf-8"))
        for identifier,apps in (("1594",2),("12286",1)):
            player=copy.deepcopy(next(p for p in portal["players"] if p["id"]==identifier))
            player["stats_minimum"]=True
            self.assertTrue(confirm_bosch_totals(player))
            self.assertFalse(player["stats_minimum"])
            self.assertEqual((player["apps"],player["goals"]),(apps,1))
            player["stats_minimum"]=True
            player["career_totals"]["public_season_rows"]=[]
            self.assertFalse(confirm_bosch_totals(player))
            self.assertTrue(player["stats_minimum"])

    def test_career_totals_cannot_promote_incomplete_club_statistics(self):
        import copy,json
        portal=json.loads((Path(__file__).resolve().parents[1]/"docs/assets/data.json").read_text(encoding="utf-8"))
        original=next(p for p in portal["players"] if p["id"]=="1594")
        for change in ("conflict","new-season","unknown"):
            player=copy.deepcopy(original);player["stats_minimum"]=True
            if change=="conflict":next(row for row in player["career_totals"]["public_season_rows"] if row["name"]=="Orlik 2025")["goals"]+=1
            elif change=="new-season":player["season_coverage"]["unassigned"]["apps"]=1
            else:player["season_stats"]["144"]["assists"]=None
            self.assertFalse(confirm_bosch_totals(player),change)
            self.assertTrue(player["stats_minimum"])

if __name__=="__main__":unittest.main()
