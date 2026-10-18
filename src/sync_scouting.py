#!/usr/bin/env python3
"""Refresh PLP league TABLE snapshots used by opponent scouting.

The main Bosch match importer is intentionally separate. This updater reads
verified I/II-division standings for specific competition editions, preserving
the last valid snapshot when PLP is unavailable or its tables are inconsistent.
It does not invent tactical observations or scrape protected video.
"""
from __future__ import annotations

from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "scouting_updates.json"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
BOSCH_ID = 6951
USER_AGENT = "BoschScouting/1.0 (+https://github.com/paweleq1994/bosch-analiza)"

def request(path, params=None):
    url = BASE + "/" + path
    if params:
        url += "?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        return json.load(response)

def normalize(value):
    if isinstance(value, dict):
        value = value.get("rendered") or ""
    value = unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).lower()
    decomposed = unicodedata.normalize("NFD", value)
    return re.sub(r"\s+", " ", "".join(c for c in decomposed if unicodedata.category(c) != "Mn")).strip()

def as_integer(value):
    if isinstance(value, bool):
        return None
    value = str(value if value is not None else "").strip()
    return int(value) if re.fullmatch(r"\d+", value) else None

def edition(label):
    """Choose a single known edition; don't silently import unrelated seasons."""
    label = normalize(label)
    collapsed = re.sub(r"[^a-z0-9]", "", label)
    if ("orlik26" in collapsed or "orlik2026" in collapsed):
        return "orlik_2026"
    if any(x in collapsed for x in ("hala2526", "hala20252026")):
        return "hala_2025_26"
    if any(x in collapsed for x in ("hala2627", "hala20262027")):
        return "hala_2026_27"
    return None

def level(title, slug):
    normalized = normalize(slug).replace("-", " ") + " " + normalize(title)
    if re.search(r"\b(ii|2)\s+liga\b", normalized):
        return "h2"
    if re.search(r"\b(i|1)\s+liga\b", normalized):
        return "h1"
    return None

def parse_table(table):
    slug = str(table.get("slug") or "")
    title = normalize(table.get("title"))
    category = edition(slug) or edition(title)
    division = level(title, slug)
    if not category or not division:
        return None
    key = category + "_" + division
    contents = table.get("data") or {}
    if not isinstance(contents, dict) or len(contents) < 8:
        return None
    standings = []
    for team_id, raw in contents.items():
        if not isinstance(raw, dict):
            return None
        fields = {
            field: as_integer(raw.get(api_key))
            for field, api_key in (
                ("position", "pos"), ("matches", "m"),
                ("wins", "w"), ("draws", "r"), ("losses", "p"),
                ("gf", "g"), ("ga", "s"), ("points", "pkt")
            )
        }
        team_name = normalize(raw.get("name"))
        if str(team_id) == "0" or team_name == "druzyna" or fields["position"] == 0:
            continue
        if not team_name or any(value is None for value in fields.values()):
            return None
        if fields["matches"] != fields["wins"] + fields["draws"] + fields["losses"]:
            return None
        if fields["points"] != fields["wins"] * 3 + fields["draws"]:
            return None
        if fields["position"] < 1:
            return None
        standings.append({
            "team_id": str(team_id), "name": unescape(re.sub(r"<[^>]*>", "", str(raw["name"]))).strip(),
            **fields, "tier": 2 if division == "h2" else 1
        })
    if len(standings) < 8:
        return None
    if len({row["team_id"] for row in standings}) != len(standings):
        return None
    if len({row["position"] for row in standings}) != len(standings):
        return None
    standings.sort(key=lambda row: (row["position"], row["name"]))
    return key, standings

def collect(teams_response, request_tables, last):
    """Pure function to support regression tests without live PLP access."""
    current = dict(last.get("tables") or {})
    successes = {}
    warnings = []
    seasons = teams_response.get("seasons") or []
    numeric = sorted({i for value in seasons if (i := as_integer(value)) is not None and i >= 146}, reverse=True)
    # Bosch's known Hala'25/26 season ID is 146. New seasons use later IDs.
    for sid in numeric[:12]:
        try:
            tables = request_tables(sid)
            if not isinstance(tables, list):
                raise ValueError("Invalid tables response")
            for table in tables:
                candidate = parse_table(table)
                if candidate is None:
                    continue
                key, rows = candidate
                if key not in ("orlik_2026_h1", "orlik_2026_h2",
                               "hala_2025_26_h1", "hala_2025_26_h2",
                               "hala_2026_27_h1"):
                    continue
                # Don't treat a stray table as the actual hall I league.
                if key == "hala_2026_27_h1" and str(BOSCH_ID) not in {r["team_id"] for r in rows}:
                    continue
                if key in successes and successes[key]["season_id"] != str(sid):
                    warnings.append(f"Conflicting editions for {key}")
                    continue
                successes[key] = {"season_id": str(sid), "table": rows}
            if not any(parse_table(table) for table in tables):
                warnings.append(f"Season {sid}: no matching table; examples: " + ", ".join(str(t.get("slug") or t.get("title"))[:45] for t in tables[:4]))
        except Exception as error:
            warnings.append(f"Season {sid}: {type(error).__name__}: {error}")
    for key, snapshot in successes.items():
        current[key] = snapshot["table"]
    return {"tables": current, "season_ids": {
        **last.get("season_ids", {}),
        **{key: snapshot["season_id"] for key, snapshot in successes.items()}
    }}, warnings

def main():
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        previous = {"tables": {}, "season_ids": {}}
    try:
        team = request(f"teams/{BOSCH_ID}")
        if not isinstance(team, dict):
            raise ValueError("Invalid team payload")
        try:
            listed = request("seasons", {"per_page": 100})
            if isinstance(listed, list):
                all_ids = [row.get("id") for row in listed if isinstance(row, dict) and edition(row.get("slug") or row.get("name") or row.get("title"))]
                team = {**team, "seasons": list(team.get("seasons") or []) + all_ids}
        except Exception as error:
            print(f"Season directory unavailable; using Bosch seasons: {error}", file=sys.stderr)
        updated, warnings = collect(
            team, lambda sid: request("tables", {"seasons": sid, "per_page": 100}), previous
        )
    except Exception as error:
        print(f"PLP scouting: source unavailable; kept last valid data: {error}", file=sys.stderr)
        return
    for warning in warnings:
        print("PLP scouting warning: " + warning, file=sys.stderr)
    rendered = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if not OUT.exists() or rendered != OUT.read_text(encoding="utf-8"):
        OUT.write_text(rendered, encoding="utf-8")
        print(f"PLP scouting: updated {len(updated['tables'])} validated standings")
    else:
        print(f"PLP scouting: unchanged ({len(updated['tables'])} validated standings)")

if __name__ == "__main__":
    main()
