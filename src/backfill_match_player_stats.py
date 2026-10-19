"""Fill otherwise unknown Bosch season statistics using source-linked match performance.

Never overwrite verified Sportspress aggregates and never infer a missing performance
from a goal scorer table. Each accepted stat has complete 113-fixture evidence.
"""
from __future__ import annotations

from collections import defaultdict

COUNT_FIELDS = ("apps", "assists", "motm", "yellow", "red")
MATCH_FIELDS = {"apps": "appearance", "assists": "assists", "motm": "motm", "yellow": "yellow", "red": "red"}


def backfill_seasons(
    players: list[dict],
    matches: list[dict],
    match_evidence: dict,
) -> dict:
    expected = {str(match["id"]): match for match in matches}
    observed = {str(match["match_id"]): match for match in match_evidence.get("matches") or []}

    if len(expected) < 113 or len(observed) < 113 or not set(observed).issubset(expected):
        raise ValueError("Cannot backfill partial PLP event archive")

    roster = {str(player["id"]): player for player in players}
    totals = defaultdict(lambda: defaultdict(int))
    missing = set()
    unmatched = set()
    source_links = defaultdict(set)

    for match_id, evidence in observed.items():
        fixture = expected[match_id]

        if (
            str(evidence["season_id"]) != str(fixture["sid"])
            or str(evidence["date"]) != str(fixture["date"])
            or str(evidence["source_url"]).rstrip("/") != str(fixture["event_link"]).rstrip("/")
        ):
            raise ValueError(f"PLP event evidence mismatch: {match_id}")

        known_players = set()

        for entry in evidence["players"]:
            player_id = str(entry["player_id"])

            if player_id in known_players:
                raise ValueError(f"Repeated match appearance: {match_id} / {player_id}")

            known_players.add(player_id)

            if player_id not in roster:
                unmatched.add(player_id)
                continue

            key = (player_id, str(fixture["sid"]))
            source_links[key].add(evidence["source_url"])

            for field, source_key in MATCH_FIELDS.items():
                value = entry.get(source_key)

                if type(value) is not int or value < 0:
                    missing.add((*key, field))
                else:
                    totals[key][field] += value

    written = []
    conflicts = []

    for (player_id, season_id), reconstructed in sorted(totals.items()):
        player = roster[player_id]
        season_stats = player.setdefault("season_stats", {})
        current = dict(season_stats.get(season_id) or {})

        for field in COUNT_FIELDS:
            if (player_id, season_id, field) in missing:
                continue

            recovered = reconstructed[field]
            previous = current.get(field)

            if type(previous) is int and previous >= recovered:
                if previous > recovered:
                    conflicts.append({
                        "player_id": player_id,
                        "season_id": season_id,
                        "field": field,
                        "stored": previous,
                        "match_evidence": recovered,
                        "reason": "season_total_exceeds_known_match_performance",
                    })
                continue

            full_total = player.get(field)

            if type(full_total) is int:
                other_verified = sum(
                    value[field]
                    for sid, value in season_stats.items()
                    if str(sid) != season_id and type(value.get(field)) is int
                )

                if other_verified + recovered > full_total:
                    conflicts.append({
                        "player_id": player_id,
                        "season_id": season_id,
                        "field": field,
                        "stored": None,
                        "match_evidence": recovered,
                        "reason": "larger_than_verified_player_total",
                    })
                    continue

            current[field] = recovered
            if type(previous) is int and previous < recovered:
                current.setdefault("corrected_from_lower_season_values", {})[field] = previous
            written.append({
                "player_id": player_id,
                "season_id": season_id,
                "field": field,
                "value": recovered,
                "source_urls": sorted(source_links[(player_id, season_id)]),
            })

        if any(row["player_id"] == player_id and row["season_id"] == season_id for row in written):
            current["match_performance_verified"] = True
            current["match_performance_sources"] = sorted(source_links[(player_id, season_id)])
            current.setdefault("origin", "plp_match_performance")
            season_stats[season_id] = current

    return {
        "verified_matches": len(observed),
        "filled": written,
        "conflicts": conflicts,
        "unmatched_player_ids": sorted(unmatched),
    }
