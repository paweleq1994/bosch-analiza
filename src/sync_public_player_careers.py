#!/usr/bin/env python3
"""Capture official public PLP player career tables without SportsPress REST endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "docs/assets/data.json"
OUTPUT = ROOT / "data/player_html_career_snapshot.json"
HEADERS = {"apps": 1, "goals": 3, "assists": 4, "motm": 5, "yellow": 8, "red": 9}
FIELDS = tuple(HEADERS)

class CareerTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.table_id = 0
        self.depth = 0
        self.in_row = False
        self.cell = None
        self.row = []
        self.rows = []
        self.current_is_career = False
        self.capture_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table":
            self.depth += 1
            self.table_id += 1
            self.current_is_career = "player-league" in attributes.get("class", "")
        elif tag == "tr" and self.depth and self.current_is_career:
            self.in_row = True
            self.row = []
        elif tag in ("td", "th") and self.in_row:
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.in_row:
            if self.row:
                self.rows.append({"table": self.table_id, "cells": self.row})
            self.in_row = False
        elif tag == "table" and self.depth:
            self.depth -= 1
            self.current_is_career = False


def capture(url: str) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "podlaskaliga.pl" or not parsed.path.startswith("/zawodnik/"):
        raise ValueError("Not a verified public PLP player URL")

    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BoschArchiveAudit/1.0)"})
    with urlopen(request, timeout=35) as response:
        html = response.read().decode("utf-8", "replace")

    parser = CareerTableParser()
    parser.feed(html)
    grouped = {}
    for entry in parser.rows:
        grouped.setdefault(entry["table"], []).append(entry["cells"])

    # The final combined table has both a sum and all season rows; never sum
    # the per-league 'Suma' sections, which can overlap or omit supercups.
    combined = max(grouped.values(), key=lambda rows: (sum(len(row) == 12 for row in rows), len(rows)))
    final_totals = [row for row in combined if row and row[0].lower() == "suma" and len(row) >= 11]
    if not final_totals:
        raise ValueError("No combined career table")
    last = final_totals[-1]
    totals = {field: int(last[index]) for field, index in HEADERS.items()}

    season_rows = []
    for row in combined:
        if len(row) != 12 or row[0].strip().lower() in {"suma", "sezon"}:
            continue
        try:
            values = {field: int(row[index]) for field, index in HEADERS.items()}
        except (ValueError, IndexError):
            continue
        season_rows.append({"name": row[0], **values})

    # Do not silently drop a competition or parse a different table.
    for field in FIELDS:
        observed = sum(row[field] for row in season_rows)
        if observed != totals[field]:
            raise ValueError(f"Mismatch in HTML player career {field}: rows={observed}, total={totals[field]}")

    return {"totals": totals, "season_rows": season_rows}


def main():
    db = json.loads(PORTAL.read_text(encoding="utf-8"))
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"players": {}}
    players = previous.get("players", {})
    failures = {}
    for player in db["players"]:
        player_id = str(player["id"])
        url = str(player.get("profile_url") or "")
        if not url or not urlsplit(url).path.startswith("/zawodnik/"):
            failures[player_id] = "No public /zawodnik/ profile URL"
            continue
        try:
            record = capture(url)
            players[player_id] = {
                **record,
                "source_url": url,
                "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            print(f"OK {player_id} {player['name']}: {record['totals']}", flush=True)
        except Exception as error:
            failures[player_id] = str(error)
            print(f"WARN {player_id} {player['name']}: {error}", flush=True)
        time.sleep(0.35)

    snapshot = {"players": players, "failures": failures}
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"HTML career audit: {len(players)}/{len(db['players'])} profiles, {len(failures)} failures", flush=True)


if __name__ == "__main__":
    main()
