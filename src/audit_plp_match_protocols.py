#!/usr/bin/env python3
"""Inspect every Bosch match source and preserve reproducible goal evidence."""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import json
import re
import time
import unicodedata

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "docs" / "assets" / "data.json"
REPORT_PATH = ROOT / "data" / "match_protocol_audit.json"
BOSCH_TEAM_ID = "6951"
BOSCH_NAME = "Bosch Service Tech-Car"
API_BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
HTTP_TIMEOUT = 18
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BoschHistoricalAudit/1.0; +https://github.com/paweleq1994/bosch-analiza)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}
PERFORMANCE_FIELDS = ("goals", "assists", "samobje", "samoboje", "own_goals")


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", unescape(str(value or "")).lower().replace("ł", "l"))
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")

    return " ".join(re.findall(r"[a-z0-9]+", text))


def integer(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None

    text = str(value or "").strip()

    if not re.fullmatch(r"\d+", text):
        return None

    return int(text)


def get(url: str) -> tuple[str | None, str]:
    if not url.startswith("https://podlaskaliga.pl/"):
        return None, "invalid_official_domain"

    for attempt in range(2):
        try:
            request = Request(url, headers=BROWSER_HEADERS)

            with urlopen(request, timeout=HTTP_TIMEOUT) as response:
                contents = response.read(2_000_000)
                charset = response.headers.get_content_charset() or "utf-8"

            return contents.decode(charset, "replace"), "ok"
        except HTTPError as error:
            if error.code in (403, 404):
                return None, "http_" + str(error.code)

            reason = "http_" + str(error.code)
        except (URLError, TimeoutError, OSError) as error:
            reason = type(error).__name__

        if attempt == 0:
            time.sleep(0.4)

    return None, reason


def rendered(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("rendered")

    return unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()


def player_id_from_anchor(anchor) -> str | None:
    if anchor is None:
        return None

    href = str(anchor.get("href") or "")
    path = urlsplit(href)
    identifiers = parse_qs(path.query)
    player_id = (identifiers.get("p") or [None])[0]

    return str(player_id) if player_id and str(player_id).isdigit() else None


def minutes_from_text(value: object) -> list[str]:
    return re.findall(r"(?<!\d)(\d{1,3}(?:\+\d{1,2})?)\s*['’′]", str(value or ""))


def icon_performance(performance_cell) -> dict:
    goals = 0
    own_goals = 0
    assists = 0
    goal_minutes = []
    unknown_goal_markers = 0

    if performance_cell is None:
        return {
            "goals": 0,
            "own_goals": 0,
            "assists": 0,
            "goal_minutes": [],
            "unreadable_goal_markers": 0,
        }

    for icon in performance_cell.select("i[title]"):
        title = normalize(icon.get("title"))
        following_text = []

        for sibling in icon.next_siblings:
            if getattr(sibling, "name", None) in {"br", "i"}:
                break

            following_text.append(sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling))

        minutes = minutes_from_text(" ".join(following_text))

        if title == "gol":
            goals += len(minutes)
            goal_minutes.extend(minutes)

            if not minutes:
                unknown_goal_markers += 1

        elif title in {"samoboj", "samobojczy", "samobojcza"}:
            own_goals += len(minutes)

            if not minutes:
                unknown_goal_markers += 1

        elif title == "asysta":
            assists += 1

    return {
        "goals": goals,
        "own_goals": own_goals,
        "assists": assists,
        "goal_minutes": goal_minutes,
        "unreadable_goal_markers": unknown_goal_markers,
    }


def interpret_performance(event: dict | None, player_names: dict) -> dict:
    if not isinstance(event, dict):
        return {"available": False, "players": [], "goals": None, "own_goals": None}

    team_performance = (event.get("performance") or {}).get(BOSCH_TEAM_ID)
    opposing_performance = (event.get("performance") or {})
    players = []
    own_goals = 0

    if not isinstance(team_performance, dict):
        return {"available": False, "players": [], "goals": None, "own_goals": None}

    for player_id, stats in team_performance.items():
        if not str(player_id).isdigit() or int(player_id) == 0 or not isinstance(stats, dict):
            continue

        goals = integer(stats.get("goals"))
        assists = integer(stats.get("assists"))
        own_goal = next((integer(stats.get(key)) for key in PERFORMANCE_FIELDS[2:] if integer(stats.get(key)) is not None), None)

        if goals is None and assists is None and own_goal is None:
            continue

        players.append({
            "player_id": str(player_id),
            "name": player_names.get(str(player_id), ""),
            "goals": goals,
            "assists": assists,
            "own_goals": own_goal,
            "raw_fields": sorted(stats),
            "raw_goals": str(stats.get("goals") or ""),
            "raw_assists": str(stats.get("assists") or ""),
            "raw_own_goals": str(stats.get("samobje") or ""),
        })

        if own_goal:
            own_goals += own_goal

    opposing_own_goals = 0

    for other_team_id, other_players in opposing_performance.items():
        if str(other_team_id) == BOSCH_TEAM_ID or not isinstance(other_players, dict):
            continue

        for player_id, stats in other_players.items():
            if not str(player_id).isdigit() or not isinstance(stats, dict):
                continue

            own_goal = next((integer(stats.get(key)) for key in PERFORMANCE_FIELDS[2:] if integer(stats.get(key)) is not None), None)
            opposing_own_goals += own_goal or 0

    known_goals = [player["goals"] for player in players if player["goals"] is not None]

    return {
        "available": True,
        "players": players,
        "goals": sum(known_goals) if known_goals else None,
        "own_goals": own_goals,
        "opponent_own_goals": opposing_own_goals,
    }


def parse_table_performance(table, index: int) -> dict:
    parent = table.find_parent(class_=re.compile(r"sp-template-event-performance"))
    previous_heading = table.find_previous(["h3", "h4", "h5", "caption"])
    heading = rendered(previous_heading.get_text(" ", strip=True)) if previous_heading else ""
    caption = table.find("caption")

    if caption:
        heading = rendered(caption.get_text(" ", strip=True))

    if parent:
        parent_heading = parent.find(["h3", "h4", "h5"])

        if parent_heading:
            heading = rendered(parent_heading.get_text(" ", strip=True))

    column_headers = [normalize(header.get_text(" ", strip=True)) for header in table.select("thead tr:last-child th")]
    goals_index = next((position for position, label in enumerate(column_headers) if label == "gole"), None)
    own_goals_index = next((position for position, label in enumerate(column_headers) if label in ("samoboje", "samoboj")), None)
    player_rows = []

    for row in table.select("tbody tr"):
        if "sp-total-row" in (row.get("class") or []):
            continue

        cells = row.find_all(["td", "th"], recursive=False)
        name_cell = row.select_one(".data-name")

        if name_cell is None:
            name_cell = next((cell for cell in cells if cell.find("a", href=re.compile(r"zawodnik|sp_player|post_type"))), None)

        if name_cell is None:
            continue

        name = name_cell.get_text(" ", strip=True)
        player_link = name_cell.find("a", href=True)
        goals_cell = row.select_one(".data-goals")
        own_goals_cell = row.select_one(".data-samobje, .data-samoboje")
        icons = icon_performance(row.select_one(".sp-performance-icons"))

        if goals_cell is None and goals_index is not None and goals_index < len(cells):
            goals_cell = cells[goals_index]

        if own_goals_cell is None and own_goals_index is not None and own_goals_index < len(cells):
            own_goals_cell = cells[own_goals_index]

        if not name:
            continue

        player_rows.append({
            "name": name,
            "player_id": player_id_from_anchor(player_link),
            "goals": integer(goals_cell.get_text(" ", strip=True)) if goals_cell else icons["goals"],
            "own_goals": integer(own_goals_cell.get_text(" ", strip=True)) if own_goals_cell else icons["own_goals"],
            "assists": icons["assists"],
            "goal_minutes": icons["goal_minutes"],
            "unreadable_goal_markers": icons["unreadable_goal_markers"],
            "profile_url": player_link.get("href") if player_link else None,
            "raw_goals": goals_cell.get_text(" ", strip=True) if goals_cell else "",
            "raw_own_goals": own_goals_cell.get_text(" ", strip=True) if own_goals_cell else "",
        })

    confirmed_goals = [row["goals"] for row in player_rows if row["goals"] is not None]

    return {
        "index": index,
        "heading": heading,
        "is_bosch": normalize(BOSCH_NAME) in normalize(heading),
        "header_fields": column_headers,
        "players": player_rows,
        "goals": sum(confirmed_goals) if confirmed_goals else 0,
        "unreadable_goal_markers": sum(row["unreadable_goal_markers"] for row in player_rows),
    }


def parse_match_html(source: str | None) -> dict:
    if not source:
        return {"available": False, "performance_tables": [], "bosch_goals": None, "own_goals": None}

    soup = BeautifulSoup(source, "html.parser")
    result = {
        "available": True,
        "page_title": rendered(soup.title.get_text(" ", strip=True)) if soup.title else "",
        "performance_tables": [],
        "bosch_goals": None,
        "own_goals": None,
        "statistic_rows": [],
    }

    tables = soup.select(".sp-template-event-performance table")

    if not tables:
        tables = soup.select("table.sp-event-performance")

    for index, table in enumerate(tables):
        parsed = parse_table_performance(table, index)
        result["performance_tables"].append(parsed)

    confirmed_bosch_tables = [
        table for table in result["performance_tables"]
        if table["is_bosch"] and table["goals"] is not None
    ]

    if len(confirmed_bosch_tables) == 1:
        result["bosch_goals"] = confirmed_bosch_tables[0]["goals"]
        result["bosch_players"] = confirmed_bosch_tables[0]["players"]
        result["unreadable_goal_markers"] = confirmed_bosch_tables[0]["unreadable_goal_markers"]

    result["statistic_values"] = {}

    for title in soup.select(".sp-template-event-statistics .sp-statistic-label"):
        name = normalize(title.get_text(" ", strip=True))
        table = title.find_next("table")

        if not table:
            continue

        values = [
            integer(cell.get_text(" ", strip=True))
            for cell in table.select("td.sp-statistic-value")
        ]

        if len(values) == 2:
            result["statistic_values"][name] = values

    first_heading = result["performance_tables"][0]["heading"] if result["performance_tables"] else ""
    bosch_position = 0 if normalize(BOSCH_NAME) in normalize(first_heading) else 1
    all_goals = result["statistic_values"].get("gole", [])
    own_goals = result["statistic_values"].get("samoboje", [])

    if len(all_goals) == 2:
        result["bosch_on_field_goals"] = all_goals[bosch_position]

    if len(own_goals) == 2:
        result["own_goals_by_bosch"] = own_goals[bosch_position]
        result["own_goals_by_opponent"] = own_goals[1 - bosch_position]


    return result


def fetch_season(season: dict) -> dict:
    original_id = "148" if str(season["id"]) == "orlik-2026" else str(season["id"])
    endpoint = API_BASE + "/events?" + urlencode({
        "teams": BOSCH_TEAM_ID,
        "seasons": original_id,
        "per_page": 100,
        "page": 1,
    })
    body, status = get(endpoint)

    if not body:
        return {"season_id": str(season["id"]), "status": status, "events": {}}

    try:
        payload = json.loads(body)

        if not isinstance(payload, list):
            raise ValueError("unexpected_event_list")

        return {
            "season_id": str(season["id"]),
            "status": "ok",
            "events": {str(event["id"]): event for event in payload if isinstance(event, dict) and "id" in event},
        }
    except (ValueError, TypeError) as error:
        return {"season_id": str(season["id"]), "status": type(error).__name__, "events": {}}


def inspect_match(match: dict, events: dict, player_names: dict) -> dict:
    page, status = get(str(match.get("event_link") or ""))
    season_id = str(match["sid"])
    event_id = str(match.get("id") or "")

    if not event_id.isdigit():
        event_id = next(
            (
                str(event["id"])
                for event in events.get(season_id, {}).values()
                if str(event.get("date") or "")[:10] == match["date"]
                and str(match["event_link"]).rstrip("/") == str(event.get("link") or "").rstrip("/")
            ),
            "",
        )

    api_event = events.get(season_id, {}).get(event_id)
    api_stats = interpret_performance(api_event, player_names)
    html_stats = parse_match_html(page)

    if str(match.get("id")) in {"7416", "7758", "10145", "12153", "12656"} and page:
        document = BeautifulSoup(page, "html.parser")
        tables = document.select(".sp-template-event-performance table")
        html_stats["debug_table_markup"] = str(tables[0])[:9500] if tables else ""
        html_stats["debug_statistic_markup"] = str(document.select_one(".sp-template-event-statistics"))[:4500]

    official_goals = int(match["gf"])
    accounted_goals = api_stats["goals"]

    if accounted_goals is None:
        accounted_goals = html_stats["bosch_goals"]

    if accounted_goals is None:
        quality = "no_per_player_protocol"
    elif accounted_goals == official_goals:
        quality = "matched"
    elif accounted_goals < official_goals:
        quality = "missing_goal_or_own_goal"
    else:
        quality = "goals_above_official_score"

    return {
        "id": match["id"],
        "event_id": event_id,
        "sid": season_id,
        "date": match["date"],
        "opponent": match["opponent"],
        "score": f"{match['gf']}:{match['ga']}",
        "official_goals": official_goals,
        "event_url": match.get("event_link"),
        "page_status": status,
        "api_status": "ok" if api_event else "event_absent_or_api_unavailable",
        "api": api_stats,
        "html": html_stats,
        "goal_count_from_protocol": accounted_goals,
        "goal_difference_at_match_level": official_goals - accounted_goals if accounted_goals is not None else None,
        "quality": quality,
    }


def main() -> None:
    database = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    names = {
        str(player["id"]): player["name"]
        for player in database.get("players", [])
    }
    season_rows = database.get("seasons", [])
    fixture_rows = database.get("matches", [])
    seasons = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        season_futures = {executor.submit(fetch_season, row): str(row["id"]) for row in season_rows}

        for future in as_completed(season_futures):
            row = future.result()
            seasons[row["season_id"]] = row
            print("PLP events:", row["season_id"], row["status"], len(row["events"]), flush=True)

    events_by_season = {
        season_id: row["events"]
        for season_id, row in seasons.items()
    }
    fixtures = []
    count_done = 0

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(inspect_match, fixture, events_by_season, names): fixture["id"]
            for fixture in fixture_rows
        }

        for future in as_completed(futures):
            try:
                fixtures.append(future.result())
            except Exception as error:
                raise RuntimeError(f"Could not audit match {futures[future]}") from error

            count_done += 1

            if count_done % 15 == 0:
                print(f"Audited {count_done}/{len(fixture_rows)} distinct match URLs", flush=True)

    fixtures.sort(key=lambda match: (match["date"], match["id"]))
    grouped = defaultdict(list)

    for fixture in fixtures:
        grouped[fixture["sid"]].append(fixture)

    season_summaries = []

    for season in season_rows:
        fixtures_in_season = grouped[str(season["id"])]
        breakdown = dict(Counter(fixture["quality"] for fixture in fixtures_in_season))
        season_summaries.append({
            "sid": str(season["id"]),
            "name": season["name"],
            "matches": len(fixtures_in_season),
            "pages_fetched": sum(fixture["page_status"] == "ok" for fixture in fixtures_in_season),
            "api_events_resolved": sum(fixture["api_status"] == "ok" for fixture in fixtures_in_season),
            "fully_attributed_matches": breakdown.get("matched", 0),
            "unmatched_match_level": breakdown.get("missing_goal_or_own_goal", 0),
            "score_conflicts": breakdown.get("goals_above_official_score", 0),
            "missing_per_player_protocols": breakdown.get("no_per_player_protocol", 0),
        })

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub Bosch portal v3 fixture archive + original PLP public WordPress match pages and SportsPress event API",
        "expected_total_matches": len(fixture_rows),
        "fetched_total_pages": sum(row["page_status"] == "ok" for row in fixtures),
        "api_seasons": {key: {"status": value["status"], "count": len(value["events"])} for key, value in seasons.items()},
        "seasons": season_summaries,
        "matches": fixtures,
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    REPORT_PATH.write_text(rendered, encoding="utf-8")
    print("AUDIT_SUMMARY", json.dumps(season_summaries, ensure_ascii=False), flush=True)
    print("AUDIT_MATCHES", len(fixtures), "PAGES", report["fetched_total_pages"], flush=True)


if __name__ == "__main__":
    main()
