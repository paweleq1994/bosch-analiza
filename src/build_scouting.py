#!/usr/bin/env python3
"""Build transparent preseason scouting from PLP tables and verified historic profiles."""
import json
import re
import unicodedata
from pathlib import Path

from scouting_strength import team_strength, evidence as score_evidence

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

def score(hall, orlik, old=None):
    return team_strength(hall, orlik)


def head_to_head(matches, team_name, team_id):
    """Keep renamed opponents together without merging clubs that share a name."""
    name_ids = {}
    for match in matches:
        if match.get("opponent_id") is not None:
            name_ids.setdefault(norm(match["opponent"]), set()).add(str(match["opponent_id"]))
    known_ids = name_ids.get(norm(team_name), set())
    identifier = str(team_id) if team_id is not None else next(iter(known_ids)) if len(known_ids) == 1 else None
    aliases = {norm(team_name)} | {
        norm(match["opponent"]) for match in matches
        if identifier is not None and str(match.get("opponent_id")) == identifier
    }
    selected = [match for match in matches if (
        str(match["opponent_id"]) == identifier if match.get("opponent_id") is not None
        else norm(match["opponent"]) in aliases
        and name_ids.get(norm(match["opponent"]), set()).issubset({identifier})
    )]
    return sorted(selected, key=lambda match: (match["date"], str(match["id"])), reverse=True)


def historical_players(team_name, team_id, old_profile, details_rows, promotion_rows, profile_map, overrides, refreshed):
    candidates = []
    seasons = {
        "Orlik 2026": 2026.6,
        "Hala 2025/26": 2026.2,
        "Hala 2025/2026": 2026.2,
        "Orlik 2025": 2025.6,
        "Hala 2024/2025": 2025.2,
        "Orlik 2024": 2024.6,
        "Orlik 2023": 2023.6,
    }

    def add(row, fallback_season, provenance):
        name = str(row.get("name") or "").strip()
        player_id = str(row.get("id") or row.get("player_id") or "")
        profile = profile_map.get(player_id) or {}

        if not name or name.startswith("Zawodnik #"):
            name = str(profile.get("resolved_name") or "").strip()

        if not name or name.startswith("Zawodnik #"):
            return

        goals = row.get("goals")
        assists = row.get("assists")
        season = str(row.get("source_season") or row.get("season") or fallback_season)
        if not isinstance(goals, int) or not isinstance(assists, int):
            return

        candidates.append({
            "id": player_id if player_id.isdigit() else None,
            "name": name,
            "apps": row.get("apps"),
            "goals": goals,
            "assists": assists,
            "motm": row.get("motm") if row.get("motm") is not None else row.get("mvp"),
            "source_season": season,
            "source_label": row.get("source_label") or provenance,
            "source_url": row.get("source_url") or row.get("profile_url") or profile.get("profile_url") or "",
            "profile_url": row.get("profile_url") or profile.get("profile_url") or (
                row.get("source_url") if "/zawodnik/" in str(row.get("source_url")) else ""),
            "season_rank": seasons.get(season, 2020.0),
        })

    for row in refreshed.get(str(team_id), []):
        add(row, "Orlik 2026", "Oficjalne statystyki SportsPress")

    for row in overrides.get(team_name, []):
        add(row, "Orlik 2026", "Oficjalny profil PLP")

    for snapshot in details_rows:
        if not snapshot.get("player_stats_complete"):
            continue

        division = snapshot.get("division")
        season = {
            "orlik_2026_h1": "Orlik 2026",
            "orlik_2026_h2": "Orlik 2026",
            "hala_2025_26_h1": "Hala 2025/26",
            "hala_2025_26_h2": "Hala 2025/26",
        }.get(division, division)

        for row in snapshot.get("players") or []:
            add(row, season, "PLP — oficjalne protokoły")

    for row in promotion_rows:
        if str(row.get("team_id")) == str(team_id):
            add(row, row.get("season"), "Archiwum PLP — poprzednie sezony")

    for row in old_profile.get("top_players") or []:
        add(row, "Hala 2025/26", "Historyczny raport PLP")

    for row in old_profile.get("orlik_2025_top_players") or []:
        add(row, "Orlik 2025", "Historyczny raport PLP")

    identified = {}

    for row in candidates:
        key = str(row.get("profile_url") or "").rstrip("/") or str(row.get("id") or "") or norm(row["name"])
        previous = identified.get(key)
        if previous is None or (
            row["season_rank"], row["source_label"] == "Oficjalna tabela indywidualna PLP", row["goals"] + row["assists"]
        ) > (
            previous["season_rank"], previous["source_label"] == "Oficjalna tabela indywidualna PLP", previous["goals"] + previous["assists"]
        ):
            identified[key] = row

    top = sorted(identified.values(), key=lambda row: (
        -row["season_rank"],
        -(row["goals"] + row["assists"]),
        row["name"],
    ))

    return [{key: value for key, value in row.items() if key != "season_rank"} for row in top[:8]]


def all_time_players(team_id, refreshed):
    """Join career totals by official profile URL, using the latest known club."""
    associations = {}
    editions = {"Orlik 2026": 2, "Hala 2025/26": 1, "Hala 2025/2026": 1}
    for identifier, rows in refreshed.items():
        if not str(identifier).isdigit():
            continue
        for row in rows:
            uri = str(row.get("profile_url") or row.get("source_url") or "").rstrip("/") + "/"
            priority = editions.get(row.get("source_season"), 0)
            if priority == 0 or not uri.startswith("https://podlaskaliga.pl/zawodnik/"):
                continue
            previous = associations.get(uri)
            if previous is None or priority > previous["priority"]:
                associations[uri] = {"priority": priority, "clubs": {str(identifier)}, "row": row}
            elif priority == previous["priority"]:
                previous["clubs"].add(str(identifier))

    result = {"scorers": [], "goalkeepers": []}
    for category in result:
        for uri, career in (refreshed.get("_all_time", {}).get(category) or {}).items():
            association = associations.get(uri)
            if association is None or association["clubs"] != {str(team_id)}:
                continue
            club = association["row"]
            result[category].append({**career, "club_season": club["source_season"],
                                     "club_source_url": club["source_url"]})
    # Goals and goalkeeper ratings describe different contributions. Never add
    # them to a season tally or treat a goalkeeper's assists as a scorer threat.
    keeper_urls = {row["profile_url"] for row in result["goalkeepers"]}
    result["scorers"] = sorted(
        [row for row in result["scorers"] if row["goals"] > 0 and row["profile_url"] not in keeper_urls],
        key=lambda row: (-row["goals"], -row["assists"], row["name"]),
    )[:3]
    result["goalkeepers"] = sorted(result["goalkeepers"], key=lambda row: (-row["apps"], -row["rating"], row["name"]))[:2]
    return result


def benchmark(row):
    if not row: return []
    notes=[]
    if metric(row,"gf")>=3.5:notes.append("Wysoka średnia bramek na mecz — ograniczyć straty w fazie przejścia i sprawdzić na wideo, skąd powstają okazje.")
    if metric(row,"ga")>=2.8:notes.append("Dużo straconych bramek — szukać możliwości ataku, ale dopiero nagrania pokażą, które sektory boiska są słabo zabezpieczone.")
    if metric(row,"ga")<=1.8:notes.append("Niska średnia straconych bramek — przygotować cierpliwe ataki i kilka wariantów rozegrania.")
    if row["wins"]>=row["matches"]*.7:notes.append("Wysoki odsetek zwycięstw — unikać niepotrzebnej wymiany akcji bez zabezpieczenia obrony.")
    return notes or ["Statystyki nie wskazują jednoznacznej charakterystyki taktycznej; przed meczem zweryfikować nagrania i aktualny skład."]

def match_strategy(row):
    "Evidence-based tactical hypotheses, not claims of observed play."
    default_defense="Bez piłki: zamknąć środek i zachować asekurację; sposób doskoku skorygować po pierwszych akcjach."
    default_attack="Z piłką: testować zmianę strony i wejścia trzeciego zawodnika, obserwując reakcję rywala."
    if row and metric(row,"gf") is not None and metric(row,"gf")>=3.5:
        default_defense="Wysoka skuteczność ataku rywala: utrzymać asekurację po stracie, ograniczać otwarte wymiany i nie przesądzać sposobu pressingu bez nagrań."
    if row and metric(row,"ga") is not None and metric(row,"ga")>=2.8:
        default_attack="Wysoka średnia traconych bramek: testować szybkie przejścia i ruch bez piłki; dopiero mecz wykaże, czy obrona reaguje z opóźnieniem."
    elif row and metric(row,"ga") is not None and metric(row,"ga")<=1.8:
        default_attack="Rywal ma niski wskaźnik straconych goli: cierpliwe budowanie akcji, zmiana strony i przygotowane stałe fragmenty."
    plan_a=[default_defense,default_attack,"Po stracie: bezpieczna asekuracja za akcją i jasny podział zadań defensywnych."]
    plan_b=["Gdy doskok nie działa: cofnąć pierwszą linię pressingu i ograniczyć odległości między zawodnikami.",
            "Przy prowadzeniu: kontrolować tempo, utrzymać środek i minimalizować niepotrzebne straty.",
            "Przy niekorzystnym wyniku: stopniowo zwiększać ryzyko, dobierając wariant gry do regulaminu i składu."]
    return plan_a,plan_b

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
    bosch_name="Bosch Service Tech-Car"
    bosch_orlik=match_row(lower,bosch_name) or seed["tables"]["bos_ch"]
    bosch_hall=match_row(verified.get("hala_2025_26_h2") or [],bosch_name) or {
        "name":bosch_name,"matches":15,"points":21,"gf":33,"ga":39,"tier":2
    }
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
    player_map=json.loads((DATA/"player_profile_map.json").read_text(encoding="utf-8"))
    promotion_archive=json.loads((DATA/"promoted_teams_analysis.json").read_text(encoding="utf-8"))
    overrides=json.loads((DATA/"scouting_player_overrides.json").read_text(encoding="utf-8"))
    refreshed_path=DATA/"scouting_player_updates.json"
    refreshed=json.loads(refreshed_path.read_text(encoding="utf-8")) if refreshed_path.exists() else {}
    teams=[]
    for name in candidates:
        indoor=match_row(hall,name)
        outdoor=match_row(orlik,name) or match_row(lower,name)
        older=(old.get(norm(name)) or {}).get("hall")
        old_data=({"name":name, "tier":2, "position":older.get("pos"),"matches":older.get("matches"),"gf":older.get("gf"),"ga":older.get("ga"),"points":older.get("points")} if older else None)
        # Never use duplicated same-season hall rows as "older" history.
        rating=score(indoor,outdoor,None)
        risk_basis=indoor or outdoor
        unique={norm(x):x for x in (candidates)}
        profile=old.get(norm(name)) or {}
        stars=profile.get("top_players") or []
        team_id=next((str(r.get("team_id")) for r in (hall+orlik+lower) if norm(r["name"])==norm(name) and r.get("team_id")),None)
        h2h=head_to_head(portal["matches"],name,team_id)
        w=sum(m["gf"]>m["ga"] for m in h2h);d=sum(m["gf"]==m["ga"] for m in h2h)
        coverage=(.5 if indoor else 0)+(.3 if outdoor else 0)
        confidence="średnia" if coverage>=.8 else "niska"
        threats=benchmark(risk_basis)
        plan_a,plan_b=match_strategy(risk_basis)
        video_rows=[]
        video_ids=set()
        for prior_match in h2h:
            for video in prior_match.get("videos") or []:
                video_id=video.get("video_id")
                if not video_id or video_id in video_ids:
                    continue
                video_ids.add(video_id)
                video_rows.append({"id":video_id,"title":video.get("title") or "",
                    "url":video.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                    "date":prior_match["date"],"match_id":prior_match["id"],"source":"Archiwum Boscha, niezweryfikowane taktycznie"})
        detailed=[v for v in details.get("teams",{}).values() if team_id and str(v["team_id"])==team_id]
        preferred=next((v for v in detailed if v["division"]=="hala_2026_27_h1"),None) or next((v for v in detailed if v["division"]=="hala_2025_26_h1"),None) or (detailed[0] if detailed else None)
        player_rows=historical_players(name,team_id,profile,detailed,promotion_archive.get("player_rows",[]),player_map,overrides,refreshed)
        teams.append({
            "id":norm(name).replace(" ","-"),"name":name,
            "status":"confirmed_from_table" if current_hall else "candidate", "division":"verified_1_hala_2026_27" if current_hall else "projected_1_hala_2026_27",
            "origin":"promoted_II" if match_row(lower,name) else "retained_I",
            "hall":indoor,"orlik":outdoor,"historic_hall":old_data,
            "strength":rating,"strength_details":score_evidence(indoor,outdoor),"data_coverage":round(coverage,2),"confidence":confidence,
            "players":player_rows,
            "all_time_players":all_time_players(team_id,refreshed),
            "plp_team_id":team_id,
            "season_match_details":preferred.get("matches",[]) if preferred else [],
            "player_stats_verified":bool(refreshed.get(str(team_id))) or any(snapshot.get("player_stats_complete") for snapshot in detailed),
            "h2h":{"games":len(h2h),"wins":w,"draws":d,"losses":len(h2h)-w-d,
                "gf":sum(m["gf"] for m in h2h),"ga":sum(m["ga"] for m in h2h),
                "matches":[{key:m.get(key) for key in ("date","gf","ga","id","season","opponent","event_link")}
                    | {"video_count":len(m.get("videos") or [])} for m in h2h]},
            "statistical_watchouts":threats,
            "plan_a":plan_a,
            "plan_b":plan_b,
            "scouting_status":"statistical_only",
            "observations":[],
            "videos":video_rows,
            "warning":"Plan gry to hipotezy wyjściowe. Brak potwierdzonej współczesnej analizy wideo; nie przypisano stylu taktycznego na podstawie samych wyników."
        })
    teams.sort(key=lambda row: (-(row["strength"] or 0),row["name"]))
    metadata={**seed["meta"],"forecast_not_confirmed":not bool(current_hall),"snapshot_type":"live_hala_table" if current_hall else "projected_from_orlik"}
    metadata["source_links"] = metadata.get("source_links", []) + [
        {"label": label, "url": url} for label, url in (
            ("All time — gole i asysty", "https://podlaskaliga.pl/lista/alltime-strzelec/"),
            ("All time — bramkarze", "https://podlaskaliga.pl/lista/bramkarze-alltime/"),
        ) if not any(source["url"] == url for source in metadata.get("source_links", []))
    ]
    result={"meta":metadata,"teams":teams,"bosch":{"name":bosch_name,"orlik_2026":bosch_orlik,"hala_2025_26":bosch_hall,"strength":score(bosch_hall,bosch_orlik),"strength_details":score_evidence(bosch_hall,bosch_orlik),"strength_weights":{"hala_2025_26":.35,"orlik_2026":.65,"older_hall":0},"note":"Dane Boscha i oceny historyczne; bieżące role zawodników wymagają potwierdzenia."},"editorial":seed["editorial"],"videos":seed["videos"],"reviews":seed["match_reviews"],"rules":{"weights":"65% Orlik 2026, 35% Hala 2025/26; explicit I/II league calibration, sample adjustment, and neutral prior when missing","new_season_weight":"0.65 verified Orlik 2026","tactical_evidence":"A timestamped source is required for any assertion about playing style"}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=rendered:OUT.write_text(rendered,encoding="utf-8")
    print("Scouting built:",len(teams),"candidates")
if __name__=="__main__":main()
