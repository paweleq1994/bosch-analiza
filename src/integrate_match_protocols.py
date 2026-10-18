"""Bring source-linked PLP match protocols into the public Bosch portal."""
from __future__ import annotations

from collections import defaultdict

from player_identity import legacy_player_id, person_key

BOSCH = "Bosch Service Tech-Car"
CONFIRMED_SEASON_ADDITIONS = {
    ("7282", "120"): {"goals": 1, "match_id": "7851"},
    ("7285", "139"): {"goals": 2, "match_ids": ["10157", "10254"]},
}
OWN_GOAL_MATCHES = {"7788", "8366", "12617"}
UNCLEAR_MATCH = "9755"


def match_id(value: object) -> str:
    return str(value or "")


def integrate_match_protocols(players: list[dict], matches: list[dict], audit: dict) -> dict:
    by_match = {match_id(match["id"]): match for match in matches}
    protocol_rows = audit.get("matches") or []

    if len(by_match) != 113 or len(protocol_rows) != 113:
        raise ValueError("Historical PLP protocol audit requires all 113 fixtures")

    seen = set()
    by_name = defaultdict(list)

    for player in players:
        by_name[person_key(player["name"])].append(player)

    player_match_goals = defaultdict(list)
    historical_scorers = defaultdict(list)

    for record in protocol_rows:
        identifier = match_id(record["id"])
        match = by_match.get(identifier)

        if match is None or identifier in seen or record.get("page_status") != "ok":
            raise ValueError(f"Unverified or duplicate PLP match protocol: {identifier}")

        if str(record["sid"]) != str(match["sid"]) or record["official_team_goals"] != match["gf"]:
            raise ValueError(f"PLP protocol mismatch for fixture {identifier}")

        if str(record.get("event_url") or "") != str(match.get("event_link") or ""):
            raise ValueError(f"PLP match link mismatch: {identifier}")

        seen.add(identifier)
        confirmed_scorers = []

        for scorer in record.get("scorers") or []:
            name = str(scorer["name"])
            candidates = by_name.get(person_key(name)) or []
            resolved = candidates[0] if len(candidates) == 1 else None
            goals = int(scorer.get("goals") or 0)
            minutes = scorer.get("goal_minutes") or []

            if goals <= 0 or len(minutes) > goals:
                raise ValueError(f"Inconsistent scorer evidence: {identifier} / {name}")

            event = {
                "name": name,
                "player_id": resolved["id"] if resolved else None,
                "goals": goals,
                "minutes": minutes,
                "minutes_complete": len(minutes) == goals,
                "profile_url": scorer.get("profile_url") or "",
            }
            confirmed_scorers.append(event)
            historical_scorers[(str(match["sid"]), person_key(name))].append((identifier, goals))

            if resolved:
                player_match_goals[resolved["id"]].append({
                    "match_id": identifier,
                    "date": match["date"],
                    "sid": str(match["sid"]),
                    "opponent": match["opponent"],
                    "goals": goals,
                    "minutes": minutes,
                    "source_url": record["event_url"],
                })

        own_goals = int(record.get("opponent_own_goals") or 0)
        administrative = int(record.get("administrative_goals") or 0)
        protocol_goals = record.get("protocol_player_goals")
        ambiguous = int(record.get("unreadable_goal_markers") or 0) > 0

        if own_goals and identifier not in OWN_GOAL_MATCHES:
            raise ValueError(f"Unexpected opponent own goal: {identifier}")

        if protocol_goals is not None and protocol_goals != sum(scorer["goals"] for scorer in confirmed_scorers):
            raise ValueError(f"PLP match scorer total mismatch: {identifier}")

        if not ambiguous and protocol_goals is not None and protocol_goals + own_goals + administrative != match["gf"]:
            raise ValueError(f"Unreconciled Bosch match score: {identifier}")

        match["protocol"] = {
            "scorers": confirmed_scorers,
            "opponent_own_goals": own_goals,
            "administrative_goals": administrative,
            "source_url": record["event_url"],
            "complete": not ambiguous,
            "unreadable_goal_markers": int(record.get("unreadable_goal_markers") or 0),
        }

    if seen != set(by_match):
        raise ValueError("Protocol coverage missing Bosch fixtures")

    for (player_id, season_id), correction in CONFIRMED_SEASON_ADDITIONS.items():
        player = next((item for item in players if str(item["id"]) == player_id), None)

        if player is None:
            raise ValueError(f"Missing documented Bosch scorer {player_id}")

        expected_ids = correction.get("match_ids") or [correction["match_id"]]
        observed = historical_scorers.get((season_id, person_key(player["name"])), [])

        if sum(goals for identifier, goals in observed if identifier in expected_ids) != correction["goals"]:
            raise ValueError(f"Missing original goal evidence for {player['name']}")

        existing_stats = player.setdefault("season_stats", {}).get(season_id) or {}

        if isinstance(existing_stats.get("goals"), int):
            if existing_stats["goals"] != correction["goals"]:
                raise ValueError(f"Conflicting season goal totals for {player['name']}")
        else:
            player["season_stats"][season_id] = {
                **existing_stats,
                "goals": correction["goals"],
                "origin": "plp_match_protocols",
            }

    kakareko = historical_scorers.get(("144", person_key("Kakareko Kamil")), [])

    if kakareko != [("12165", 1)]:
        raise ValueError("Kamil Kakareko source goal requires direct PLP verification")

    existing_kakareko = by_name.get(person_key("Kakareko Kamil")) or []

    if not existing_kakareko:
        new_player = {
            "id": legacy_player_id("Kakareko Kamil"),
            "name": "Kakareko Kamil",
            "profile_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
            "status": "Archiwum PLP — potwierdzony występ",
            "apps": None,
            "goals": 1,
            "assists": None,
            "motm": None,
            "yellow": None,
            "red": None,
            "peak": "",
            "seasons_label": "",
            "orlik2026": None,
            "hala2526": None,
            "stats_minimum": True,
            "bosch_totals": None,
            "career_totals": None,
            "season_stats": {"144": {"apps": None, "goals": 1, "assists": None, "origin": "plp_match_protocols"}},
            "stats_source": "Oficjalny protokół PLP — potwierdzone minimum",
        }
        players.append(new_player)
        player_match_goals[new_player["id"]].append({
            "match_id": "12165",
            "date": by_match["12165"]["date"],
            "sid": "144",
            "opponent": by_match["12165"]["opponent"],
            "goals": 1,
            "minutes": ["22"],
            "source_url": by_match["12165"]["event_link"],
        })
        by_match["12165"]["protocol"]["scorers"][0]["player_id"] = new_player["id"]

    for player in players:
        player["protocol_goals"] = sorted(
            player_match_goals.get(player["id"], []),
            key=lambda row: (row["date"], row["match_id"]),
            reverse=True,
        )

    return {
        "audited_matches": len(seen),
        "opponent_own_goals": sum(match["protocol"]["opponent_own_goals"] for match in matches),
        "administrative_goals": sum(match["protocol"]["administrative_goals"] for match in matches),
        "matches_with_unreadable_markers": [
            match["id"] for match in matches if not match["protocol"]["complete"]
        ],
    }
