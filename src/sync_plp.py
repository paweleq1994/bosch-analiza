#!/usr/bin/env python3
"""Synchronize played Bosch matches from SportsPress, including existing seasons.

A season is replaced atomically only if all played event scores agree with the
published league table. A transient API failure leaves the last snapshot intact.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "league_updates.json"
PORTAL = ROOT / "docs" / "assets" / "data.json"
PROFILES = ROOT / "data" / "player_profile_map.json"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
BOSCH_ID = 6951
USER_AGENT = "BoschKnowledgeBase/1.0 (+https://github.com/paweleq1994/bosch-analiza)"
FIELDS = ("goals", "assists", "pikarzmeczu", "top", "yellowcards", "redcards")


def request(resource: str, params: dict | None = None):
    url = f"{BASE}/{resource}"
    if params:
        url += "?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=35) as response:
        return json.load(response)


def clean(value):
    if isinstance(value, dict):
        value = value.get("rendered", "")
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).split())


def norm(value):
    text = unicodedata.normalize("NFD", clean(value).lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).split())


def number(value):
    if isinstance(value, bool):
        return None
    text = str(value if value is not None else "").strip()
    return int(text) if re.fullmatch(r"\d+", text) else None


def season_key(value):
    text = norm(value)
    match = re.search(r"\b(orlik|hala)\s+(20\d{2})(?:\s+(20\d{2}))?\b", text)
    return (match.group(1), match.group(2), match.group(3) or "") if match else None


def season_id_for(plp_id: int, label: str, known: list[dict]):
    for item in known:
        if str(item.get("plp_id") or item.get("id")) == str(plp_id):
            return str(item["id"])
    key = season_key(label)
    if key:
        matched = [row for row in known if season_key(row["name"]) == key]
        if len(matched) == 1:
            return str(matched[0]["id"])
    return str(plp_id)


def league_table(payload, season_id: int):
    possible = []
    for table in payload:
        data = table.get("data")
        if not isinstance(data, dict) or str(BOSCH_ID) not in data:
            continue
        title = clean(table.get("title"))
        slug = str(table.get("slug") or "").lower()
        if "fair" in slug or "fair" in norm(title) or "generalka" in norm(title):
            continue
        if "liga" not in norm(title) and "liga" not in slug:
            continue
        row = data[str(BOSCH_ID)]
        if not isinstance(row, dict):
            continue
        fields = {field: number(row.get(key)) for field, key in {
            "position": "pos", "points": "pkt", "matches": "m", "wins": "w",
            "draws": "r", "losses": "p", "gf": "g", "ga": "s",
        }.items()}
        if any(value is None for value in fields.values()):
            continue
        tier = 1 if re.search(r"\b(ii|2)\s+liga\b", norm(title)) or slug.startswith(("ii-liga", "2-liga")) else 0
        possible.append((tier, title, fields))
    possible.sort(key=lambda item: (-item[0], item[1]))
    return possible[0][1:] if possible else None


def player_stats_from_event(event, profiles):
    team_data = (event.get("performance") or {}).get(str(BOSCH_ID))
    if not isinstance(team_data, dict) or not team_data:
        return [], False
    rows = []
    for player_id, entry in team_data.items():
        if not str(player_id).isdigit() or int(player_id) == 0 or not isinstance(entry, dict):
            continue
        # SportsPress sometimes includes all roster names without any match data.
        played = bool(str(entry.get("status") or "").strip()) or any(
            str(entry.get(key) or "").strip() for key in FIELDS + ("samobje", "ocenabramkarza")
        )
        if not played:
            continue
        stats = {key: number(entry.get(key)) for key in FIELDS}
        if any(value is None and str(entry.get(key) or "").strip() for key, value in stats.items()):
            # Do not turn unparseable values (e.g. time annotations) into invented goals.
            return [], False
        profile = profiles.get(str(player_id)) or {}
        rows.append({
            "id": str(player_id), "name": profile.get("resolved_name") or f"Zawodnik #{player_id}",
            "apps": 1, "goals": stats["goals"] or 0, "assists": stats["assists"] or 0,
            "motm": stats["pikarzmeczu"] or 0, "top": stats["top"] or 0,
            "yellow": stats["yellowcards"] or 0, "red": stats["redcards"] or 0,
        })
    return rows, bool(rows)


def date_today():
    return date.today().isoformat()


def parse_event(event, plp_season_id: int, public_season_id: str, season_name: str, legacy: list[dict], profiles):
    teams = [number(item) for item in event.get("teams") or []]
    if len(teams) != 2 or BOSCH_ID not in teams or None in teams:
        return None
    other_id = next(team_id for team_id in teams if team_id != BOSCH_ID)
    score = event.get("results") or {}
    own = number((score.get(str(BOSCH_ID)) or {}).get("goals"))
    conceded = number((score.get(str(other_id)) or {}).get("goals"))
    date_value = str(event.get("date") or "")[:10]
    if own is None or conceded is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value) or date_value > date_today():
        return None  # Scheduled games must not be counted as draws.
    title = clean(event.get("title"))
    names = re.split(r"\s+vs\.?\s+", title, maxsplit=1, flags=re.I)
    opponent = (names[1] if teams[0] == BOSCH_ID else names[0]) if len(names) == 2 else f"Rywal #{other_id}"
    event_id = str(event.get("id") or "")
    if not event_id.isdigit():
        return None
    match_id = event_id
    # Orlik 2026 has legacy synthetic match URLs and external video bindings.
    legacy_candidates = [m for m in legacy if str(m.get("sid")) == public_season_id and m.get("date") == date_value and norm(m.get("opponent")) == norm(opponent)]
    if len(legacy_candidates) == 1:
        match_id = str(legacy_candidates[0]["id"])
    stats, complete = player_stats_from_event(event, profiles)
    firsthalf = ((score.get(str(BOSCH_ID)) or {}).get("firsthalf"), (score.get(str(other_id)) or {}).get("firsthalf"))
    halftime = f"{firsthalf[0]}:{firsthalf[1]}" if all(number(v) is not None for v in firsthalf) else ""
    return {
        "id": match_id, "event_id": event_id, "sid": public_season_id,
        "plp_season_id": str(plp_season_id), "season": season_name, "date": date_value,
        "opponent_id": other_id, "opponent": opponent, "match": title,
        "gf": own, "ga": conceded, "halftime": halftime,
        "event_link": event.get("link") or "", "player_stats": stats,
        "player_stats_complete": complete,
    }


def validate_season(standing, events):
    if not standing["matches"] and not events:
        return True
    if standing["wins"] + standing["draws"] + standing["losses"] != standing["matches"]:
        return False
    return (
        len(events) == standing["matches"]
        and len({str(item["event_id"]) for item in events}) == len(events)
        and sum(item["gf"] for item in events) == standing["gf"]
        and sum(item["ga"] for item in events) == standing["ga"]
        and 3 * sum(item["gf"] > item["ga"] for item in events)
            + sum(item["gf"] == item["ga"] for item in events) == standing["points"]
        and sum(item["gf"] > item["ga"] for item in events) == standing["wins"]
        and sum(item["gf"] == item["ga"] for item in events) == standing["draws"]
        and sum(item["gf"] < item["ga"] for item in events) == standing["losses"]
    )


def aggregate_players(rows, sid):
    if not rows or not all(row.get("player_stats_complete") for row in rows):
        return []  # No partial leaderboards masquerading as complete season statistics.
    people = {}
    for match in rows:
        for stat in match.get("player_stats", []):
            pid = stat["id"]
            if pid not in people:
                people[pid] = {**stat, "sid": sid}
            else:
                for field in ("apps", "goals", "assists", "motm", "top", "yellow", "red"):
                    people[pid][field] += stat[field]
    return sorted(people.values(), key=lambda row: row["id"])


def fetch_event_pages(season_id: int):
    page, rows = 1, []
    while True:
        page_rows = request("events", {"teams": BOSCH_ID, "seasons": season_id, "per_page": 100, "page": page})
        if not isinstance(page_rows, list):
            raise ValueError("Unexpected Sportspress events response")
        rows.extend(page_rows)
        if len(page_rows) < 100:
            return rows
        page += 1


def synchronize(team, fetch_tables, fetch_events, existing, known_seasons, legacy_matches, profiles):
    """Pure synchronization engine; dependencies are injected for regression tests."""
    valid = []
    errors = []
    for raw_sid in team.get("seasons") or []:
        sid = number(raw_sid)
        if sid is None:
            continue
        try:
            candidates = fetch_tables(sid)
            table = league_table(candidates, sid)
            if table is None:
                continue
            title, counts = table
            local_sid = season_id_for(sid, title, known_seasons)
            local_name = next((s["name"] for s in known_seasons if str(s["id"]) == local_sid), None) or (" ".join(season_key(title)) if season_key(title) else title).strip()
            standing = {
                "id": local_sid, "plp_id": str(sid), "name": local_name,
                **counts, "clean_sheets": None, "table": title, "origin": "plp_sync",
            }
            if standing["matches"] == 0 and not any(str(s["id"]) == local_sid for s in known_seasons):
                continue  # Keep homepage focused on last played season.
            events = [parsed for event in fetch_events(sid)
                      if (parsed := parse_event(event, sid, local_sid, local_name, legacy_matches, profiles)) is not None]
            if not validate_season(standing, events):
                errors.append(f"Season {local_name}: table/match mismatch; snapshot unchanged")
                continue
            standing["clean_sheets"] = sum(match["ga"] == 0 for match in events)
            valid.append((standing, events, aggregate_players(events, local_sid)))
        except Exception as error:
            errors.append(f"Season {sid}: {type(error).__name__}: {error}")
    merged_seasons = {str(row["id"]): row for row in existing.get("season_rows", [])}
    matches_by_season = defaultdict(list)
    for item in existing.get("matches", []):
        matches_by_season[str(item["sid"])].append(item)
    people_by_season = defaultdict(list)
    for person in existing.get("player_seasons", []):
        people_by_season[str(person["sid"])].append(person)
    for standing, events, people in valid:
        sid = str(standing["id"])
        merged_seasons[sid] = standing
        matches_by_season[sid] = events
        people_by_season[sid] = people
    payload = {
        "season_rows": sorted(merged_seasons.values(), key=lambda item: (season_key(item["name"]) or ("", "", ""), str(item["id"]))),
        "matches": sorted((match for group in matches_by_season.values() for match in group), key=lambda item: (item["date"], str(item["id"]))),
        "player_seasons": sorted((person for group in people_by_season.values() for person in group), key=lambda item: (str(item["sid"]), item["id"])),
    }
    return payload, valid, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Fail if every source fails")
    args = parser.parse_args()
    portal = json.loads(PORTAL.read_text(encoding="utf-8"))
    current = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"season_rows": [], "matches": [], "player_seasons": []}
    profiles = json.loads(PROFILES.read_text(encoding="utf-8")) if PROFILES.exists() else {}
    try:
        team = request(f"teams/{BOSCH_ID}")
    except Exception as error:
        print(f"PLP unavailable; retained previous snapshot: {type(error).__name__}: {error}", file=sys.stderr)
        if args.strict:
            raise
        return
    payload, valid, errors = synchronize(
        team,
        lambda sid: request("tables", {"seasons": sid, "per_page": 100}),
        fetch_event_pages, current, portal.get("seasons", []), portal.get("matches", []), profiles,
    )
    for message in errors:
        print("PLP warning:", message, file=sys.stderr)
    if not valid and errors and args.strict:
        raise RuntimeError("Every PLP season failed verification")
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"PLP updated: {len(valid)} season snapshots, {len(payload['matches'])} matches")
    else:
        print(f"PLP unchanged: {len(valid)} verified seasons")


if __name__ == "__main__":
    main()
