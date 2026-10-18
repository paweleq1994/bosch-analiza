#!/usr/bin/env python3
"""Fetch published Bosch matches from the public Sportspress API conservatively."""
from __future__ import annotations

from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "league_updates.json"
ARCHIVE = ROOT / "docs" / "assets" / "data.json"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
BOSCH_ID = 6951


def request(resource: str, params: dict | None = None):
    url = BASE + "/" + resource + (("?" + urlencode(params)) if params else "")
    with urlopen(Request(url, headers={"User-Agent": "BoschKnowledgeBase/1.0"}), timeout=30) as response:
        return json.load(response)


def text(value):
    if isinstance(value, dict):
        value = value.get("rendered", "")
    return unescape(re.sub("<[^>]+>", " ", str(value or ""))).strip()


def number(value):
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return 0


def main():
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    historic_ids = {str(item["id"]) for item in archive.get("seasons", [])}
    existing = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"season_rows": [], "matches": []}
    try:
        team = request(f"teams/{BOSCH_ID}")
    except Exception as error:
        print(f"PLP unavailable; retain last validated snapshot: {type(error).__name__} {error}", file=sys.stderr)
        return
    new_seasons = []
    new_matches = []
    for season_id in sorted({number(s) for s in team.get("seasons", []) if number(s)}):
        if str(season_id) in historic_ids:
            continue
        try:
            tables = request("tables", {"seasons": season_id, "per_page": 100})
            league = next((obj for obj in tables if ("liga" in text(obj.get("title")).lower()) and str(BOSCH_ID) in (obj.get("data") or {})), None)
            if league is None:
                continue
            row = league["data"][str(BOSCH_ID)]
            standing = {
                "id": str(season_id), "name": text(league.get("title")),
                "position": number(row.get("pos")), "points": number(row.get("pkt")),
                "matches": number(row.get("m")), "wins": number(row.get("w")),
                "draws": number(row.get("r")), "losses": number(row.get("p")),
                "gf": number(row.get("g")), "ga": number(row.get("s")),
                "clean_sheets": None, "table": text(league.get("title")),
                "origin": "plp_sync",
            }
            if not standing["matches"] or standing["wins"] * 3 + standing["draws"] != standing["points"]:
                continue
            page = 1
            found = []
            while True:
                entries = request("events", {"teams": BOSCH_ID, "seasons": season_id, "per_page": 100, "page": page})
                if not isinstance(entries, list):
                    raise ValueError("Unexpected PLP event response")
                found.extend(entries)
                if len(entries) < 100:
                    break
                page += 1
            for event in found:
                teams = [number(item) for item in event.get("teams", [])]
                if BOSCH_ID not in teams or len(teams) < 2:
                    continue
                opponent_id = next((value for value in teams if value != BOSCH_ID), None)
                results = event.get("results") or {}
                own = (results.get(str(BOSCH_ID)) or {}).get("goals")
                other = (results.get(str(opponent_id)) or {}).get("goals")
                if own in ("", None) or other in ("", None):
                    continue
                title = text(event.get("title"))
                parts = re.split(r"\s+vs\s+", title, flags=re.I)
                opponent = parts[1] if len(parts) == 2 and teams[0] == BOSCH_ID else parts[0] if len(parts) == 2 else f"Rywal #{opponent_id}"
                found_entry = {
                    "event_id": str(event["id"]), "sid": str(season_id),
                    "season": standing["name"], "date": str(event.get("date", ""))[:10],
                    "opponent": opponent, "opponent_id": opponent_id,
                    "match": title, "gf": number(own), "ga": number(other),
                    "halftime": "", "event_link": event.get("link") or "", "links": [],
                }
                if found_entry["date"]:
                    new_matches.append(found_entry)
            all_for_season = [item for item in new_matches if item["sid"] == str(season_id)]
            if len(all_for_season) == standing["matches"] and sum(item["gf"] for item in all_for_season) == standing["gf"] and sum(item["ga"] for item in all_for_season) == standing["ga"]:
                new_seasons.append(standing)
            else:
                new_matches = [item for item in new_matches if item["sid"] != str(season_id)]
        except Exception as error:
            print(f"PLP season {season_id} skipped: {type(error).__name__} {error}", file=sys.stderr)
    valid_ids = {row["id"] for row in new_seasons}
    updated = {
        "season_rows": sorted({row["id"]: row for row in (existing.get("season_rows") or []) + new_seasons}.values(), key=lambda row: row["id"]),
        "matches": sorted({str(row["event_id"]): row for row in (existing.get("matches") or [] if str(row["sid"]) not in valid_ids) + new_matches}.values(), key=lambda row: (row["date"], row["event_id"])),
    }
    rendered = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"PLP sync: {len(updated['season_rows'])} additional seasons, {len(updated['matches'])} games")


if __name__ == "__main__":
    main()
