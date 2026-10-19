"""Integrate verified match protocols into Bosnia's historical goals and player pages."""
from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from player_identity import legacy_player_id, person_key


def canonical_player_id(identifier: object, aliases: dict[str, str]) -> str:
    return aliases.get(str(identifier), str(identifier))


def official_plp_link(value: object) -> bool:
    parts = urlsplit(str(value or ""))

    return parts.scheme == "https" and parts.hostname == "podlaskaliga.pl"


def scorer_player(
    event: dict,
    players: list[dict],
    profile_links: dict[str, str],
    aliases: dict[str, str],
) -> dict:
    name = str(event.get("name") or "").strip()
    source_url = str(event.get("profile_url") or "")

    if len(person_key(name).split()) != 2 or not official_plp_link(source_url):
        raise ValueError(f"Untrusted scorer identity: {name}")

    by_id = {str(player["id"]): player for player in players}
    source_id = str(event.get("player_id") or "")
    candidate_id = canonical_player_id(source_id, aliases) if source_id else ""
    matched_by_id = by_id.get(candidate_id)
    linked_id = profile_links.get(source_url.rstrip("/"))
    linked_player = by_id.get(canonical_player_id(linked_id, aliases)) if linked_id else None
    matching_names = [
        player for player in players
        if person_key(player["name"]) == person_key(name)
    ]

    if len(matching_names) > 1:
        raise ValueError(f"Scorer name still has multiple player profiles: {name}")

    named_player = matching_names[0] if matching_names else None
    resolved = matched_by_id or linked_player or named_player

    if resolved is not None:
        if person_key(resolved["name"]) != person_key(name):
            raise ValueError(f"Scorer source identifies a different player: {name}")

        if any(player is not None and player is not resolved for player in (matched_by_id, linked_player, named_player)):
            raise ValueError(f"Conflicting PLP identity matches for {name}")

        return resolved

    identifier = source_id if source_id.isdigit() else legacy_player_id(name)

    if identifier in by_id:
        raise ValueError(f"Unresolved ID collision: {identifier}")

    new_player = {
        "id": identifier,
        "name": name,
        "profile_url": source_url,
        "status": "PLP — potwierdzone protokoły",
        "apps": None,
        "goals": None,
        "assists": None,
        "motm": None,
        "yellow": None,
        "red": None,
        "peak": "",
        "seasons_label": "",
        "orlik2026": None,
        "hala2526": None,
        "career_totals": None,
        "bosch_totals": None,
        "stats_source": "Protokoły meczowe PLP — potwierdzone minimum",
        "stats_minimum": True,
        "season_stats": {},
    }
    players.append(new_player)
    profile_links[source_url.rstrip("/")] = identifier

    return new_player


def enrich_from_protocols(
    matches: list[dict],
    players: list[dict],
    official_profiles: dict,
    protocol_index: dict,
    aliases: dict[str, str],
    own_goal_evidence: dict | None = None,
    minimum_matches: int = 113,
) -> dict:
    fixture_map = {str(match["id"]): match for match in matches}
    protocol_rows = protocol_index.get("matches") or []
    unique_source_ids = {str(row.get("id")) for row in protocol_rows}
    source_links: dict[str, str] = {}

    for player_id, profile in official_profiles.items():
        link = str(profile.get("profile_url") or "")

        if official_plp_link(link):
            source_links[link.rstrip("/")] = canonical_player_id(player_id, aliases)

    for player in players:
        for link in [player.get("profile_url")] + (player.get("alternate_profile_urls") or []):
            if link and official_plp_link(link):
                source_links[str(link).rstrip("/")] = str(player["id"])

    if len(protocol_rows) < minimum_matches or len(unique_source_ids) != len(protocol_rows):
        raise ValueError("Historical PLP match audit is incomplete or contains duplicate matches")

    by_player_season = defaultdict(int)
    by_player_match = defaultdict(list)
    by_season = defaultdict(lambda: {"player_goals": 0, "opponent_own_goals": 0, "administrative_goals": 0})
    verified_ids = set()
    goals_with_unknown_minute = []
    own_goal_events = defaultdict(list)
    known_own_scorers = {str(player["id"]): player for player in players}
    claimed_own_events = set()

    for event in (own_goal_evidence or {}).get("events") or []:
        match_id = str(event.get("match_id") or "")
        player_id = canonical_player_id(event.get("player_id"), aliases)

        if match_id in claimed_own_events or player_id not in known_own_scorers:
            raise ValueError(f"Invalid or duplicated Bosch own-goal attribution: {match_id}")

        if type(event.get("goals")) is not int or event["goals"] <= 0:
            raise ValueError(f"Invalid own-goal count in {match_id}")

        claimed_own_events.add(match_id)
        own_goal_events[match_id].append({
            "player_id": player_id,
            "name": known_own_scorers[player_id]["name"],
            "goals": event["goals"],
        })

    for record in protocol_rows:
        match_id = str(record.get("id") or "")
        match = fixture_map.get(match_id)

        if match is None:
            raise ValueError(f"Missing Bosch fixture linked from audited PLP event: {match_id}")

        event_url = str(record.get("event_url") or "")
        match_url = str(match.get("event_link") or "")

        if (
            not official_plp_link(event_url)
            or record.get("page_status") != "ok"
            or match_url.rstrip("/") != event_url.rstrip("/")
            or str(match["sid"]) != str(record["sid"])
            or match["date"] != record["date"]
            or int(match["gf"]) != record["official_team_goals"]
        ):
            raise ValueError(f"Match protocol differs from the official fixture: {match_id}")

        verified_ids.add(match_id)
        scorers = []
        scored_goals = 0

        for row in record.get("scorers") or []:
            amount = row.get("goals")

            if type(amount) is not int or amount <= 0:
                continue

            player = scorer_player(row, players, source_links, aliases)
            player_id = str(player["id"])
            minutes = [str(minute) for minute in row.get("goal_minutes") or []]

            if len(minutes) != amount:
                raise ValueError(f"Scored goals disagree with minute markers for {match_id}: {player['name']}")

            item = {
                "player_id": player_id,
                "name": player["name"],
                "goals": amount,
                "minutes": minutes,
                "source_url": event_url,
                "minute_uncertain": False,
            }
            scorers.append(item)
            scored_goals += amount

        missing_goal_markers = record.get("unreadable_goal_marker_players") or []
        unreadable_count = record.get("unreadable_goal_markers") or 0

        if unreadable_count:
            if (
                unreadable_count != 1
                or len(missing_goal_markers) != 1
                or scored_goals + 1 != int(record["protocol_on_field_goals"])
            ):
                raise ValueError(f"Cannot identify ambiguous scorer marker in match {match_id}")

            candidate = {
                "name": missing_goal_markers[0]["name"],
                "profile_url": missing_goal_markers[0]["profile_url"],
            }
            player = scorer_player(candidate, players, source_links, aliases)
            scorers.append({
                "player_id": str(player["id"]),
                "name": player["name"],
                "goals": 1,
                "minutes": [],
                "source_url": event_url,
                "minute_uncertain": True,
            })
            scored_goals += 1
            goals_with_unknown_minute.append({"id": match_id, "player_id": player["id"], "source_url": event_url})

        own_goals = record.get("opponent_own_goals") or 0
        administrative_goals = record.get("administrative_goals") or 0

        if not all(type(value) is int and value >= 0 for value in (own_goals, administrative_goals)):
            raise ValueError(f"Invalid opponent own-goal or administrative count: {match_id}")

        own_goals_conceded_scorers = own_goal_events.get(match_id) or []
        recorded_own_goals_conceded = sum(item["goals"] for item in own_goals_conceded_scorers)

        if recorded_own_goals_conceded != int(record.get("bosch_own_goals") or 0):
            raise ValueError(f"Unverified individual own-goal attribution in {match_id}")

        if scored_goals + own_goals + administrative_goals != int(match["gf"]):
            raise ValueError(
                f"Official score mismatch in {match_id}: "
                f"{scored_goals} + {own_goals} + {administrative_goals} != {match['gf']}"
            )

        scorers.sort(key=lambda row: (min((int(minute.split("+")[0]) for minute in row["minutes"]), default=999), row["name"]))
        match["goal_protocol"] = {
            "source_url": event_url,
            "scorers": scorers,
            "player_goals": scored_goals,
            "own_goals": own_goals,
            "administrative_goals": administrative_goals,
            "own_goals_conceded": recorded_own_goals_conceded,
            "own_goals_conceded_scorers": own_goals_conceded_scorers,
            "unverified_goals": 0,
            "verified": True,
            "minute_uncertainties": unreadable_count,
        }
        season_id = str(match["sid"])
        totals = by_season[season_id]
        totals["player_goals"] += scored_goals
        totals["opponent_own_goals"] += own_goals
        totals["administrative_goals"] += administrative_goals

        for scorer in scorers:
            key = (scorer["player_id"], season_id)
            by_player_season[key] += scorer["goals"]
            by_player_match[scorer["player_id"]].append({
                "match_id": match_id,
                "date": match["date"],
                "sid": season_id,
                "opponent": match["opponent"],
                "score": f"{match['gf']}:{match['ga']}",
                "goals": scorer["goals"],
                "minutes": scorer["minutes"],
                "source_url": event_url,
                "minute_uncertain": scorer["minute_uncertain"],
            })

    if len(verified_ids) < minimum_matches:
        raise ValueError(f"Expected {minimum_matches} verified Bosch match protocols, found {len(verified_ids)}")

    for player in players:
        player_id = str(player["id"])
        logs = sorted(
            by_player_match.get(player_id) or [],
            key=lambda row: (row["date"], row["match_id"]),
            reverse=True,
        )
        player["goal_matches"] = logs
        own_goal_history = [
            {
                "match_id": match["id"],
                "date": match["date"],
                "opponent": match["opponent"],
                "source_url": match["goal_protocol"]["source_url"],
                "goals": scorer["goals"],
            }
            for match in matches
            for scorer in (match.get("goal_protocol") or {}).get("own_goals_conceded_scorers") or []
            if scorer["player_id"] == player_id
        ]
        player["own_goal_matches"] = sorted(own_goal_history, key=lambda row: row["date"], reverse=True)
        player["own_goals_conceded"] = sum(row["goals"] for row in own_goal_history)
        player["protocol_goal_total"] = sum(row["goals"] for row in logs)
        season_stats = player.setdefault("season_stats", {})

        for (scorer_id, season_id), known_goals in by_player_season.items():
            if scorer_id != player_id:
                continue

            old_stats = season_stats.get(season_id) or {}
            old_goals = old_stats.get("goals")

            if type(old_goals) is int and old_goals > known_goals:
                raise ValueError(
                    f"Official season has more goals than every historical match: "
                    f"{player['name']} {season_id}: {old_goals} > {known_goals}"
                )

            origin = old_stats.get("origin") or "plp_match_protocols"
            season_stats[season_id] = {
                **old_stats,
                "goals": known_goals,
                "origin": origin,
                "goals_verified_by_protocol": True,
            }

            if old_goals is None or old_goals < known_goals:
                season_stats[season_id]["origin"] = "plp_match_protocols"

            if season_id == "146" and player.get("hala2526"):
                player["hala2526"] = dict(season_stats[season_id])

            if season_id == "orlik-2026" and player.get("orlik2026"):
                player["orlik2026"] = dict(season_stats[season_id])

        lifetime_goals = player.get("goals")

        if type(lifetime_goals) is not int or lifetime_goals < player["protocol_goal_total"]:
            player["goals"] = player["protocol_goal_total"]
            player["stats_source"] = "PLP — direct match protocols"
            player["stats_minimum"] = True

    return {
        "audited_matches": len(verified_ids),
        "seasons": dict(by_season),
        "goals_with_unknown_minute": goals_with_unknown_minute,
        "total_protocol_goals": sum(row["player_goals"] for row in by_season.values()),
        "total_own_goals": sum(row["opponent_own_goals"] for row in by_season.values()),
        "total_own_goals_conceded": sum(
            scorer["goals"]
            for match in matches
            for scorer in (match.get("goal_protocol") or {}).get("own_goals_conceded_scorers") or []
        ),
        "total_administrative_goals": sum(row["administrative_goals"] for row in by_season.values()),
    }
