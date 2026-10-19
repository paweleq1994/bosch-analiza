#!/usr/bin/env python3
"""Collect confirmed historical opponents' standout players from SportsPress."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from html import unescape
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "scouting_player_updates.json"
TABLES = ROOT / "data" / "scouting_updates.json"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
SEASONS = {"148": "Orlik 2026", "146": "Hala 2025/26", "144": "Orlik 2025", "141": "Hala 2024/2025"}
USER_AGENT = "BoschScout/1.0"
PUBLIC_LISTS = [
    ("Orlik 2026", "https://podlaskaliga.pl/lista/orlik26-indywidualne-i-liga/"),
    ("Orlik 2026", "https://podlaskaliga.pl/lista/orlik26-indywidualne-ii-liga/"),
    ("Hala 2025/26", "https://podlaskaliga.pl/lista/hala25-26-indywidualne-i-liga/"),
    ("Hala 2025/26", "https://podlaskaliga.pl/lista/hala25-26-indywidualne-ii-liga/"),
]


def clean(value: object) -> str:
    if isinstance(value, dict):
        value = value.get("rendered", "")

    return " ".join(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def normalized(value: object) -> str:
    text = unicodedata.normalize("NFD", clean(value).lower().replace("ł", "l"))
    return re.sub(r"[^a-z0-9]+", " ", "".join(character for character in text if unicodedata.category(character) != "Mn")).strip()


def integer(value: object) -> int | None:
    text = str(value).strip() if value is not None else ""
    return int(text) if re.fullmatch(r"\d+", text) else None


def request(url: str):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=12) as response:
        return json.load(response)


def request_html(url: str) -> str:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
        return response.read().decode("utf-8", "replace")


def parse_public_players(html: str, season: str, source_url: str, team_urls: dict) -> dict:
    """Read the whole public table, including rows hidden by client pagination."""
    tables = re.findall(r'<table\b[^>]*class="[^"]*\bsp-player-list\b[^"]*"[^>]*>(.*?)</table>', html, re.S)
    if len(tables) != 1:
        raise ValueError("Expected one official player list")
    grouped = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tables[0], re.S):
        cells = {}
        for classes, content in re.findall(r'<td\b[^>]*class="([^"]*)"[^>]*>(.*?)</td>', row, re.S):
            for column in classes.split():
                cells[column] = content
        def link(column):
            found = re.search(r'href="([^"]+)"', cells.get(column, ""))
            return unescape(found.group(1)).rstrip("/") if found else ""
        team_id = team_urls.get(link("data-team"))
        name = clean(cells.get("data-name"))
        apps, goals, assists = [integer(clean(cells.get(column))) for column in ("data-appearances", "data-goals", "data-assists")]
        if team_id is None or len(name.split()) < 2 or apps is None or apps <= 0 or goals is None or assists is None:
            continue
        profile_url = link("data-name")
        if not profile_url.startswith("https://podlaskaliga.pl/zawodnik/"):
            continue
        grouped.setdefault(str(team_id), []).append({
            "name": name, "apps": apps, "goals": goals, "assists": assists,
            "motm": integer(clean(cells.get("data-pikarzmeczu"))),
            "source_season": season, "source_label": "Oficjalna tabela indywidualna PLP",
            "source_url": source_url, "profile_url": profile_url + "/",
        })
    if not grouped:
        raise ValueError("No identified teams in public player list")
    return grouped


def read_public_lists(teams: dict, fetch=request, fetch_html=request_html):
    team_urls = {}
    warnings = []
    def resolve(item):
        identifier, team = item
        payload = fetch(BASE + "/teams/" + identifier)
        url = str(payload.get("link") or "").rstrip("/")
        if str(payload.get("id")) != identifier or not url.startswith("https://podlaskaliga.pl/druzyna/"):
            raise ValueError("Unverified team identity")
        return url, identifier
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(resolve, item): item[0] for item in teams.items()}
        for future in as_completed(futures):
            try:
                url, identifier = future.result()
                team_urls[url] = identifier
            except Exception as error:
                warnings.append(f"team {futures[future]}: {type(error).__name__}: {error}")
    grouped, sources = {}, []
    for season, url in PUBLIC_LISTS:
        try:
            html = fetch_html(url)
            parsed = parse_public_players(html, season, url, team_urls)
            for identifier, rows in parsed.items():
                grouped.setdefault(identifier, []).extend(rows)
            sources.append({"url": url, "season": season, "sha256": sha256(html.encode()).hexdigest(),
                            "rows": sum(map(len, parsed.values()))})
        except Exception as error:
            warnings.append(f"{url}: {type(error).__name__}: {error}")
    # Retain both editions; selection happens after all candidates are available.
    for identifier, rows in grouped.items():
        rows.sort(key=lambda row: (row["source_season"] == "Orlik 2026", row["goals"] + row["assists"], row["goals"]), reverse=True)
        grouped[identifier] = rows[:24]
    return grouped, sources, warnings


def read_team_players(team: dict, fetch=request) -> list[dict]:
    team_id = str(team["team_id"])
    team_name = str(team["name"])
    season_priorities = {"148": 4, "146": 3, "144": 2, "141": 1}
    records = {}

    url = BASE + "/players?" + urlencode({"teams": team_id, "per_page": 25, "page": 1})
    payload = fetch(url)

    if not isinstance(payload, list):
        raise ValueError("Unexpected PLP team roster response")

    fallback_lookups = 0

    for player in payload[:25]:
        if not isinstance(player, dict) or not str(player.get("id") or "").isdigit():
            continue

        profile = player

        if not isinstance(player.get("statistics"), dict):
            if fallback_lookups >= 5:
                continue

            fallback_lookups += 1

            try:
                profile = fetch(BASE + "/players/" + str(player["id"]))
            except Exception:
                continue

        name = clean(profile.get("title") or player.get("title"))
        player_id = str(player["id"])

        if len(name.split()) < 2:
            continue

        for league_rows in (profile.get("statistics") or {}).values():
            if not isinstance(league_rows, dict):
                continue

            for season_id, stats in league_rows.items():
                if str(season_id) not in SEASONS or not isinstance(stats, dict):
                    continue

                team_markup = str(stats.get("team") or "")
                if normalized(team_markup) != normalized(team_name):
                    continue

                apps = integer(stats.get("appearances"))
                goals = integer(stats.get("goals"))
                assists = integer(stats.get("assists"))

                if apps is None or apps <= 0 or goals is None or assists is None:
                    continue

                row = {
                    "id": player_id,
                    "name": name,
                    "apps": apps,
                    "goals": goals,
                    "assists": assists,
                    "motm": integer(stats.get("pikarzmeczu")),
                    "source_season": SEASONS[str(season_id)],
                    "source_label": "SportsPress: potwierdzony sezon i klub",
                    "source_url": str(profile.get("link") or player.get("link") or ""),
                    "_priority": season_priorities[str(season_id)],
                }

                existing = records.get(player_id)
                if existing is None or row["_priority"] > existing["_priority"]:
                    records[player_id] = row

    return sorted(
        [{key: value for key, value in entry.items() if key != "_priority"} for entry in records.values()],
        key=lambda record: (-(record["goals"] + record["assists"]), record["name"]),
    )[:12]


def refresh(table_data: dict, previous: dict, fetch=request, today: str | None = None, fetch_html=request_html):
    today = today or date.today().isoformat()
    old_date = str(previous.get("_checked_on") or "")
    signature = sha256(json.dumps(table_data.get("tables") or {}, sort_keys=True).encode()).hexdigest()

    if old_date and previous.get("_schema") == 2 and previous.get("_standings_signature") == signature:
        days_passed = (date.fromisoformat(today) - date.fromisoformat(old_date)).days
        if 0 <= days_passed < 7:
            return previous, []

    teams = {}
    for rows in (table_data.get("tables") or {}).values():
        for team in rows:
            if team.get("team_id"):
                teams[str(team["team_id"])] = team

    public, sources, warnings = read_public_lists(teams, fetch, fetch_html)
    updated = {key: value for key, value in previous.items() if key not in ("_checked_on", "_schema")}
    updated.update(public)
    updated["_sources"] = sources
    updated["_schema"] = 2
    updated["_standings_signature"] = signature

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(read_team_players, team, fetch): team_id
            for team_id, team in teams.items()
            if team_id not in public
        }

        for future in as_completed(futures):
            team_id = futures[future]

            try:
                players = future.result()

                if players:
                    updated[team_id] = players
            except Exception as error:
                warnings.append(f"{team_id}: {type(error).__name__}: {error}")

    if not warnings:
        updated["_checked_on"] = today

    return updated, warnings


def main():
    snapshot = json.loads(TABLES.read_text(encoding="utf-8"))
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    updated, warnings = refresh(snapshot, previous)
    result = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"

    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != result:
        OUTPUT.write_text(result, encoding="utf-8")

    print(
        "PLP named scouting players:",
        sum(len(players) for players in updated.values() if isinstance(players, list)),
        "players in",
        len([value for value in updated.values() if isinstance(value, list)]),
        "clubs",
    )

    for warning in warnings[:12]:
        print("PLP scouting players warning:", warning, file=sys.stderr)


if __name__ == "__main__":
    main()
