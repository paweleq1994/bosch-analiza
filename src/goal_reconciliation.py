"""Reconcile verified PLP player evidence and administrative score corrections."""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from player_identity import legacy_player_id, person_key

GOAL_FIELDS = ("apps", "goals", "assists")
STAT_FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
OFFICIAL_HOST = "podlaskaliga.pl"


def verified_source_url(source_url: object, expected_path: str) -> bool:
    source = urlsplit(str(source_url or ""))

    return (
        source.scheme == "https"
        and source.netloc == OFFICIAL_HOST
        and source.path.startswith(expected_path)
    )


def canonical_season_id(season_id: object) -> str:
    return "orlik-2026" if str(season_id) == "148" else str(season_id)


def resolve_identity(row: dict, profiles: dict) -> tuple[str, dict]:
    player_name = str(row.get("name") or "").strip()
    player_id = str(row.get("player_id") or "")

    if not player_name or len(person_key(player_name).split()) < 2:
        raise ValueError(f"Invalid verified player name: {player_name!r}")

    if player_id:
        profile = profiles.get(player_id) or {}

        if not player_id.isdigit():
            raise ValueError(f"Invalid PLP player ID: {player_id}")

        if profile.get("resolved_name") and person_key(profile["resolved_name"]) != person_key(player_name):
            raise ValueError(f"PLP player ID belongs to another person: {player_id}")

        return player_id, profile

    matched_profiles = [
        (str(profile_id), profile)
        for profile_id, profile in profiles.items()
        if str(profile_id).isdigit()
        and person_key(profile.get("resolved_name")) == person_key(player_name)
    ]

    if len(matched_profiles) > 1:
        raise ValueError(f"Ambiguous PLP player identity: {player_name}")

    if matched_profiles:
        return matched_profiles[0]

    return legacy_player_id(player_name), {}


def validate_goal_evidence(evidence: dict, seasons: list[dict], matches: list[dict]) -> None:
    valid_seasons = {str(season["id"]) for season in seasons}
    matches_by_event = {
        str(match.get("event_id") or match.get("id")): match
        for match in matches
    }
    recorded_players = set()
    recorded_events = set()

    for row in evidence.get("players") or []:
        name = str(row.get("name") or "")
        season_id = canonical_season_id(row.get("season_id"))
        minimum = row.get("minimum")

        if season_id not in valid_seasons or type(minimum) is not bool:
            raise ValueError(f"Invalid sourced scorer season or coverage: {name}")

        if not verified_source_url(
            row.get("source_url"),
            "/wydarzenie/" if minimum else "/zawodnik/",
        ):
            raise ValueError(f"Unverified scorer evidence URL: {name}")

        if type(row.get("goals")) is not int or row["goals"] <= 0:
            raise ValueError(f"Invalid confirmed goal count: {name}")

        if minimum:
            event_id = str(row.get("match_event_id") or "")
            match = matches_by_event.get(event_id)

            if match is None or str(match["sid"]) != season_id:
                raise ValueError(f"Goal evidence is not linked to a verified Bosch fixture: {name}")

            if row.get("apps") is not None or row.get("assists") is not None:
                raise ValueError(f"One match cannot certify entire season totals: {name}")
        else:
            if type(row.get("apps")) is not int or row["apps"] <= 0:
                raise ValueError(f"Full-season evidence requires verified appearances: {name}")

            if type(row.get("assists")) is not int or row["assists"] < 0:
                raise ValueError(f"Full-season evidence requires verified assists: {name}")

        player_key = str(row.get("player_id") or "") or person_key(name)
        unique_key = (player_key, season_id)

        if unique_key in recorded_players:
            raise ValueError(f"Duplicate scorer evidence: {name} in {season_id}")

        recorded_players.add(unique_key)

    for row in evidence.get("administrative_adjustments") or []:
        event_id = str(row.get("event_id") or "")
        season_id = canonical_season_id(row.get("season_id"))
        fixture = matches_by_event.get(event_id)

        if event_id in recorded_events or fixture is None:
            raise ValueError(f"Duplicate or unknown administrative event: {event_id}")

        if season_id not in valid_seasons or str(fixture["sid"]) != season_id:
            raise ValueError(f"Administrative event belongs to a different season: {event_id}")

        if (
            fixture.get("date") != row.get("date")
            or fixture.get("opponent") != row.get("opponent")
            or fixture.get("gf") != row.get("awarded_goals")
        ):
            raise ValueError(f"Administrative score is inconsistent with fixtures: {event_id}")

        if not verified_source_url(row.get("source_url"), "/wydarzenie/"):
            raise ValueError(f"Administrative score lacks official source: {event_id}")

        awarded_goals = row.get("awarded_goals")
        on_field_goals = row.get("on_field_goals")
        difference = row.get("difference")

        if not all(type(value) is int for value in (awarded_goals, on_field_goals, difference)):
            raise ValueError(f"Administrative goals must be integers: {event_id}")

        if difference <= 0 or awarded_goals - on_field_goals != difference:
            raise ValueError(f"Administrative correction amount is inconsistent: {event_id}")

        recorded_events.add(event_id)


def add_verified_players(
    players: list[dict],
    profiles: dict,
    evidence: dict,
    season_details: dict,
) -> None:
    player_by_id = {str(player["id"]): player for player in players}
    player_by_name = {person_key(player["name"]): player for player in players}

    for row in evidence.get("players") or []:
        player_id, profile = resolve_identity(row, profiles)
        person = person_key(row["name"])
        by_id = player_by_id.get(player_id)
        by_name = player_by_name.get(person)

        if by_id is not None and by_name is not None and by_id is not by_name:
            raise ValueError(f"Evidence matches conflicting player records: {row['name']}")

        player = by_id or by_name

        if player is None:
            player = {
                "id": player_id,
                "name": str(profile.get("resolved_name") or row["name"]),
                "profile_url": (
                    profile.get("profile_url")
                    if verified_source_url(profile.get("profile_url"), "/zawodnik/")
                    else row["source_url"]
                    if not row["minimum"]
                    else ""
                ),
                "status": "PLP — potwierdzone dane",
                "apps": row["apps"],
                "goals": row["goals"],
                "assists": row["assists"],
                "motm": None,
                "yellow": None,
                "red": None,
                "peak": "",
                "seasons_label": "",
                "orlik2026": None,
                "hala2526": None,
            }
            players.append(player)
            player_by_id[player_id] = player
            player_by_name[person] = player
        elif person_key(player["name"]) != person:
            raise ValueError(f"Scorer identity is inconsistent: {row['name']}")

        alias = legacy_player_id(row["name"])

        if alias != player["id"] and alias not in player.setdefault("aliases", []):
            player["aliases"].append(alias)

        season_id = canonical_season_id(row["season_id"])
        stored_season_id = "148" if season_id == "orlik-2026" else season_id
        previous = (season_details.get(str(player["id"])) or {}).get(stored_season_id) or {}
        source_stats = {
            "apps": row["apps"],
            "goals": row["goals"],
            "assists": row["assists"],
            "motm": None,
            "yellow": None,
            "red": None,
            "origin": row["source_type"],
        }

        if row["minimum"]:
            player["stats_minimum"] = True
            player["goal_evidence_source"] = row["source_url"]

        if previous:
            for field in GOAL_FIELDS:
                verified_value = previous.get(field)
                expected_value = source_stats.get(field)

                if (
                    type(verified_value) is int
                    and type(expected_value) is int
                    and verified_value < expected_value
                ):
                    raise ValueError(
                        f"Cached PLP figures are below confirmed goal evidence: {player['name']} {field}"
                    )

            continue

        if row["minimum"]:
            player.setdefault("season_stats", {})[season_id] = source_stats
            player["stats_minimum"] = True
        else:
            season_details.setdefault(str(player["id"]), {})[stored_season_id] = source_stats

        if not row["minimum"]:
            continue

        if type(player.get("goals")) is not int or player["goals"] < row["goals"]:
            player["goals"] = row["goals"]

        if not player.get("status"):
            player["status"] = "PLP — potwierdzony gol"

        player["goal_evidence_source"] = row["source_url"]


def administrative_goals_by_season(evidence: dict) -> dict[str, dict]:
    result = defaultdict(lambda: {"goals": 0, "events": []})

    for adjustment in evidence.get("administrative_adjustments") or []:
        season_id = canonical_season_id(adjustment["season_id"])
        result[season_id]["goals"] += adjustment["difference"]
        result[season_id]["events"].append({
            "match_id": str(adjustment["event_id"]),
            "opponent": adjustment["opponent"],
            "source_url": adjustment["source_url"],
            "reason": adjustment["reason"],
            "goals": adjustment["difference"],
        })

    return dict(result)
