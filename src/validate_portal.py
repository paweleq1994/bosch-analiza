#!/usr/bin/env python3
"""Validate consolidated public portal data before publishing."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
seasons = DATA["seasons"]
matches = DATA["matches"]
assert len(seasons) >= 8, "Expected eight historical seasons"
assert len(matches) >= 113, "Unexpected loss of historical matches"
assert len({(row["id"], row["sid"]) for row in matches}) == len(matches), "Duplicate match identity"
assert len({row["id"] for row in DATA["videos"]}) == len(DATA["videos"]), "Duplicate video ID"
for season in seasons:
    entries = [row for row in matches if str(row["sid"]) == str(season["id"])]
    if len(entries) != season["matches"]:
        raise AssertionError(f"Incorrect match count for {season['name']}")
    wins = sum(row["gf"] > row["ga"] for row in entries)
    draws = sum(row["gf"] == row["ga"] for row in entries)
    assert season["points"] == wins * 3 + draws, f"Incorrect points for {season['name']}"
    assert season["gf"] == sum(row["gf"] for row in entries), f"Incorrect goals for {season['name']}"
    assert season["ga"] == sum(row["ga"] for row in entries), f"Incorrect conceded goals for {season['name']}"
print(f"Valid: {len(seasons)} seasons, {len(matches)} games, {len(DATA['videos'])} videos")
