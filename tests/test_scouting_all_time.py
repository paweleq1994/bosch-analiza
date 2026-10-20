"""Career scouting must retain club scope and separate season statistics."""
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sync_scouting_players import parse_all_time, parse_public_players, read_all_time_players, ALL_TIME_LISTS
from build_scouting import all_time_players

PROFILE = "https://podlaskaliga.pl/zawodnik/example-player/"
SEASON = "https://podlaskaliga.pl/lista/example-season/"


def row(uri=PROFILE, name="Example Player", apps="10", goals="8", assists="2", rating="4.30"):
    return f'<tr><td class="data-name"><a href="{uri}">{name}</a></td><td class="data-team"><a href="https://podlaskaliga.pl/druzyna/example/">Example</a></td><td class="data-appearances">{apps}</td><td class="data-goals">{goals}</td><td class="data-assists">{assists}</td><td class="data-threethreethreesix">{rating}</td></tr>'


def table(rows):
    return '<table class="sp-player-list sp-paginated-table" data-sp-rows="25">'+rows+'</table>'


class AllTimeScoutingTests(unittest.TestCase):
    def test_classifications_read_all_pages_and_keep_unknowns_out(self):
        html = table(''.join(row(PROFILE+str(i)+"/") for i in range(30))+
                     row(uri="https://unrelated.test/player/")+row(uri=PROFILE+"missing/",goals="—"))
        parsed = parse_all_time(html, "scorers", ALL_TIME_LISTS["scorers"])
        self.assertEqual(len(parsed), 30)
        self.assertEqual(parsed[PROFILE+"29/"]["goals"], 8)
        self.assertEqual(parsed[PROFILE+"29/"]["source_url"], ALL_TIME_LISTS["scorers"])

    def test_goalkeeper_role_does_not_require_goals_or_assists(self):
        html = table(row(goals="", assists="", rating="4,30"))
        clubs = {"https://podlaskaliga.pl/druzyna/example": "1"}
        records = parse_public_players(html,"Orlik 2026",SEASON,clubs,goalkeeper=True)
        self.assertEqual(records["1"][0]["role"], "goalkeeper")
        self.assertIsNone(records["1"][0]["goals"])
        keeper = parse_all_time(html,"goalkeepers",ALL_TIME_LISTS["goalkeepers"])[PROFILE]
        self.assertEqual(keeper["rating"],4.3)
        with self.assertRaises(ValueError):
            parse_all_time(table(row(rating="—")),"goalkeepers",ALL_TIME_LISTS["goalkeepers"])

    def fixture(self):
        career = {"name":"Example Player","profile_url":PROFILE,"source_url":ALL_TIME_LISTS["scorers"],
                  "apps":100,"goals":50,"assists":30}
        roster = {"name":"Example Player","profile_url":PROFILE,"source_url":SEASON,"source_season":"Hala 2025/26",
                  "apps":2,"goals":1,"assists":0}
        return {"1":[roster],"_all_time":{"scorers":{PROFILE:career},"goalkeepers":{}}}

    def test_newer_club_wins_and_same_name_is_not_an_identity(self):
        data = self.fixture()
        data["2"] = [{**data["1"][0],"source_season":"Orlik 2026"}]
        self.assertFalse(all_time_players("1",data)["scorers"])
        self.assertEqual(all_time_players("2",data)["scorers"][0]["goals"],50)
        data["3"] = [{**data["1"][0],"profile_url":PROFILE+"unrelated/","source_season":"Orlik 2026"}]
        self.assertFalse(all_time_players("3",data)["scorers"])

    def test_ambiguous_same_season_club_is_not_guessed(self):
        data = self.fixture()
        data["2"] = deepcopy(data["1"])
        self.assertFalse(all_time_players("1",data)["scorers"])
        self.assertFalse(all_time_players("2",data)["scorers"])

    def test_repeated_season_rows_do_not_duplicate_career_or_change_season_totals(self):
        data = self.fixture()
        data["1"].extend(deepcopy(data["1"])*2)
        before = deepcopy(data)
        players = all_time_players("1",data)["scorers"]
        self.assertEqual(len(players),1)
        self.assertEqual(players[0]["club_season"],"Hala 2025/26")
        self.assertEqual(data,before)

    def test_goalkeeper_is_not_duplicated_in_scorers(self):
        data = self.fixture()
        data["_all_time"]["goalkeepers"][PROFILE] = {**data["_all_time"]["scorers"][PROFILE],"rating":4.5}
        players = all_time_players("1",data)
        self.assertFalse(players["scorers"])
        self.assertEqual(len(players["goalkeepers"]),1)

    def test_outage_keeps_last_verified_classification(self):
        data = self.fixture()
        def offline(url):
            raise OSError("offline")
        records, sources, warnings = read_all_time_players(data,data["_all_time"],offline)
        self.assertEqual(records,data["_all_time"])
        self.assertFalse(sources)
        self.assertEqual(len(warnings),2)

    def test_live_snapshot_has_all_rivals_and_added_scorers_and_keepers(self):
        db=json.loads((ROOT/"docs/assets/scouting.json").read_text(encoding="utf-8"))
        for team in db["teams"]:
            with self.subTest(team=team["name"]):
                career=team["all_time_players"]
                self.assertEqual(len(career["scorers"]),3)
                self.assertTrue(career["goalkeepers"])
                rows=career["scorers"]+career["goalkeepers"]
                self.assertEqual(len(rows),len({p["profile_url"] for p in rows}))
                self.assertTrue(all(p["club_source_url"].startswith("https://podlaskaliga.pl/lista/") for p in rows))
        krokus=next(t for t in db["teams"] if t["name"]=="Hurtownia Krokus")
        self.assertTrue(any(p["name"]=="Zaręba Przemysław" and p["goals"]>=141 for p in krokus["all_time_players"]["scorers"]))
        self.assertTrue(any(p["name"]=="Klikowski Dawid (GK)" for p in krokus["all_time_players"]["goalkeepers"]))


if __name__ == "__main__":
    unittest.main()
