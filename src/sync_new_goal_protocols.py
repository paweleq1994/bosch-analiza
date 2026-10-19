#!/usr/bin/env python3
"""Add only completely reconcilable new PLP goals to the historic match audit.

Existing verified records are immutable. Incomplete source reports remain
pending with explicit reasons rather than being silently counted as zero.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INDEX = DATA / "match_protocol_audit_index.json"
PENDING = DATA / "pending_goal_protocols.json"
BOSCH_ID = "6951"
SCORED_RE = re.compile(r"^\s*(\d+)(?:\s*\(([^)]*)\))?\s*$")
MINUTE_RE = re.compile(r"(\d+(?:\+\d+)?)['′]")
GOAL_KEYS = ("goals", "samobje")


def plp_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "podlaskaliga.pl"
        and parsed.path.startswith("/wydarzenie/")
    )


def parse_goals(value) -> tuple[int, list[str]]:
    if type(value) is int and value >= 0:
        return value, []

    if value is None or str(value).strip() == "":
        return 0, []

    found = SCORED_RE.fullmatch(str(value))
    if not found:
        raise ValueError(f"Unparseable goal value: {value}")

    count = int(found.group(1))
    minutes = MINUTE_RE.findall(found.group(2) or "")
    if len(minutes) > count:
        raise ValueError(f"Goal minute list exceeds goal total: {value}")

    return count, minutes


def get_event(event_id: str) -> dict:
    url = f"https://podlaskaliga.pl/wp-json/sportspress/v2/events/{event_id}"
    with urlopen(Request(url, headers={"User-Agent": "Bosch-Analiza-Audit/1.0"}), timeout=25) as reply:
        return json.load(reply)


def verified_protocol(match: dict, event: dict, profiles: dict) -> dict:
    match_id = str(match["id"])
    event_id = str(match["event_id"])
    teams = [str(team) for team in event.get("teams") or []]
    source = str(event.get("link") or "")

    if (
        str(event.get("id")) != event_id
        or len(teams) != 2
        or BOSCH_ID not in teams
        or not plp_url(source)
        or source.rstrip("/") != str(match.get("event_link") or "").rstrip("/")
        or str(event.get("date") or "")[:10] != match["date"]
    ):
        raise ValueError(f"Source event mismatch for {match_id}")

    other_id = next(team for team in teams if team != BOSCH_ID)
    official_results = event.get("results") or {}
    official_team = (official_results.get(BOSCH_ID) or {}).get("goals")
    official_conceded = (official_results.get(other_id) or {}).get("goals")

    if (
        str(official_team) != str(match["gf"])
        or str(official_conceded) != str(match["ga"])
    ):
        raise ValueError(f"Official score does not match saved result: {match_id}")

    performance = event.get("performance") or {}
    bosch_players = performance.get(BOSCH_ID) or {}
    opposing_players = performance.get(other_id) or {}

    if not isinstance(bosch_players, dict) or not isinstance(opposing_players, dict):
        raise ValueError("Cannot identify official team performance tables")

    goals = 0
    scorers = []
    own_goals = 0
    own_goals_conceded = 0

    for player_id, entry in bosch_players.items():
        if not str(player_id).isdigit() or str(player_id) == "0" or not isinstance(entry, dict):
            continue

        amount, minutes = parse_goals(entry.get("goals"))
        conceded, _ = parse_goals(entry.get("samobje"))
        own_goals_conceded += conceded
        if amount == 0:
            continue

        profile = profiles.get(str(player_id)) or {}
        name = str(profile.get("resolved_name") or "")
        if len(name.split()) < 2:
            raise ValueError(f"Unknown official goal scorer ID {player_id}")
        if len(minutes) != amount:
            raise ValueError(f"Missing official scoring minutes for {player_id}")

        scorers.append({
            "name": name,
            "player_id": str(player_id),
            "goals": amount,
            "own_goals": 0,
            "goal_minutes": minutes,
            "profile_url": profile.get("profile_url") or source,
        })
        goals += amount

    for player_id, entry in opposing_players.items():
        if not str(player_id).isdigit() or str(player_id) == "0" or not isinstance(entry, dict):
            continue
        amount, _ = parse_goals(entry.get("samobje"))
        own_goals += amount

    if own_goals_conceded:
        # A Bosch own goal needs a separate confirmed player attribution.
        raise ValueError("Bosch own goals require direct individual evidence")

    if goals + own_goals != int(match["gf"]):
        raise ValueError(
            f"Goal source does not reconcile: {goals} player + "
            f"{own_goals} opponent own != {match['gf']} official"
        )

    return {
        "id": match_id,
        "sid": str(match["sid"]),
        "date": match["date"],
        "opponent": match["opponent"],
        "event_url": source,
        "score": f"{match['gf']}:{match['ga']}",
        "official_team_goals": int(match["gf"]),
        "page_status": "ok",
        "protocol_player_goals": goals,
        "protocol_on_field_goals": goals,
        "opponent_own_goals": own_goals,
        "bosch_own_goals": 0,
        "unreadable_goal_markers": 0,
        "unreadable_goal_marker_players": [],
        "scorers": scorers,
        "administrative_goals": 0,
        "audit_origin": "plp_event_api_verified",
    }


def extend(
    archive: dict,
    fixtures: list[dict],
    profiles: dict,
    fetch=get_event,
) -> tuple[dict, dict]:
    retained = list(archive.get("matches") or [])
    indexed = {str(row["id"]) for row in retained}

    if len(indexed) != len(retained) or len(retained) < 113:
        raise ValueError("Existing 113-match historical audit is incomplete")

    added = []
    pending = []

    for match in sorted(fixtures, key=lambda item: (item["date"], str(item["id"]))):
        match_id = str(match["id"])
        if match_id in indexed:
            continue

        if not str(match.get("event_id") or "").isdigit() or not plp_url(
            str(match.get("event_link") or "")
        ):
            pending.append({
                "id": match_id,
                "date": match.get("date"),
                "reason": "Missing official numeric event ID or source URL",
                "source_url": match.get("event_link") or "",
            })
            continue

        try:
            item = verified_protocol(match, fetch(str(match["event_id"])), profiles)
            retained.append(item)
            indexed.add(match_id)
            added.append(match_id)
        except Exception as error:
            pending.append({
                "id": match_id,
                "date": match.get("date"),
                "reason": f"{type(error).__name__}: {error}",
                "source_url": match["event_link"],
            })

    return {**archive, "matches": retained}, {
        "newly_verified_match_ids": added,
        "pending": pending,
    }


def save_json(path: Path, payload: dict) -> None:
    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    league = json.loads((DATA / "league_updates.json").read_text(encoding="utf-8"))
    profiles = json.loads((DATA / "player_profile_map.json").read_text(encoding="utf-8"))
    archive = json.loads(INDEX.read_text(encoding="utf-8"))
    merged, audit = extend(archive, league.get("matches") or [], profiles)
    save_json(INDEX, merged)
    save_json(PENDING, audit)
    print(
        f"Goal protocols: {len(merged['matches'])} verified, "
        f"new={len(audit['newly_verified_match_ids'])}, "
        f"pending={len(audit['pending'])}",
        flush=True,
    )
    for item in audit["pending"][:12]:
        print(f"GOAL PENDING {item['id']}: {item['reason']}", flush=True)


if __name__ == "__main__":
    main()
