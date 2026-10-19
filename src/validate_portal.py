#!/usr/bin/env python3
"""Validate consolidated public portal data before publishing."""
from pathlib import Path
import json
from sync_videos import validate_fixture_dates
from copy import deepcopy
from player_totals import confirm_bosch_totals

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
seasons = DATA["seasons"]
matches = DATA["matches"]
players = DATA["players"]
jurkowicz = next(player for player in players if str(player["id"]) == "7275")
assert all(jurkowicz[field] >= baseline for field, baseline in (("apps", 69), ("goals", 30), ("assists", 20))), "Historical PLP Supercup totals for Jurkowicz regressed"
assert jurkowicz["career_totals"]["apps"] >= 69 and jurkowicz["career_totals"]["goals"] >= 30, "Historical whole-career PLP totals regressed"
player_ids = [str(player["id"]) for player in players]
assert len(player_ids) == len(set(player_ids)), "Duplicate PLP player identifiers"

alias_ids = [str(alias) for player in players for alias in player.get("aliases", [])]
assert len(alias_ids) == len(set(alias_ids)), "Duplicate player aliases"
assert not any(alias in player_ids for alias in alias_ids), "Player alias collides with active ID"

daniluk = [player for player in players if player["name"] == "Dawid Daniluk"]
assert len(daniluk) == 1 and daniluk[0]["id"] == "2204", "Daniluk must resolve to PLP player 2204"
assert "new-dawid-daniluk" in daniluk[0].get("aliases", []), "Preserve old Daniluk profile link"
assert daniluk[0]["orlik2026"]["goals"] >= 16, "Missing verified Daniluk recap goals"

known_scorers = {
    "wojciuk": next((player for player in players if "wojciuk" in player["name"].lower()), None),
    "pietruczuk": next((player for player in players if "pietruczuk" in player["name"].lower()), None),
}
assert all(known_scorers.values()), "Official PLP scorers are missing from the Bosch roster"
assert known_scorers["wojciuk"]["goals"] >= 2, "Missing Wojciuk official goals"
assert known_scorers["pietruczuk"]["goals"] >= 1, "Missing Pietruczuk match goal"
if not known_scorers["pietruczuk"].get("stats_minimum"):
    verified = deepcopy(known_scorers["pietruczuk"])
    verified["stats_minimum"] = True
    assert confirm_bosch_totals(verified), "A full balance needs independently confirmed public Bosch season rows"

attribution = DATA["analysis"]["player_goal_coverage"]
for record in attribution:
    assert record["team_goals"] == (
        record["attributed_goals"] + record["administrative_goals"] + record["opponent_own_goals"] + record["unattributed_goals"] + record.get("pending_match_goals", 0)
    ), f"Unbalanced season goal attribution: {record['season']}"
    assert record["unattributed_goals"] >= 0, f"Negative unexplained goals: {record['season']}"
    pending = [match for match in matches if str(match["sid"]) == str(record["sid"]) and not (match.get("goal_protocol") or {}).get("verified")]
    assert record.get("pending_match_count", 0) == len(pending), f"Incorrect pending match count: {record['season']}"
    assert record.get("pending_match_goals", 0) == sum(match["gf"] for match in pending), f"Incorrect pending goals: {record['season']}"

awarded_goals = sum(record["administrative_goals"] for record in attribution)
assert awarded_goals >= 1, "The officially awarded OST Sport goal must be accounted for"
assert any(
    event["match_id"] == "12656"
    for record in attribution
    for event in record.get("administrative_events", [])
), "Official walkover evidence is missing"

for player in players:
    for field in ("apps", "goals", "assists", "motm"):
        confirmed = sum(
            record[field]
            for record in player.get("season_history", [])
            if type(record.get(field)) is int
        )
        unassigned = (player.get("season_coverage") or {}).get("unassigned", {}).get(field)

        if type(player.get(field)) is int:
            assert type(unassigned) is int and confirmed + unassigned == player[field], (
                f"Inconsistent {field} history for {player['name']}"
            )

    player_season_ids = [str(entry["sid"]) for entry in player.get("season_history", [])]
    assert len(player_season_ids) == len(set(player_season_ids)), f"Repeated Bosch season for {player['name']}"

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
assert len(matches) >= 113, "The 113 audited historical matches are missing"
assert sum(bool(match.get("goal_protocol", {}).get("verified")) for match in matches) >= 113, "Published snapshot lost verified historical goal protocols"
assert len([player for player in players if str(player["id"]) == "7284"]) == 1, "Canonical goalkeeper missing"
assert not any(str(player["id"]) == "13060" for player in players), "Duplicate goalkeeper reappeared"
assert all(row["unattributed_goals"] == 0 for row in attribution if row.get("audited", True)), "Verified match goals may not be lost during publication"
assert sum(row["attributed_goals"] for row in attribution) >= 289, "Verified historical scorer attribution regressed"
assert DATA["analysis"]["match_protocol_audit"]["total_own_goals_conceded"] >= 6, "Verified historical own goals regressed"
assert len({(row["id"], row["sid"]) for row in matches}) == len(matches), "Duplicate match identity"
assert len({row["id"] for row in DATA["videos"]}) == len(DATA["videos"]), "Duplicate video ID"
validate_fixture_dates(DATA["videos"], matches)
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
archived_orlik_ids = {f"orlik26-{index}" for index in range(1, 16)}
assert archived_orlik_ids.issubset({row["id"] for row in orlik}), "Missing original Orlik 2026 fixtures"
linked = {row["id"] for row in orlik if row.get("videos")}
assert len(linked) >= 14, f"Missing archived Orlik 2026 YouTube footage: {len(linked)}/15"
assert all(row.get("videos") for row in orlik if row["id"] in archived_orlik_ids - {"orlik26-15"}), "Missing historical 2026 fixture recording"
print(f"Valid: {len(seasons)} seasons, {len(matches)} games, {len(DATA['videos'])} videos")
