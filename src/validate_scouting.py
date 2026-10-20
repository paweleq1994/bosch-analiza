#!/usr/bin/env python3
"""Check public scouting output and disclaimers before publishing."""
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]
data=json.loads((p/"docs/assets/scouting.json").read_text(encoding="utf-8"))
teams=data["teams"]
assert len(teams)>=12
assert len({team["id"] for team in teams})==len(teams)
assert all(team["status"] in ("candidate","confirmed_from_table") for team in teams)
assert all(0<=team["strength"]<=100 for team in teams if team["strength"] is not None)
assert all(team["confidence"] in ("średnia","niska","wysoka") for team in teams)
assert all(team["scouting_status"]=="statistical_only" for team in teams)
assert all(not team["observations"] for team in teams)
assert all(video.get("url","").startswith("https://www.youtube.com/watch?v=") for team in teams for video in team["videos"])
assert all(team["plan_a"] and team["plan_b"] for team in teams)
assert all(player.get("source_url","").startswith("https://podlaskaliga.pl/") and player.get("source_season")
           and player.get("name") and not player["name"].startswith("Zawodnik #")
           for team in teams for player in team["players"])
for team in teams:
    career=team["all_time_players"]
    assert len(career["scorers"])<=3 and len(career["goalkeepers"])<=2
    players=career["scorers"]+career["goalkeepers"]
    assert len({player["profile_url"] for player in players})==len(players)
    assert all(player["profile_url"].startswith("https://podlaskaliga.pl/zawodnik/")
               and player["club_source_url"].startswith("https://podlaskaliga.pl/lista/")
               and player["club_season"] and type(player["apps"]) is int and player["apps"]>0 for player in players)
    assert all(player["source_url"]=="https://podlaskaliga.pl/lista/alltime-strzelec/"
               and type(player["goals"]) is int and player["goals"]>0
               and type(player["assists"]) is int and player["assists"]>=0 for player in career["scorers"])
    assert all(player["source_url"]=="https://podlaskaliga.pl/lista/bramkarze-alltime/"
               and 0<=player["rating"]<=5 for player in career["goalkeepers"])
assert data["meta"]["forecast_not_confirmed"] or all(team["status"]=="confirmed_from_table" for team in teams)
assert (p/"docs/scouting.html").exists()
print("Scouting validation OK:",len(teams),"provisional opponents")
