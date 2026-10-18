#!/usr/bin/env python3
"""Build transparent preseason scouting from PLP tables and verified historic profiles."""
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=ROOT/"docs"/"assets"/"scouting.json"

def norm(value):
    value=unicodedata.normalize("NFD",str(value or "").lower())
    return re.sub(r"[^a-z0-9]+"," ","".join(x for x in value if unicodedata.category(x)!="Mn")).strip()

def match_row(rows,name):
    return next((r for r in rows if norm(r["name"])==norm(name)),None)

def metric(row,field):
    return round(row[field]/row["matches"],3) if row and row.get("matches") and row.get(field) is not None else None

def regularize(value, tier):
    return max(0,min(100,value * (0.83 if tier==2 else 1)))

def score(hall,orlik,old=None):
    parts=[]
    for row,weight in ((hall,.5),(orlik,.3),(old,.2)):
        if not row or not row.get("matches"): continue
        ppg=metric(row,"points")/3
        gd=metric(row,"gf")-metric(row,"ga")
        attack=metric(row,"gf")
        defense=metric(row,"ga")
        value=100*(.55*ppg+.2*max(0,min(1,(gd+2)/5))+.15*max(0,min(1,attack/5))+.1*max(0,min(1,1-defense/5)))
        parts.append((regularize(value,row.get("tier",1)),weight))
    if not parts: return None
    return round(sum(v*w for v,w in parts)/sum(w for _,w in parts),1)

def benchmark(row):
    if not row: return []
    notes=[]
    if metric(row,"gf")>=3.5:notes.append("Wysoka średnia bramek na mecz — ograniczyć straty w fazie przejścia i sprawdzić na wideo, skąd powstają okazje.")
    if metric(row,"ga")>=2.8:notes.append("Dużo straconych bramek — szukać możliwości ataku, ale dopiero nagrania pokażą, które sektory boiska są słabo zabezpieczone.")
    if metric(row,"ga")<=1.8:notes.append("Niska średnia straconych bramek — przygotować cierpliwe ataki i kilka wariantów rozegrania.")
    if row["wins"]>=row["matches"]*.7:notes.append("Wysoki odsetek zwycięstw — unikać niepotrzebnej wymiany akcji bez zabezpieczenia obrony.")
    return notes or ["Statystyki nie wskazują jednoznacznej charakterystyki taktycznej; przed meczem zweryfikować nagrania i aktualny skład."]

def main():
    seed=json.loads((DATA/"scouting_2026_27_seed.json").read_text(encoding="utf-8"))
    historical=json.loads((DATA/"orlik_2026_opponents.json").read_text(encoding="utf-8"))
    portal=json.loads((ROOT/"docs"/"assets"/"data.json").read_text(encoding="utf-8"))
    hall=seed["tables"]["hala_2025_26_h1"]
    orlik=seed["tables"]["orlik_2026_h1"]
    lower=seed["tables"]["orlik_2026_h2"]
    updates_path=DATA/"scouting_updates.json"
    updates=json.loads(updates_path.read_text(encoding="utf-8")) if updates_path.exists() else {"tables":{}}
    verified=updates.get("tables") or {}
    hall=verified.get("hala_2025_26_h1") or hall
    orlik=verified.get("orlik_2026_h1") or orlik
    lower=verified.get("orlik_2026_h2") or lower
    old={norm(t["team_name"]):t for t in historical["opponents"]}
    # Three bottom teams are excluded by the user's promotion/relegation assumption;
    # a future official participant list overrides these projections.
    dropped={norm(r["name"]) for r in orlik[-3:]}
    candidates=[r["name"] for r in orlik if norm(r["name"]) not in dropped]
    candidates += [r["name"] for r in lower[:3] if norm(r["name"])!=norm("Bosch Service Tech-Car")]
    # If a verified current Hala I table is found, it becomes authoritative.
    current_hall=verified.get("hala_2026_27_h1")
    if current_hall:
        candidates=[r["name"] for r in current_hall if norm(r["name"])!=norm("Bosch Service Tech-Car")]
    candidates=list(dict((norm(name),name) for name in candidates).values())
    details_path=DATA/"scouting_details.json"
    details=json.loads(details_path.read_text(encoding="utf-8")) if details_path.exists() else {"teams":{}}
    teams=[]
    for name in candidates:
        indoor=match_row(hall,name)
        outdoor=match_row(orlik,name) or match_row(lower,name)
        older=(old.get(norm(name)) or {}).get("hall")
        old_data=({"name":name, "tier":2, "matches":older.get("matches"),"gf":older.get("gf"),"ga":older.get("ga"),"points":older.get("points")} if older else None)
        # Never use duplicated same-season hall rows as "older" history.
        rating=score(indoor,outdoor,None)
        risk_basis=indoor or outdoor
        unique={norm(x):x for x in (candidates)}
        profile=old.get(norm(name)) or {}
        stars=profile.get("top_players") or []
        h2h=[m for m in portal["matches"] if norm(m["opponent"])==norm(name)]
        w=sum(m["gf"]>m["ga"] for m in h2h);d=sum(m["gf"]==m["ga"] for m in h2h)
        coverage=(.5 if indoor else 0)+(.3 if outdoor else 0)
        confidence="średnia" if coverage>=.8 else "niska"
        threats=benchmark(risk_basis)
        team_id=next((str(r.get("team_id")) for r in (hall+orlik+lower) if norm(r["name"])==norm(name) and r.get("team_id")),None)
        detailed=[v for v in details.get("teams",{}).values() if team_id and str(v["team_id"])==team_id]
        preferred=next((v for v in detailed if v["division"]=="hala_2026_27_h1"),None) or next((v for v in detailed if v["division"]=="hala_2025_26_h1"),None) or (detailed[0] if detailed else None)
        team_players=preferred.get("players") if preferred and preferred.get("player_stats_complete") else None
        player_rows=[{"name":f"Zawodnik #{p['id']}","id":p["id"],"apps":p["apps"],"goals":p["goals"],"assists":p["assists"],"source_season":preferred["division"]} for p in sorted(team_players,key=lambda p:-(p["goals"]+p["assists"]))] if team_players else []
        teams.append({
            "id":norm(name).replace(" ","-"),"name":name,
            "status":"confirmed_from_table" if current_hall else "candidate", "division":"verified_1_hala_2026_27" if current_hall else "projected_1_hala_2026_27",
            "origin":"promoted_II" if match_row(lower,name) else "retained_I",
            "hall":indoor,"orlik":outdoor,"historic_hall":old_data,
            "strength":rating,"data_coverage":round(coverage,2),"confidence":confidence,
            "players":player_rows or [{"name":p["name"],"id":p.get("player_id"),"apps":p.get("apps"),"goals":p.get("goals"),"assists":p.get("assists"),"source_season":"Hala 2025/26"} for p in stars[:7]],
            "plp_team_id":team_id,
            "season_match_details":preferred.get("matches",[]) if preferred else [],
            "player_stats_verified":bool(team_players),
            "h2h":{"games":len(h2h),"wins":w,"draws":d,"losses":len(h2h)-w-d,"matches":[{"date":m["date"],"gf":m["gf"],"ga":m["ga"],"id":m["id"]} for m in h2h]},
            "statistical_watchouts":threats,
            "plan_a":["W obronie: potwierdzić na wideo role rozgrywających i sposób wyprowadzania piłki; bez potwierdzenia nie przypisywać indywidualnego krycia.","W ataku: sprawdzić na początku meczu reakcję obrony na zmianę strony i ruch trzeciego zawodnika.","Po stracie: zachować asekurację i nie dopuścić do łatwej sytuacji liczebnej."],
            "plan_b":["Gdy pressing nie działa: przejść na bardziej kompaktowe ustawienie i ograniczyć otwartą wymianę.","Przy prowadzeniu: kontrolować tempo i zabezpieczyć środek po stracie.","Przy stracie: zwiększać ryzyko stopniowo, zgodnie z regulaminem i dostępnymi zawodnikami."],
            "scouting_status":"statistical_only",
            "observations":[],
            "videos":[],
            "warning":"Plan gry to hipotezy wyjściowe. Brak potwierdzonej współczesnej analizy wideo; nie przypisano stylu taktycznego na podstawie samych wyników."
        })
    teams.sort(key=lambda row: (-(row["strength"] or 0),row["name"]))
    metadata={**seed["meta"],"forecast_not_confirmed":not bool(current_hall),"snapshot_type":"live_hala_table" if current_hall else "projected_from_orlik"}
    result={"meta":metadata,"teams":teams,"bosch":{"name":"Bosch Service Tech-Car","orlik_2026":seed["tables"]["bos_ch"],"hala_2025_26":{"points":21,"matches":15,"gf":33,"ga":39},"strength_weights":{"hala_2025_26":.5,"orlik_2026":.3,"older_hall":.2},"note":"Dane Boscha i oceny historyczne; bieżące role zawodników wymagają potwierdzenia."},"editorial":seed["editorial"],"videos":seed["videos"],"reviews":seed["match_reviews"],"rules":{"weights":"50/30/20 reweighted among available seasons; do not replace missing data with zero","new_season_weight":"min(0.65, matches / (matches + 8))","tactical_evidence":"A timestamped source is required for any assertion about playing style"}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=rendered:OUT.write_text(rendered,encoding="utf-8")
    print("Scouting built:",len(teams),"candidates")
if __name__=="__main__":main()
