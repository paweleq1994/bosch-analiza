#!/usr/bin/env python3
"""Fetch official opponent match logs and season player stats; no guessed events."""
from collections import defaultdict
from datetime import date
from html import unescape
from pathlib import Path
import json
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"scouting_details.json"
STANDINGS=ROOT/"data"/"scouting_updates.json"
SEED=ROOT/"data"/"scouting_2026_27_seed.json"
BASE="https://podlaskaliga.pl/wp-json/sportspress/v2"
COLUMNS={"goals":"goals","assists":"assists","motm":"pikarzmeczu","yellow":"yellowcards","red":"redcards"}
def get(path,params=None):
    url=BASE+"/"+path+("?" + urlencode(params) if params else "")
    with urlopen(Request(url,headers={"User-Agent":"BoschScout/1.0"}),timeout=30) as response:return json.load(response)
def number(x):
    return int(str(x)) if re.fullmatch(r"\d+",str(x or "").strip()) else None
def clean(x):
    if isinstance(x,dict):x=x.get("rendered","")
    return unescape(re.sub(r"<[^>]*>","",str(x or ""))).strip()
def pages(season,team):
    all_items=[]
    for page in range(1,6):
        rows=get("events",{"seasons":season,"teams":team,"page":page,"per_page":100})
        if not isinstance(rows,list):raise ValueError("Unexpected match response")
        all_items.extend(rows)
        if len(rows)<100:return all_items
    raise ValueError("Too many event pages")
def detail(events,team):
    matches=[]; people=defaultdict(lambda:{"apps":0,"goals":0,"assists":0,"motm":0,"yellow":0,"red":0})
    complete=True
    for event in events:
        ids=[number(i) for i in event.get("teams",[])]
        if team not in ids or len(ids)!=2:continue
        opponent=next((i for i in ids if i!=team),None)
        r=event.get("results") or {}
        gf=number((r.get(str(team)) or {}).get("goals"));ga=number((r.get(str(opponent)) or {}).get("goals"))
        if gf is None or ga is None:continue
        match={"event_id":str(event["id"]),"date":str(event.get("date") or "")[:10],"opponent_id":str(opponent),"title":clean(event.get("title")),"gf":gf,"ga":ga,"url":event.get("link") or ""}
        matches.append(match)
        performance=(event.get("performance") or {}).get(str(team))
        if not isinstance(performance,dict) or not performance:
            complete=False
            continue
        used=0
        for pid,record in performance.items():
            if not str(pid).isdigit() or int(pid)==0 or not isinstance(record,dict):continue
            appeared=bool(str(record.get("status") or "").strip()) or any(str(record.get(k) or "").strip() for k in COLUMNS.values())
            if not appeared:continue
            values={k:number(record.get(v)) if record.get(v) not in (None,"") else 0 for k,v in COLUMNS.items()}
            if any(v is None for v in values.values()):complete=False;continue
            used+=1
            entry=people[str(pid)]
            entry["apps"]+=1
            for k,v in values.items():entry[k]+=v
        if not used:complete=False
    return matches, [{"id":pid,**stat} for pid,stat in people.items()] if complete else [],complete
def team_signature(team):
    return {key: team.get(key) for key in ("matches", "wins", "draws", "losses", "gf", "ga", "points")}

def cache_fresh(old, team, today=None):
    if not old or old.get("standing_signature") != team_signature(team):
        return False
    try:
        checked = date.fromisoformat(old["verified_at"])
        elapsed = (today or date.today()) - checked
        return 0 <= elapsed.days < 7
    except (KeyError, ValueError, TypeError):
        return False

def collect(snapshot, previous, fetch):
    updated=dict(previous.get("teams") or {})
    warnings=[]
    tables=snapshot.get("tables") or {}
    ids=snapshot.get("season_ids") or {}
    for key in ("hala_2026_27_h1","hala_2025_26_h1","hala_2025_26_h2","orlik_2026_h1","orlik_2026_h2"):
        season=number(ids.get(key))
        if not season:continue
        for team in tables.get(key,[]):
            tid=number(team.get("team_id"))
            if not tid:continue
            identity=f"{key}:{tid}"
            try:
                old=updated.get(identity) or {}
                if cache_fresh(old,team):
                    continue
                matches,players,complete=detail(fetch(season,tid),tid)
                expected=team.get("matches")
                # Do not replace previous complete snapshot with incomplete listing.
                if expected is not None and len(matches)!=expected:
                    warnings.append(f"{identity}: expected {expected} results, found {len(matches)}")
                    continue
                if sum(m["gf"] for m in matches)!=team["gf"] or sum(m["ga"] for m in matches)!=team["ga"]:
                    warnings.append(f"{identity}: goals do not match table")
                    continue
                updated[identity]={"team_id":str(tid),"season_id":str(season),"division":key,"matches":matches,
                    "standing_signature":team_signature(team),"verified_at":date.today().isoformat(),
                    "players":players if complete else old.get("players",[]),
                    "player_stats_complete":complete,"source":"PLP SportsPress"}
            except Exception as error:warnings.append(f"{identity}: {type(error).__name__}: {error}")
    return {"teams":updated},warnings
def main():
    previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"teams":{}}
    snap=json.loads(STANDINGS.read_text(encoding="utf-8")) if STANDINGS.exists() else {"tables":{}}
    updated,warnings=collect(snap,previous,pages)
    for warning in warnings:print("SCOUT WARNING:",warning,file=sys.stderr)
    result=json.dumps(updated,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=result:
        OUT.write_text(result,encoding="utf-8")
    print("Scouting details:",len(updated["teams"]),"team-season snapshots")
if __name__=="__main__":main()
