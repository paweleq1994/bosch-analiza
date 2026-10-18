#!/usr/bin/env python3
"""Check public scouting output and disclaimers before publishing."""
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1]
data=json.loads((p/"docs/assets/scouting.json").read_text(encoding="utf-8"))
teams=data["teams"]
assert len(teams)>=12
assert len({team["id"] for team in teams})==len(teams)
assert all(team["status"]=="candidate" for team in teams)
assert all(0<=team["strength"]<=100 for team in teams if team["strength"] is not None)
assert all(team["confidence"] in ("średnia","niska","wysoka") for team in teams)
assert all(team["scouting_status"]=="statistical_only" for team in teams)
assert all(not team["observations"] and not team["videos"] for team in teams)
assert all(team["plan_a"] and team["plan_b"] for team in teams)
assert "prognoz" in data["meta"]["note"].lower() or data["meta"]["forecast_not_confirmed"]
assert (p/"docs/scouting.html").exists()
print("Scouting validation OK:",len(teams),"provisional opponents")
