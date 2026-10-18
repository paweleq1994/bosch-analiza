#!/usr/bin/env python3
"""Summarize all official Bosch match protocols and compare named scorers."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "match_protocol_audit.json"
PORTAL_PATH = ROOT / "docs" / "assets" / "data.json"
SUMMARY_PATH = ROOT / "data" / "match_protocol_audit_summary.json"
FINDINGS_PATH = ROOT / "data" / "match_protocol_audit_findings.json"
INDEX_PATH = ROOT / "data" / "match_protocol_audit_index.json"
ADMIN_PATH = ROOT / "data" / "goal_evidence.json"


def key(value: object) -> str:
    name = unicodedata.normalize("NFD", str(value or "").lower().replace("ł", "l"))
    name = "".join(character for character in name if unicodedata.category(character) != "Mn")
    words = re.findall(r"[a-z0-9]+", name)
    core = [word for word in words if word not in {"gk", "br", "ii"}]

    return " ".join(sorted(core))


def canonical_goals(record: dict) -> int | None:
    goals = record.get("goals")

    return goals if type(goals) is int and goals >= 0 else None


def match_summary(record: dict) -> dict:
    html = record.get("html") or {}
    direct_players = html.get("bosch_players") or []
    scorers = []

    for player in direct_players:
        goals = canonical_goals(player)
        own_goals = player.get("own_goals") or 0

        if goals is None:
            goals = 0

        if goals <= 0 and own_goals <= 0:
            continue

        scorers.append({
            "name": player["name"],
            "player_id": player.get("player_id"),
            "goals": goals,
            "own_goals": own_goals,
            "goal_minutes": player.get("goal_minutes") or [],
            "profile_url": player.get("profile_url") or "",
        })

    return {
        "id": record["id"],
        "sid": record["sid"],
        "date": record["date"],
        "opponent": record["opponent"],
        "event_url": record["event_url"],
        "score": record["score"],
        "official_team_goals": record["official_goals"],
        "page_status": record["page_status"],
        "protocol_player_goals": html.get("bosch_goals"),
        "protocol_on_field_goals": html.get("bosch_on_field_goals"),
        "opponent_own_goals": html.get("own_goals_by_opponent"),
        "bosch_own_goals": html.get("own_goals_by_bosch"),
        "unreadable_goal_markers": html.get("unreadable_goal_markers") or 0,
        "unreadable_goal_marker_players": [
            {"name": player["name"], "profile_url": player.get("profile_url") or ""}
            for player in direct_players
            if player.get("unreadable_goal_markers")
        ],
        "scorers": sorted(scorers, key=lambda item: (-item["goals"], item["name"])),
    }


def summarize(source: dict, portal: dict, administrative_evidence: dict) -> dict:
    fixtures = [match_summary(row) for row in source["matches"]]
    administrative_by_id = {str(row["event_id"]): row for row in administrative_evidence.get("administrative_adjustments", [])}
    database_players = defaultdict(list)

    for player in portal["players"]:
        database_players[key(player["name"])].append(player)

    recognized_players = defaultdict(lambda: defaultdict(lambda: {"goals": 0, "matches": []}))
    unusual_games = []
    unmatched_people = {}
    series = defaultdict(list)

    for match in fixtures:
        season_id = str(match["sid"])
        series[season_id].append(match)

        for scorer in match["scorers"]:
            if not scorer["goals"]:
                continue

            scorer_key = key(scorer["name"])
            entry = recognized_players[season_id][scorer_key]
            entry["goals"] += scorer["goals"]
            entry["matches"].append({
                "date": match["date"],
                "opponent": match["opponent"],
                "goals": scorer["goals"],
                "url": match["event_url"],
                "minutes": scorer["goal_minutes"],
            })

            if not database_players.get(scorer_key):
                unmatched_people[scorer_key] = scorer["name"]

        on_field_goals = match["protocol_on_field_goals"]
        roster_goals = match["protocol_player_goals"]
        opponent_own_goals = match["opponent_own_goals"] or 0

        administrative = administrative_by_id.get(str(match["id"])) or {}
        administrative_goals = administrative.get("difference", 0)
        match["administrative_goals"] = administrative_goals

        if on_field_goals is None or roster_goals is None:
            unusual_games.append({
                "match": match["id"],
                "season": season_id,
                "date": match["date"],
                "opponent": match["opponent"],
                "source_url": match["event_url"],
                "issue": "missing_match_statistics",
            })
        elif (
            match["unreadable_goal_markers"]
            or on_field_goals != roster_goals
            or match["official_team_goals"] != on_field_goals + opponent_own_goals + administrative_goals
        ):
            unusual_games.append({
                "match": match["id"],
                "season": season_id,
                "date": match["date"],
                "opponent": match["opponent"],
                "source_url": match["event_url"],
                "scoreboard": match["official_team_goals"],
                "player_goals": roster_goals,
                "own_goals_by_opponent": opponent_own_goals,
                "on_field_goals": on_field_goals,
                "administrative_goals": administrative_goals,
                "unreadable_goal_markers": match["unreadable_goal_markers"],
                "unreadable_goal_marker_players": match["unreadable_goal_marker_players"],
                "issue": "goals_disagree_with_match_statistics",
            })

    season_summaries = []
    scorer_discrepancies = []

    for season in portal["seasons"]:
        season_id = str(season["id"])
        matches = series[season_id]
        observations = recognized_players[season_id]
        roster_sum = sum(match["protocol_player_goals"] or 0 for match in matches)
        opposing_own_goals = sum(match["opponent_own_goals"] or 0 for match in matches)
        field_goals = sum(match["protocol_on_field_goals"] or 0 for match in matches)
        verified_count = sum(match["protocol_on_field_goals"] is not None for match in matches)
        roster_count = sum(match["protocol_player_goals"] is not None for match in matches)
        administrative_goals = sum(match.get("administrative_goals", 0) for match in matches)

        season_summaries.append({
            "sid": season_id,
            "name": season["name"],
            "matches": len(matches),
            "matches_with_individual_scorer_table": roster_count,
            "matches_with_field_goal_statistics": verified_count,
            "official_team_goals": season["gf"],
            "player_goals_in_match_protocols": roster_sum,
            "opponent_own_goals_in_protocols": opposing_own_goals,
            "on_field_goals_in_protocols": field_goals,
            "administrative_goals_in_protocols": administrative_goals,
            "sum_protocol_goals_vs_official": roster_sum + opposing_own_goals + administrative_goals - season["gf"],
        })

        for player_name, observed in observations.items():
            registered = database_players.get(player_name) or []
            saved = None
            player_id = None

            if len(registered) == 1:
                player_id = registered[0]["id"]
                row = (registered[0].get("season_stats") or {}).get(season_id) or {}
                saved = row.get("goals") if type(row.get("goals")) is int else None

            delta = observed["goals"] - saved if saved is not None else None

            if delta != 0 or len(registered) != 1:
                scorer_discrepancies.append({
                    "sid": season_id,
                    "player_name": (
                        registered[0]["name"] if len(registered) == 1
                        else unmatched_people.get(player_name, player_name)
                    ),
                    "player_id": player_id,
                    "match_protocol_goals": observed["goals"],
                    "existing_season_goals": saved,
                    "difference": delta,
                    "goal_evidence": observed["matches"],
                    "identity_status": "matched" if len(registered) == 1 else "missing_or_ambiguous_player",
                })

    return {
        "source_audit_created_at": source["created_at"],
        "matches_checked": len(fixtures),
        "all_pages_fetched": all(row["page_status"] == "ok" for row in fixtures),
        "total_matches_with_scorers": sum(match["scorers"] != [] for match in fixtures),
        "season_summaries": season_summaries,
        "unusual_matches": unusual_games,
        "scorer_discrepancies": sorted(
            scorer_discrepancies,
            key=lambda row: (str(row["sid"]), -(row["difference"] or 0), row["player_name"]),
        ),
        "matches": fixtures,
    }


def main() -> None:
    source = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    database = json.loads(PORTAL_PATH.read_text(encoding="utf-8"))
    administrative_evidence = json.loads(ADMIN_PATH.read_text(encoding="utf-8"))
    report = summarize(source, database, administrative_evidence)
    SUMMARY_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    FINDINGS_PATH.write_text(
        json.dumps({key: value for key, value in report.items() if key != "matches"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    INDEX_PATH.write_text(
        json.dumps({"matches": report["matches"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("SCORER_AUDIT_SUMMARY", json.dumps(report["season_summaries"], ensure_ascii=False))
    print("SCORER_AUDIT_UNUSUAL_GAMES", json.dumps(report["unusual_matches"], ensure_ascii=False))
    print("SCORER_AUDIT_DIFFERENCES", json.dumps(report["scorer_discrepancies"], ensure_ascii=False))
    print("SCORER_AUDIT_MATCHES", report["matches_checked"], "SCORERS", report["total_matches_with_scorers"])


if __name__ == "__main__":
    main()
