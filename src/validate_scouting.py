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
assert data["meta"]["forecast_not_confirmed"] or all(team["status"]=="confirmed_from_table" for team in teams)
assert (p/"docs/scouting.html").exists()
print("Scouting validation OK:",len(teams),"provisional opponents")
