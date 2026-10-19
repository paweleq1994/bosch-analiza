#!/usr/bin/env python3
"""Capture official public PLP player career tables without SportsPress REST endpoints."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "docs/assets/data.json"
OUTPUT = ROOT / "data/player_html_career_snapshot.json"
SOURCE_COLUMNS = {"apps": "data-appearances", "goals": "data-goals", "assists": "data-assists",
                  "motm": "data-pikarzmeczu", "yellow": "data-yellowcards", "red": "data-redcards"}
FIELDS = tuple(SOURCE_COLUMNS)

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
        self.columns = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table":
            self.depth += 1
            self.table_id += 1
            self.current_is_career = "player-league" in attributes.get("class", "")
        elif tag == "tr" and self.depth and self.current_is_career:
            self.in_row = True
            self.row = []
            self.columns = []
        elif tag in ("td", "th") and self.in_row:
            self.cell = []
            self.columns.append(attributes.get("class", "").split())

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.in_row:
            if self.row:
                self.rows.append({"table": self.table_id, "cells": self.row, "columns": self.columns})
            self.in_row = False
        elif tag == "table" and self.depth:
            self.depth -= 1
            self.current_is_career = False


def capture(url: str) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "podlaskaliga.pl" or not parsed.path.startswith("/zawodnik/"):
        raise ValueError("Not a verified public PLP player URL")

    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BoschArchiveAudit/1.0)"})
    with urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", "replace")

    return parse_career_html(html)


def parse_career_html(html: str, expected_id: str | None = None) -> dict:
    """Read semantic SportsPress columns; older archived templates reorder appearances."""
    if expected_id is not None and str(expected_id) not in set(re.findall(r"\bpostid-(\d+)\b", html)):
        raise ValueError("Archived player identity mismatch")
    parser = CareerTableParser()
    parser.feed(html)
    grouped = {}
    for entry in parser.rows:
        grouped.setdefault(entry["table"], []).append(entry)

    # The final combined table has both a sum and all season rows; never sum
    # the per-league 'Suma' sections, which can overlap or omit supercups.
    if not grouped:
        raise ValueError("No combined career table")
    entries = max(grouped.values(), key=lambda rows: (sum(len(row["cells"]) == 12 for row in rows), len(rows)))
    combined = [row["cells"] for row in entries]
    columns = next((entry["columns"] for entry in entries
                    if all(any(source in cell for cell in entry["columns"]) for source in SOURCE_COLUMNS.values())), None)
    if columns is None:
        raise ValueError("No semantic career columns")
    positions = {field: next(i for i, cell in enumerate(columns) if source in cell)
                 for field, source in SOURCE_COLUMNS.items()}
    final_totals = [row for row in combined if row and row[0].lower() == "suma" and len(row) >= 11]
    if not final_totals:
        raise ValueError("No combined career table")
    last = final_totals[-1]
    totals = {field: int(last[index]) for field, index in positions.items()}

    season_rows = []
    for row in combined:
        if len(row) != 12 or row[0].strip().lower() in {"suma", "sezon"}:
            continue
        try:
            values = {field: int(row[index]) for field, index in positions.items()}
        except (ValueError, IndexError):
            continue
        season_rows.append({"name": row[0], **values})

    # Do not silently drop a competition or parse a different table.
    for field in FIELDS:
        observed = sum(row[field] for row in season_rows)
        if observed != totals[field]:
            raise ValueError(f"Mismatch in HTML player career {field}: rows={observed}, total={totals[field]}")

    return {"totals": totals, "season_rows": season_rows}


def canonicalize_cached_careers(previous: dict, roster: list[dict]) -> dict:
    """Remove historical synthetic aliases only after checking source identity."""
    records = dict(previous)
    for player in roster:
        target_id = str(player["id"])
        for alias in player.get("aliases") or []:
            old_id = str(alias)
            if old_id == target_id or old_id not in records:
                continue

            earlier = records[old_id]
            current = records.get(target_id)
            if current is not None and (
                current.get("source_url") != earlier.get("source_url")
                or current.get("totals") != earlier.get("totals")
            ):
                raise ValueError(
                    f"Conflicting public career cache for {target_id}/{old_id}"
                )
            records.setdefault(target_id, earlier)
            del records[old_id]

    return records


def refresh_public_careers(
    roster: list[dict], previous: dict, get=capture, workers: int = 4
) -> tuple[dict, dict]:
    """Download each published profile once, preserve cached snapshots on outage."""
    players = canonicalize_cached_careers(previous, roster)
    failures = {}
    requests = []

    for player in roster:
        player_id = str(player["id"])
        url = str(player.get("profile_url") or "")
        if not url or not urlsplit(url).path.startswith("/zawodnik/"):
            failures[player_id] = "No public /zawodnik/ profile URL"
            continue

        requests.append((player_id, url, player["name"]))

    def inspect(item: tuple[str, str, str]):
        player_id, url, name = item

        try:
            return player_id, url, name, get(url), None
        except Exception as error:
            return player_id, url, name, None, f"{type(error).__name__}: {error}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for player_id, url, name, record, error in pool.map(inspect, requests):
            if error:
                failures[player_id] = error
                print(f"WARN {player_id} {name}: {error}", flush=True)
                continue

            signature = {**record, "source_url": url}
            prior = players.get(player_id) or {}
            if {key: val for key, val in prior.items() if key != "captured_at"} != signature:
                players[player_id] = {
                    **signature,
                    "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            print(f"OK {player_id} {name}: {record['totals']}", flush=True)

    return players, failures


def main():
    db = json.loads(PORTAL.read_text(encoding="utf-8"))
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"players": {}}
    players, failures = refresh_public_careers(db["players"], previous.get("players", {}))
    snapshot = {"players": players, "failures": failures}
    rendered = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"HTML career audit: {len(players)}/{len(db['players'])} profiles, {len(failures)} failures", flush=True)

if __name__ == "__main__":
    main()
