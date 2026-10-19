"""Promote only source-verified event-level PLP player identities to Bosch profiles."""
from __future__ import annotations

from collections import defaultdict

from player_identity import legacy_player_id, person_key

FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
EVENT_FIELDS = {
    "apps": "appearance",
    "assists": "assists",
    "motm": "motm",
    "yellow": "yellow",
    "red": "red",
}


def attach_verified_identities(players: list[dict], snapshot: dict, evidence: dict) -> dict:
    match_ids = {
        str(row["player_id"])
        for match in evidence.get("matches") or []
        for row in match.get("players") or []
    }
    new_profiles = []
    promoted_aliases = []
    suspicious_duplicates = []

    for player_id, record in sorted((snapshot.get("players") or {}).items()):
        if (
            not player_id.isdigit()
            or player_id not in match_ids
            or not record.get("verified")
            or not record.get("evidence_urls")
        ):
            continue

        name = str(record["name"]).strip()
        player_name_key = person_key(name)
        public_url = str(record.get("public_url") or "")
        matches = [item for item in players if str(item["id"]) == player_id]

        if len(matches) > 1:
            raise ValueError(f"Duplicate numeric player ID {player_id}")

        if matches:
            player = matches[0]
            if person_key(player["name"]) != player_name_key:
                raise ValueError(f"Conflicting verified match identity {player_id}: {player['name']} != {name}")
        else:
            synthetic = [
                item for item in players
                if str(item["id"]).startswith("new-")
                and person_key(item["name"]) == player_name_key
            ]

            if len(synthetic) > 1:
                raise ValueError(f"Ambiguous synthetic player identity {name}")

            if synthetic:
                player = synthetic[0]
                previous_id = str(player["id"])
                player["id"] = player_id
                player.setdefault("aliases", []).append(previous_id)
                promoted_aliases.append({"old_id": previous_id, "id": player_id})
            else:
                competing = [
                    item for item in players
                    if str(item["id"]).isdigit()
                    and person_key(item["name"]) == player_name_key
                ]
                if competing:
                    suspicious_duplicates.append({
                        "id": player_id,
                        "name": name,
                        "existing_ids": [str(item["id"]) for item in competing],
                    })

                player = {
                    "id": player_id,
                    "name": name,
                    "profile_url": "",
                    "status": "PLP — protokoły meczowe",
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
                    "season_stats": {},
                    "stats_minimum": True,
                    "match_only_profile": True,
                }
                player["aliases"] = [legacy_player_id(name)]
                players.append(player)
                new_profiles.append(player_id)

        if public_url and not player.get("profile_url"):
            player["profile_url"] = public_url

        player["verified_identity_source"] = {
            "type": record["source"],
            "evidence_urls": list(record["evidence_urls"]),
            "public_url": public_url,
        }

    return {
        "created_ids": new_profiles,
        "promoted_aliases": promoted_aliases,
        "possible_duplicate_identities": suspicious_duplicates,
    }


def minimum_match_totals(players: list[dict], evidence: dict) -> None:
    totals = defaultdict(lambda: defaultdict(int))
    unknown = defaultdict(set)

    for match in evidence.get("matches") or []:
        for entry in match.get("players") or []:
            player_id = str(entry["player_id"])
            for field, source in EVENT_FIELDS.items():
                value = entry.get(source)
                if type(value) is int and value >= 0:
                    totals[player_id][field] += value
                else:
                    unknown[player_id].add(field)

    for player in players:
        if not player.get("match_only_profile"):
            continue

        player_id = str(player["id"])
        for field in EVENT_FIELDS:
            if field not in unknown[player_id]:
                player[field] = totals[player_id][field]

        # Goals always come from the separately reconciled official scorer
        # protocols. Never overwrite them with raw performance totals.
        player["stats_minimum"] = True
        player["stats_source"] = "Oficjalne protokoły PLP — udokumentowane minimum"

