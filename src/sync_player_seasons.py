#!/usr/bin/env python3
"""Refresh complete per-season Bosch player statistics from public SportsPress.

The API returns statistics grouped by league and season; keep only rows whose
team points to the verified Bosch team, avoid 'Suma' (-1) and column headers (0).
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request,urlopen
import json,re,sys
from player_totals import career_from_profile
from player_identity import match_public_profile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"player_season_updates.json"
PORTAL=ROOT/"docs/assets/data.json"
TEAM_SLUG="bosch-service-tech-car"

def number(value):
    return int(value) if str(value).strip().isdigit() else None

def parse_player(data):
    output={}
    for league,season_rows in (data.get("statistics") or {}).items():
        if not isinstance(season_rows,dict):continue
        for sid,stat in season_rows.items():
            if sid in ("0","-1") or not isinstance(stat,dict):continue
            if TEAM_SLUG not in str(stat.get("team") or ""):continue
            stats={key:number(stat.get(source)) for key,source in (
                ("apps","appearances"),("goals","goals"),("assists","assists"),
                ("motm","pikarzmeczu"),("yellow","yellowcards"),("red","redcards"))}
            if stats["apps"] is None:continue
            if sid in output:
                # Do not silently double-count two entries in different leagues.
                if output[sid] != stats: raise ValueError(f"Conflicting season entry {sid}")
                continue
            output[str(sid)]={**stats,"name":str(stat.get("name") or ""),"origin":"PLP SportsPress"}
    return output

def request(pid):
    url=f"https://podlaskaliga.pl/wp-json/sportspress/v2/players/{pid}"
    with urlopen(Request(url,headers={"User-Agent":"Bosch-Scouting/1.0"}),timeout=12) as r:
        return json.load(r)

def refresh(ids,current,fetch=request):
    merged={str(k):v for k,v in current.items()}
    warnings=[]
    for pid in ids:
        try:
            stats=parse_player(fetch(pid))
            if stats:merged[str(pid)]=stats
        except Exception as error:
            warnings.append(f"{pid}: {type(error).__name__}: {error}")
    return merged,warnings

def refresh_careers(ids, current, fetch=request):
    merged=dict(current)
    warnings=[]
    for pid in ids:
        try:
            record=career_from_profile(fetch(pid), number)
            if record:merged[str(pid)]=record
        except Exception as error:
            warnings.append(f"{pid}: {type(error).__name__}: {error}")
    return merged,warnings

def refresh_both(ids, current_seasons, current_careers, fetch=request, workers=4):
    """Fetch each PLP profile at most once with bounded concurrent requests."""
    seasons = {str(key): value for key, value in current_seasons.items()}
    careers = {str(key): value for key, value in current_careers.items()}
    warnings = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, identifier): str(identifier) for identifier in ids}

        for future in as_completed(futures):
            player_id = futures[future]

            try:
                profile = future.result()
            except Exception as error:
                warnings.append(f"{player_id}: {type(error).__name__}: {error}")
                continue

            try:
                current_stats = parse_player(profile)
                if current_stats:
                    seasons[player_id] = current_stats
            except Exception as error:
                warnings.append(f"{player_id}/seasons: {type(error).__name__}: {error}")

            try:
                career = career_from_profile(profile, number)
                if career:
                    careers[player_id] = career
            except Exception as error:
                warnings.append(f"{player_id}/career: {type(error).__name__}: {error}")

    return seasons, careers, sorted(warnings)


def main():
    old=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    portal=json.loads(PORTAL.read_text(encoding="utf-8"))
    profiles=json.loads((ROOT/"data"/"player_profile_map.json").read_text(encoding="utf-8"))
    recap=json.loads((ROOT/"data"/"orlik_2026_recap.json").read_text(encoding="utf-8"))
    current_ids={
        match[0]
        for row in recap.get("player_leaders",[])
        if (match:=match_public_profile(str(row.get("name") or ""),profiles)) is not None
    }
    goal_evidence=json.loads((ROOT/"data"/"goal_evidence.json").read_text(encoding="utf-8"))
    verified_goal_ids={
        match[0]
        for row in goal_evidence.get("players",[])
        if (match:=match_public_profile(str(row.get("name") or ""),profiles)) is not None
    }
    roster_ids={pid for pid, profile in profiles.items() if profile.get("source")=="verified_official_roster"}
    ids=sorted({str(p["id"]) for p in portal.get("players",[]) if str(p["id"]).isdigit()}|current_ids|verified_goal_ids|roster_ids,key=int)
    careers_file=ROOT/"data"/"player_career_updates.json"
    previous_careers=json.loads(careers_file.read_text(encoding="utf-8")) if careers_file.exists() else {}
    results,careers,warnings=refresh_both(ids,old,previous_careers)
    career_warnings=[]
    career_rendered=json.dumps(careers,ensure_ascii=False,indent=2)+"\n"
    if not careers_file.exists() or careers_file.read_text(encoding="utf-8")!=career_rendered:careers_file.write_text(career_rendered,encoding="utf-8")
    rendered=json.dumps(results,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=rendered:OUT.write_text(rendered,encoding="utf-8")
    for warning in warnings[:8]:print("Player statistics warning:",warning,file=sys.stderr)
    print("PLP player season coverage:",len(results),"players;",sum(len(v) for v in results.values()),"season records;",len(warnings),"warnings;",len(careers),"career profiles;",len(career_warnings),"career warnings")
if __name__=="__main__":main()
