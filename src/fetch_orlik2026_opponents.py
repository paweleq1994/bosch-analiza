from __future__ import annotations

from collections import defaultdict
from html import unescape
from pathlib import Path
import json
import re
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "orlik_2026_opponents.json"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
USER_AGENT = "Mozilla/5.0"
HALL_SEASON_ID = 146
HALL_TABLE_ID = 12388
ORLIK_2025_SEASON_ID = 144
ORLIK_2025_TABLE_ID = 11758
BOSCH_TEAM_ID = 6951
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = TAG_RE.sub("", text).replace("\xa0", " ")
    return " ".join(text.split()).strip()


def rendered_title(value: object) -> str:
    if isinstance(value, dict):
        return clean_text(value.get("rendered") or value.get("raw") or "")
    return clean_text(value)


def extract_href(value: object) -> str:
    match = re.search(r'href="([^"]+)"', str(value or ""))
    return match.group(1).rstrip("/") if match else ""


def norm(value: object) -> str:
    return clean_text(value).lower()


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)


def parse_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return default


def load_table(table_id: int) -> dict:
    data = fetch_json(f"{BASE}/tables/{table_id}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Table {table_id} did not return a JSON object")
    return data


def table_rows(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for team_id, row in (payload.get("data") or {}).items():
        if not str(team_id).isdigit() or not isinstance(row, dict):
            continue
        pos = parse_int(row.get("pos"), -1)
        if pos <= 0:
            continue
        rows.append(
            {
                "team_id": int(team_id),
                "pos": pos,
                "name": clean_text(row.get("name")),
                "matches": parse_int(row.get("m")),
                "wins": parse_int(row.get("w")),
                "draws": parse_int(row.get("r")),
                "losses": parse_int(row.get("p")),
                "gf": parse_int(row.get("g")),
                "ga": parse_int(row.get("s")),
                "gd": parse_int(row.get("rb")),
                "points": parse_int(row.get("pkt")),
            }
        )
    return sorted(rows, key=lambda row: row["pos"])


def team_payload(team_id: int) -> dict:
    data = fetch_json(f"{BASE}/teams/{team_id}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Team {team_id} did not return a JSON object")
    return data


def event_payloads_for_season() -> list[dict]:
    rows: list[dict] = []
    page = 1
    while page <= 5:
        data = fetch_json(f"{BASE}/events?seasons={HALL_SEASON_ID}&per_page=100&page={page}")
        if not isinstance(data, list) or not data:
            break
        rows.extend(data)
        if len(data) < 100:
            break
        page += 1
    return rows


def season_player_payloads(season_id: int) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while page <= 12:
        data = fetch_json(f"{BASE}/players?seasons={season_id}&per_page=50&page={page}")
        if not isinstance(data, list) or not data:
            break
        rows.extend(data)
        if len(data) < 50:
            break
        page += 1
    return rows


def build_player_rows(players: list[dict], team_links: dict[int, str], season_id: int) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    link_to_team_id = {link.rstrip("/"): team_id for team_id, link in team_links.items()}
    for payload in players:
        player_name = rendered_title(payload.get("title"))
        for block in (payload.get("statistics") or {}).values():
            if not isinstance(block, dict) or str(season_id) not in block:
                continue
            row = block[str(season_id)]
            team_link = extract_href(row.get("team"))
            team_id = link_to_team_id.get(team_link)
            if not team_id:
                continue
            grouped[team_id].append(
                {
                    "player_id": payload.get("id"),
                    "name": player_name,
                    "profile_url": clean_text(payload.get("link")),
                    "apps": parse_int(row.get("appearances")),
                    "goals": parse_int(row.get("goals") or row.get("gole")),
                    "assists": parse_int(row.get("assists") or row.get("asysty")),
                    "points": parse_int(row.get("punktacjakanadyjska") or row.get("points")),
                    "mvp": parse_int(row.get("pikarzmeczu")),
                    "top": parse_int(row.get("top")),
                    "yellow": parse_int(row.get("yellowcards")),
                    "red": parse_int(row.get("redcards")),
                    "gk_rating_total": parse_float(row.get("ocenabramkarza")),
                }
            )
            break
    for team_id, rows in grouped.items():
        unique_rows = {(row["player_id"], row["name"]): row for row in rows}
        grouped[team_id] = sorted(
            unique_rows.values(),
            key=lambda row: (row["points"], row["goals"], row["assists"], row["apps"]),
            reverse=True,
        )
    return grouped


def build_event_rows(events: list[dict], valid_team_ids: set[int]) -> list[dict]:
    rows: list[dict] = []
    for payload in events:
        teams = [int(team_id) for team_id in (payload.get("teams") or []) if str(team_id).isdigit()]
        if len(teams) != 2 or not set(teams).issubset(valid_team_ids):
            continue
        title = rendered_title(payload.get("title"))
        results = payload.get("results") or {}
        team_a, team_b = teams
        row_a = results.get(str(team_a)) or results.get(team_a)
        row_b = results.get(str(team_b)) or results.get(team_b)
        if not isinstance(row_a, dict) or not isinstance(row_b, dict):
            continue
        rows.append(
            {
                "event_id": payload.get("id"),
                "date": payload.get("date"),
                "title": title,
                "teams": teams,
                "link": clean_text(payload.get("link")),
                "rows": {
                    team_a: {
                        "goals": parse_int(row_a.get("goals")),
                        "firsthalf": parse_int(row_a.get("firsthalf")),
                        "secondhalf": parse_int(row_a.get("secondhalf")),
                    },
                    team_b: {
                        "goals": parse_int(row_b.get("goals")),
                        "firsthalf": parse_int(row_b.get("firsthalf")),
                        "secondhalf": parse_int(row_b.get("secondhalf")),
                    },
                },
            }
        )
    return sorted(rows, key=lambda row: row["date"])


def row_for_team(event_row: dict, team_id: int) -> dict:
    opponent_id = event_row["teams"][0] if event_row["teams"][1] == team_id else event_row["teams"][1]
    own = event_row["rows"][team_id]
    opp = event_row["rows"][opponent_id]
    points = 3 if own["goals"] > opp["goals"] else 1 if own["goals"] == opp["goals"] else 0
    margin = own["goals"] - opp["goals"]
    return {
        "event_id": event_row["event_id"],
        "date": event_row["date"],
        "title": event_row["title"],
        "link": event_row["link"],
        "team_id": team_id,
        "opponent_id": opponent_id,
        "gf": own["goals"],
        "ga": opp["goals"],
        "fhf": own["firsthalf"],
        "fha": opp["firsthalf"],
        "shf": own["secondhalf"],
        "sha": opp["secondhalf"],
        "points": points,
        "margin": margin,
    }


def form_string(match_rows: list[dict]) -> str:
    if not match_rows:
        return "-"
    symbols = []
    for row in sorted(match_rows, key=lambda item: item["date"], reverse=True)[:5]:
        symbols.append("W" if row["points"] == 3 else "R" if row["points"] == 1 else "P")
    return " ".join(symbols)


def rank_map(rows: list[dict], field: str, reverse: bool) -> dict[int, int]:
    ordered = sorted(rows, key=lambda row: row[field], reverse=reverse)
    return {row["team_id"]: index + 1 for index, row in enumerate(ordered)}


def share(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def pretty_ppg(points: int, matches: int) -> float:
    return round(points / matches, 2) if matches else 0.0


def threat_level(score: float, hall_pos: int) -> str:
    if hall_pos >= 15 or score <= 2.4:
        return "mecz obowiązkowy"
    if score >= 5.3:
        return "wysokie"
    if score >= 3.8:
        return "średnie+"
    return "średnie"


def build_strengths(ctx: dict) -> list[str]:
    rows: list[str] = []
    if ctx["hall"]["attack_rank"] <= 4:
        rows.append(f"atak z czołówki hali: {ctx['hall']['gf']} goli i {ctx['hall']['attack_rank']}. wynik strzelecki ligi")
    if ctx["orlik_2025"]:
        rows.append(
            f"na Orliku 2025 byli {ctx['orlik_2025']['pos']}. z {ctx['orlik_2025']['points']} pkt, więc większa przestrzeń im nie przeszkadza"
            if ctx["orlik_2025"]["pos"] <= 6
            else f"na Orliku 2025 nie odjechali czołówce, ale już ten format znają ({ctx['orlik_2025']['pos']}. miejsce)"
        )
    if ctx["leaders"]:
        l1 = ctx["leaders"][0]
        rows.append(f"lider punktowy {l1['name']} daje {l1['points']} G+A i jest pierwszym punktem odcięcia")
    if ctx["recent_ppg"] >= 1.8:
        rows.append(f"dobra końcówka hali: {ctx['recent_form']} i {ctx['recent_ppg']:.2f} pkt/mecz w ostatnich 5 spotkaniach")
    if ctx["hall"]["defense_rank"] <= 4:
        rows.append(f"obrona z górnej ćwiartki ligi: tylko {ctx['hall']['ga']} straconych goli")
    return rows[:3]


def build_weaknesses(ctx: dict) -> list[str]:
    rows: list[str] = []
    if ctx["hall"]["ga"] >= 45:
        rows.append(f"dużo tracą: {ctx['hall']['ga']} goli na hali i {ctx['hall']['hall_gapg']:.2f} straconego na mecz")
    if ctx["secondhalf_ga"] > ctx["firsthalf_ga"]:
        rows.append("po przerwie łatwiej ich rozciągnąć i docisnąć, bo więcej tracą w drugiej połowie niż przed przerwą")
    if ctx["top1_goal_share"] >= 30:
        rows.append(f"produkcja jest dość zależna od jednego nazwiska: top1 daje {ctx['top1_goal_share']}% goli")
    if not ctx["orlik_2025"]:
        rows.append("na tle Orlika 2026 to bardziej niewiadoma niż sprawdzony zespół większej przestrzeni")
    elif ctx["orlik_2025"]["pos"] >= 11:
        rows.append(f"na ostatnim orliku nie wyglądali stabilnie: {ctx['orlik_2025']['pos']}. miejsce i {ctx['orlik_2025']['gf']}:{ctx['orlik_2025']['ga']}")
    if ctx["recent_ppg"] <= 1.0:
        rows.append(f"słaba końcówka hali: {ctx['recent_form']} i tylko {ctx['recent_ppg']:.2f} pkt/mecz w ostatnich 5")
    return rows[:3]


def build_plan(ctx: dict) -> list[str]:
    leader = ctx["leaders"][0]["name"] if ctx["leaders"] else "lidera rywala"
    rows: list[str] = []
    if ctx["hall"]["ga"] >= 45 or ctx["hall"]["pos"] >= 11:
        rows.append("wejść wysoko w mecz, narzucić tempo i szerokość, bo przy presji ten blok szybko się rozciąga")
    else:
        rows.append("nie otwierać meczu za wcześnie; najpierw kontrola środka i cierpliwe przenoszenie piłki, dopiero potem przyspieszenie")
    if ctx["top1_goal_share"] >= 30:
        rows.append(f"pierwszy cel defensywny: odciąć {leader} od podań do nogi i od drugiej piłki po odbiorze")
    else:
        rows.append("bardziej pilnować struktury niż jednego nazwiska, bo zagrożenie rozkłada się na kilka pozycji")
    if ctx["hall"]["secondhalf_edge"] < 0:
        rows.append("trzymać zmianami świeżość na drugą połowę; przy szerszej kadrze Bosch może ich zmęczyć po przerwie")
    else:
        rows.append("uważać na wejście w mecz i pierwsze 10 minut po przerwie, bo właśnie wtedy lubią budować serię")
    return rows[:3]


def build_opportunities(ctx: dict) -> list[str]:
    rows: list[str] = []
    if ctx["hall"]["ga"] >= 45:
        rows.append("szukać strzału po drugim kontakcie i szybkiego wejścia po odbiorze, bo ta obrona źle znosi kolejną falę ataku")
    if ctx["orlik_2025"] and ctx["orlik_2025"]["ga"] >= 50:
        rows.append("na większej przestrzeni zostawiali sporo miejsca za linią piłki; warto odpalać skrzydła i diagonalne podania")
    if ctx["leaders"] and ctx["leaders"][0]["yellow"] >= 2:
        rows.append(f"warto wciągać {ctx['leaders'][0]['name']} w pojedynki i kontakt, bo bywa łapany na faulach")
    if ctx["hall"]["pos"] >= 13:
        rows.append("to mecz, w którym Bosch powinien grać o pełną pulę od pierwszej minuty, a nie dopiero reagować po stracie")
    return rows[:3]


def build_watchouts(ctx: dict) -> list[str]:
    rows: list[str] = []
    if ctx["leaders"]:
        l1 = ctx["leaders"][0]
        rows.append(f"uważać na {l1['name']}: {l1['goals']} goli i {l1['assists']} asyst w hali")
    if len(ctx["leaders"]) >= 2:
        l2 = ctx["leaders"][1]
        rows.append(f"drugi punkt alarmowy to {l2['name']}, który daje {l2['points']} G+A i może wejść z drugiej fali")
    if ctx["hall"]["gf"] >= 50:
        rows.append("nie wdawać się bez potrzeby w mecz na wymianę, bo ten zespół umie podnieść tempo i nabić wynik w krótkim czasie")
    elif ctx["hall"]["close_ppg"] >= 1.8:
        rows.append("to rywal, który potrafi wycisnąć dużo z wyrównanych spotkań, więc końcówka musi być pod kontrolą")
    return rows[:3]


def manual_override(team_id: int, ctx: dict) -> dict[str, object]:
    leader_names = [leader["name"] for leader in ctx["leaders"][:3]]
    first = leader_names[0] if leader_names else "lider"
    second = leader_names[1] if len(leader_names) > 1 else "drugi motor gry"
    third = leader_names[2] if len(leader_names) > 2 else "kolejny punkt podania"
    data: dict[int, dict[str, object]] = {
        1566: {
            "summary": f"{ctx['name']} to rywal z górnej strefy hali, ale na Orliku 2025 nie był już tak dominujący. Kluczem jest odcięcie duetu {first} + {second} i niedopuszczenie do szybkiej wymiany ciosów w środku.",
            "plan": [
                "w tym meczu powrót Mateusza Jurkowicza byłby ważny, bo Bosch potrzebuje więcej spokoju w środku i mocniejszej asekuracji po stracie",
                f"pierwsza zasada: nie dać {first} ani {second} grać po odbiorze twarzą do bramki",
                "w ataku szukać przeciągania akcji na bok i wchodzenia trzecim zawodnikiem, bo to zespół bardziej do rozrywania niż do przełamywania siłą",
            ],
        },
        4382: {
            "summary": f"{ctx['name']} ma bardzo mocnego lidera w osobie {first}, a na Orliku 2025 trzymał środek tabeli. To mecz, w którym Bosch powinien jednocześnie szanować jakość finalizacji rywala i testować jego obronę tempem oraz szerokością.",
        },
        10770: {
            "summary": f"{ctx['name']} to jeden z najtrudniejszych rywali przyszłego Orlika: top3 hali i top3 ostatniego orlika, a trójka {first}, {second}, {third} napędza grę praktycznie cały mecz.",
            "plan": [
                "to nie jest mecz do biegania bez asekuracji; rest defense Bosch musi być ustawiona od pierwszej akcji",
                f"najpierw wygasić {first} jako podającego, a dopiero potem domykać pole karne na strzał {second}",
                "warto rotować zmianami mocniej niż zwykle, bo na większym boisku ich jakość rośnie, gdy rywal fizycznie siada",
            ],
        },
        10769: {
            "summary": f"{ctx['name']} strzela sporo, ale daje też dużo miejsca w obronie. To rywal, którego trzeba atakować odważnie, bo na Orliku 2025 był niżej niż sugeruje obecna hala.",
        },
        12342: {
            "summary": f"{ctx['name']} wygrało z Bosch na hali, więc nie wolno tego meczu traktować jak starcia ze środkiem tabeli bez zębów. Jeśli Bosch dobrze rozciągnie blok rywala, pole do okazji powinno się jednak otworzyć.",
        },
        8195: {
            "summary": f"{ctx['name']} to niewygodny rywal na oba formaty: dobre miejsce na hali, dobre miejsce na Orliku 2025 i sporo jakości rozłożonej na kilka nazwisk.",
        },
        8196: {
            "summary": f"{ctx['name']} daje otwarte mecze i dużo goli po obu stronach. Bosch powinien iść tu po kontrolowany chaos: mocny atak pozycyjny, ale bez rozwalania własnej asekuracji.",
        },
        8193: {
            "summary": f"{ctx['name']} na hali było niżej, ale na Orliku 2025 wypadło wyraźnie lepiej. To jeden z rywali, których ranking halowy może lekko zaniżać w perspektywie lata.",
        },
        10768: {
            "summary": f"{ctx['name']} ma bardzo miękką obronę, ale też dwóch ludzi zdolnych zamienić chaos w serię goli. Bosch powinien tu grać o pełną pulę, ale bez lekceważenia momentów przejścia.",
        },
        6984: {
            "summary": f"{ctx['name']} rzadko wygląda imponująco tabelowo, ale z Bosch często gra niewygodne, ciasne mecze. To spotkanie bardziej na cierpliwość i kontrolę niż na szarpanie od pierwszej minuty.",
        },
        11756: {
            "summary": f"{ctx['name']} ma bardzo wyraźnego lidera punktowego w osobie {first}. Jeśli Bosch odetnie jego wpływ na mecz, reszta ataku jest już dużo łatwiejsza do przytrzymania.",
        },
        4643: {
            "summary": f"{ctx['name']} skończyło halę na dole, ale na Orliku 2025 było lepsze niż dziś. To nie powinien być mecz na remisowanie, ale też nie można dać mu nabrać pewności po łatwej kontrze.",
        },
        11754: {
            "summary": f"{ctx['name']} to ostatni zespół hali i jeden z meczów obowiązkowych dla Bosch, ale ma kilku ludzi umiejących ukłuć po otwartej przestrzeni. Priorytetem jest szybkie objęcie kontroli i zabicie wiary rywala w sens czekania na chaos.",
        },
    }
    return data.get(team_id, {})


def build_payload() -> dict:
    hall_table = load_table(HALL_TABLE_ID)
    orlik_2025_table = load_table(ORLIK_2025_TABLE_ID)
    hall_rows = table_rows(hall_table)
    hall_team_ids = {row["team_id"] for row in hall_rows}
    hall_name_map = {row["team_id"]: row["name"] for row in hall_rows}
    promoted_rows = [row for row in hall_rows if row["pos"] <= 2]
    opponent_rows = [row for row in hall_rows if row["team_id"] != BOSCH_TEAM_ID and row["pos"] > 2]
    attack_rank = rank_map(hall_rows, "gf", True)
    defense_rank = rank_map(hall_rows, "ga", False)

    team_meta = {}
    team_links = {}
    for row in opponent_rows + [next(row for row in hall_rows if row["team_id"] == BOSCH_TEAM_ID)]:
        payload = team_payload(row["team_id"])
        team_meta[row["team_id"]] = {
            "name": rendered_title(payload.get("title")),
            "display_name": hall_name_map[row["team_id"]],
            "link": clean_text(payload.get("link")),
        }
        team_links[row["team_id"]] = clean_text(payload.get("link"))

    events = build_event_rows(event_payloads_for_season(), hall_team_ids)
    hall_player_rows = build_player_rows(season_player_payloads(HALL_SEASON_ID), team_links, HALL_SEASON_ID)
    orlik_player_rows = build_player_rows(season_player_payloads(ORLIK_2025_SEASON_ID), team_links, ORLIK_2025_SEASON_ID)

    orlik_rows = {row["team_id"]: row for row in table_rows(orlik_2025_table)}
    bosch_events = [row_for_team(event_row, BOSCH_TEAM_ID) for event_row in events if BOSCH_TEAM_ID in event_row["teams"]]
    bosch_by_opponent = {row["opponent_id"]: row for row in bosch_events}

    opponents: list[dict] = []
    for row in opponent_rows:
        team_id = row["team_id"]
        team_events = [row_for_team(event_row, team_id) for event_row in events if team_id in event_row["teams"]]
        firsthalf_gf = sum(event["fhf"] for event in team_events)
        firsthalf_ga = sum(event["fha"] for event in team_events)
        secondhalf_gf = sum(event["shf"] for event in team_events)
        secondhalf_ga = sum(event["sha"] for event in team_events)
        close_rows = [event for event in team_events if abs(event["margin"]) <= 1]
        close_ppg = round(sum(event["points"] for event in close_rows) / len(close_rows), 2) if close_rows else 0.0
        recent = sorted(team_events, key=lambda event: event["date"], reverse=True)[:5]
        recent_ppg = round(sum(event["points"] for event in recent) / len(recent), 2) if recent else 0.0
        leaders = hall_player_rows.get(team_id, [])[:5]
        orlik_leaders = orlik_player_rows.get(team_id, [])[:5]
        top1_goal_share = share(leaders[0]["goals"], row["gf"]) if leaders else 0.0
        top3_goal_share = share(sum(player["goals"] for player in leaders[:3]), row["gf"]) if leaders else 0.0
        hall_ppg = pretty_ppg(row["points"], row["matches"])
        hall_gapg = round(row["ga"] / row["matches"], 2)
        hall_gfpg = round(row["gf"] / row["matches"], 2)
        orlik_row = orlik_rows.get(team_id)
        orlik_ppg = pretty_ppg(orlik_row["points"], orlik_row["matches"]) if orlik_row else None
        score = (
            (17 - row["pos"]) * 0.24
            + hall_ppg
            + (2.2 - min(hall_gapg, 4.5)) * 0.55
            + (min(hall_gfpg, 4.6)) * 0.18
            + (orlik_ppg or 1.1) * 0.4
            + recent_ppg * 0.28
            + (0.35 if bosch_by_opponent.get(team_id, {}).get("points", 3) < 3 else 0.0)
        )
        ctx = {
            "team_id": team_id,
            "name": hall_name_map[team_id],
            "leaders": leaders,
            "hall": {
                **row,
                "attack_rank": attack_rank[team_id],
                "defense_rank": defense_rank[team_id],
                "hall_ppg": hall_ppg,
                "hall_gapg": hall_gapg,
                "hall_gfpg": hall_gfpg,
                "secondhalf_edge": secondhalf_gf - secondhalf_ga,
                "close_ppg": close_ppg,
            },
            "orlik_2025": {
                **orlik_row,
                "ppg": orlik_ppg,
            }
            if orlik_row
            else None,
            "top1_goal_share": top1_goal_share,
            "top3_goal_share": top3_goal_share,
            "recent_form": form_string(recent),
            "recent_ppg": recent_ppg,
            "firsthalf_gf": firsthalf_gf,
            "firsthalf_ga": firsthalf_ga,
            "secondhalf_gf": secondhalf_gf,
            "secondhalf_ga": secondhalf_ga,
        }
        override = manual_override(team_id, ctx)
        strengths = build_strengths(ctx)
        weaknesses = build_weaknesses(ctx)
        plan = override.get("plan") or build_plan(ctx)
        opportunities = build_opportunities(ctx)
        watchouts = build_watchouts(ctx)
        opponents.append(
            {
                "team_id": team_id,
                "team_name": hall_name_map[team_id],
                "team_profile_name": team_meta[team_id]["name"],
                "team_link": team_meta[team_id]["link"],
                "hall": {
                    **row,
                    "attack_rank": attack_rank[team_id],
                    "defense_rank": defense_rank[team_id],
                    "ppg": hall_ppg,
                    "gfpg": hall_gfpg,
                    "gapg": hall_gapg,
                    "close_ppg": close_ppg,
                    "recent_form": form_string(recent),
                    "recent_ppg": recent_ppg,
                },
                "orlik_2025": {
                    **orlik_row,
                    "ppg": orlik_ppg,
                }
                if orlik_row
                else None,
                "orlik_2025_top_players": orlik_leaders,
                "top_players": leaders,
                "players_used": len([player for player in hall_player_rows.get(team_id, []) if player["apps"] > 0]),
                "orlik_2025_players_used": len([player for player in orlik_player_rows.get(team_id, []) if player["apps"] > 0]),
                "top1_goal_share": top1_goal_share,
                "top3_goal_share": top3_goal_share,
                "firsthalf_gf": firsthalf_gf,
                "firsthalf_ga": firsthalf_ga,
                "secondhalf_gf": secondhalf_gf,
                "secondhalf_ga": secondhalf_ga,
                "bosch_hall_match": bosch_by_opponent.get(team_id),
                "threat_score": round(score, 2),
                "threat_level": threat_level(score, row["pos"]),
                "scouting": {
                    "summary": override.get("summary")
                    or f"{hall_name_map[team_id]} kończy halę na {row['pos']}. miejscu z bilansem {row['gf']}:{row['ga']}. To profil rywala, którego trzeba czytać przez połączenie obecnej hali, poprzedniego orlika i nazwisk robiących liczby.",
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "bosch_plan": plan,
                    "opportunities": opportunities,
                    "watchouts": watchouts,
                },
            }
        )

    opponents.sort(key=lambda row: (-row["threat_score"], row["hall"]["pos"], row["team_name"]))
    toughest = opponents[0]
    easiest = sorted(opponents, key=lambda row: (row["hall"]["pos"], row["threat_score"]))[-1]
    bottom_two = [row for row in opponents if row["hall"]["pos"] >= 15]
    best_orlik = max([row for row in opponents if row["orlik_2025"]], key=lambda row: row["orlik_2025"]["ppg"], default=None)
    widest_attack = max(opponents, key=lambda row: row["hall"]["gf"])
    softest_defense = max(opponents, key=lambda row: row["hall"]["ga"])

    return {
        "generated_at": "2026-03-25",
        "source": {
            "hall_table_id": HALL_TABLE_ID,
            "hall_table_link": clean_text(hall_table.get("link")),
            "hall_table_title": rendered_title(hall_table.get("title")),
            "hall_season_id": HALL_SEASON_ID,
            "orlik_2025_season_id": ORLIK_2025_SEASON_ID,
            "orlik_2025_table_id": ORLIK_2025_TABLE_ID,
            "orlik_2025_table_link": clean_text(orlik_2025_table.get("link")),
            "orlik_2025_table_title": rendered_title(orlik_2025_table.get("title")),
        },
        "bosch_scenario": {
            "assumptions": [
                "Mateusz Jurkowicz wraca po wakacjach i ma być dostępny od drugiej rundy.",
                "Do kadry dochodzi jeszcze około 3 nowych zawodników na poziomie ligowym.",
                "Analiza zakłada, że Bosch wchodzi w Orlik 2026 z wyraźnie szerszą rotacją niż na końcu hali.",
            ],
            "global_tips": [
                "Przy szerszej kadrze Bosch może mocniej różnicować plan: wysoko i intensywnie na słabszych, bardziej kontrolnie na zespoły z topu przyszłych rywali.",
                "Powrót Jurkowicza powinien pomóc w asekuracji po stracie, czyli dokładnie tam, gdzie Bosch na hali oddawał za dużo łatwych momentów po przejściu.",
                "Nowe profile warto wykorzystać przede wszystkim do podniesienia szerokości i jakości biegu bez piłki, bo wiele przyszłych rywali zostawia sporo miejsca po bokach lub po przerwie.",
                "W meczach obowiązkowych Bosch powinien szybciej zamykać wynik i rotować energią, zamiast trzymać spotkanie długo przy życiu i zapraszać rywala do chaosu.",
            ],
        },
        "excluded_promoted": promoted_rows,
        "bottom_two_watch": [row for row in hall_rows if row["pos"] >= 15],
        "summary": {
            "opponents_count": len(opponents),
            "toughest_team": {"team_id": toughest["team_id"], "team_name": toughest["team_name"]},
            "easiest_team": {"team_id": easiest["team_id"], "team_name": easiest["team_name"]},
            "best_orlik_2025": {"team_id": best_orlik["team_id"], "team_name": best_orlik["team_name"]} if best_orlik else None,
            "widest_attack": {"team_id": widest_attack["team_id"], "team_name": widest_attack["team_name"], "gf": widest_attack["hall"]["gf"]},
            "softest_defense": {"team_id": softest_defense["team_id"], "team_name": softest_defense["team_name"], "ga": softest_defense["hall"]["ga"]},
            "bottom_two": [{"team_id": row["team_id"], "team_name": row["team_name"]} for row in bottom_two],
        },
        "opponents": opponents,
    }


def main() -> Path:
    payload = build_payload()
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUT_PATH


if __name__ == "__main__":
    print(main())
