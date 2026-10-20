import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from player_totals import bosch_totals, career_from_profile, confirm_bosch_totals, reconcile_public_supercups

class PlayerTotalsTests(unittest.TestCase):
    def test_moskal_all_bosch_seasons_including_cup(self):
        # Public cup rows override REST league aggregates that omit those cups.
        import json
        data=json.loads((Path(__file__).resolve().parents[1]/"data/player_season_updates.json").read_text())
        root=Path(__file__).resolve().parents[1]
        careers=json.loads((root/"data/player_career_updates.json").read_text(encoding="utf-8"))
        snapshots=json.loads((root/"data/player_html_career_snapshot.json").read_text(encoding="utf-8"))["players"]
        reconcile_public_supercups(data,careers,snapshots)
        result=bosch_totals(data["1960"])
        self.assertEqual((result["apps"],result["goals"],result["assists"],result["motm"]),(109,24,33,4))

    def test_supercup_reconciliation_is_idempotent_and_does_not_import_other_clubs(self):
        import copy
        public={"name":"Superpuchar 2023","apps":2,"goals":2,"assists":2,"motm":0,"yellow":0,"red":0}
        snapshot={"1":{"source_url":"https://podlaskaliga.pl/zawodnik/example/","season_rows":[public]}}
        career={"1":{"season_rows":[{"sid":"127","name":"Superpuchar 2023","team":"Bosch Service Tech-Car"}]}}
        seasons={"1":{"127":{key:0 for key in ("apps","goals","assists","motm","yellow","red")}}}
        review=reconcile_public_supercups(seasons,career,snapshot)
        self.assertEqual(review[0]["status"],"restored_from_public_html")
        self.assertEqual(seasons["1"]["127"]["apps"],2)
        saved=copy.deepcopy(seasons)
        self.assertEqual(reconcile_public_supercups(seasons,career,snapshot)[0]["status"],"already_included")
        self.assertEqual(seasons,saved)
        career["1"]["season_rows"][0]["team"]="Other Club"
        empty={}
        self.assertEqual(reconcile_public_supercups(empty,career,snapshot)[0]["status"],"other_club_excluded")
        self.assertFalse(empty)
        career["1"]["season_rows"].append({"sid":"127","name":"Superpuchar 2023","team":"Bosch Service Tech-Car"})
        self.assertEqual(reconcile_public_supercups(empty,career,snapshot)[0]["status"],"club_scope_unverified")
        self.assertFalse(empty)

    def test_lower_html_cannot_erase_an_independent_supercup_protocol(self):
        public={"name":"Superpuchar 2025","apps":1,"goals":0,"assists":0,"motm":0,"yellow":0,"red":0}
        snapshot={"1":{"source_url":"https://podlaskaliga.pl/zawodnik/example/","season_rows":[public]}}
        career={"1":{"season_rows":[{"sid":"145","name":"Superpuchar 2025","team":"Bosch Service Tech-Car"}]}}
        seasons={"1":{"145":{**public,"apps":2}}}
        self.assertEqual(reconcile_public_supercups(seasons,career,snapshot)[0]["status"],"existing_source_exceeds_html")
        self.assertEqual(seasons["1"]["145"]["apps"],2)

    def test_every_verified_bosch_cup_is_in_season_history_and_player_totals(self):
        import json
        portal=json.loads((Path(__file__).resolve().parents[1]/"docs/assets/data.json").read_text(encoding="utf-8"))
        players={p["id"]:p for p in portal["players"]}
        checked=0
        for source in portal["analysis"]["supercup_reconciliation"]:
            if source["status"] not in {"restored_from_public_html","already_included"}:continue
            player=players[source["player_id"]]
            history=next(row for row in player["season_history"] if row["sid"]==source["season_id"])
            for field in ("apps","goals","assists","motm","yellow","red"):
                self.assertGreaterEqual(history[field],source["public"][field])
                self.assertGreaterEqual(player[field],source["public"][field])
            checked+=1
        self.assertGreaterEqual(checked,28)
        self.assertEqual((players["7276"]["season_stats"]["127"]["apps"],players["7276"]["season_stats"]["127"]["goals"],players["7276"]["season_stats"]["127"]["assists"]),(2,2,2))
        self.assertGreaterEqual(players["7276"]["apps"],46)
        self.assertGreaterEqual(players["7272"]["apps"],105)
        self.assertEqual(players["8654"]["season_stats"]["140"]["red"],1)
        self.assertNotEqual(players["1960"]["apps"],players["1960"]["career_totals"]["apps"])
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
