#!/usr/bin/env python3
"""Validate consolidated public portal data before publishing."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
seasons = DATA["seasons"]
matches = DATA["matches"]
players = DATA["players"]
player_ids = [str(player["id"]) for player in players]
assert len(player_ids) == len(set(player_ids)), "Duplicate PLP player identifiers"

alias_ids = [str(alias) for player in players for alias in player.get("aliases", [])]
assert len(alias_ids) == len(set(alias_ids)), "Duplicate player aliases"
assert not any(alias in player_ids for alias in alias_ids), "Player alias collides with active ID"

daniluk = [player for player in players if player["name"] == "Dawid Daniluk"]
assert len(daniluk) == 1 and daniluk[0]["id"] == "2204", "Daniluk must resolve to PLP player 2204"
assert "new-dawid-daniluk" in daniluk[0].get("aliases", []), "Preserve old Daniluk profile link"
assert daniluk[0]["orlik2026"]["goals"] == 16, "Missing verified Daniluk recap goals"

for player in players:
    seasons = [str(entry["sid"]) for entry in player.get("season_history", [])]
    assert len(seasons) == len(set(seasons)), f"Repeated Bosch season for {player['name']}"

    career = player.get("career_totals") or {}
    career_seasons = [
        (str(entry["sid"]), str(entry["team"]))
        for entry in career.get("season_rows", [])
    ]
    assert len(career_seasons) == len(set(career_seasons)), f"Repeated PLP career season for {player['name']}"
assert len(seasons) >= 8, "Expected eight historical seasons"
assert len([row for row in seasons if row["id"] == "orlik-2026"]) == 1, "Orlik 2026 must appear once"
assert not any(str(row["id"]) == "148" for row in seasons), "PLP 148 duplicates Orlik 2026"
assert not any(str(row["sid"]) == "148" for row in matches), "Orlik 2026 match alias must not appear"
assert len(matches) == len({(row["sid"], row["date"], row["opponent"]) for row in matches}), "Duplicate fixtures"
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
# Backfilled official Orlik 2026 YouTube coverage: last fixture has no recording yet.
orlik = [row for row in matches if row["sid"] == "orlik-2026"]
assert len(orlik) == 15, "Expected complete Orlik 2026 season"
linked = {row["id"] for row in orlik if row.get("videos")}
assert len(linked) >= 14, f"Missing archived Orlik 2026 YouTube footage: {len(linked)}/15"
assert all(row.get("videos") for row in orlik if row["id"] != "orlik26-15"), "Missing 2026 fixture recording"
print(f"Valid: {len(seasons)} seasons, {len(matches)} games, {len(DATA['videos'])} videos")
