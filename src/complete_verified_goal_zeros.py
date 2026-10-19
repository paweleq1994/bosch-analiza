"""Infer exact zero goals only when every Bosch match protocol in a season was audited."""
from __future__ import annotations

from collections import defaultdict


def complete_protocol_goal_fields(players: list[dict], matches: list[dict]) -> list[dict]:
    grouped = defaultdict(list)

    for match in matches:
        grouped[str(match["sid"])].append(match)

    verified_seasons = {
        season_id: records
        for season_id, records in grouped.items()
        if records and all((match.get("goal_protocol") or {}).get("verified") for match in records)
    }

    corrections = []

    for player in players:
        player_id = str(player["id"])
        for season_id, stats in (player.get("season_stats") or {}).items():
            if season_id not in verified_seasons or type(stats.get("apps")) is not int or stats["apps"] <= 0:
                continue

            if stats.get("goals") is not None:
                continue

            matches_in_season = verified_seasons[season_id]
            confirmed_goals = sum(
                scorer["goals"]
                for match in matches_in_season
                for scorer in match["goal_protocol"].get("scorers") or []
                if str(scorer["player_id"]) == player_id
            )

            sources = sorted({
                (match.get("goal_protocol") or {}).get("source_url") or match["event_link"]
                for match in matches_in_season
                if any(
                    str(scorer["player_id"]) == player_id
                    for scorer in (match.get("goal_protocol") or {}).get("scorers") or []
                )
                or any(
                    str(entry["player_id"]) == player_id
                    for entry in match.get("player_performance") or []
                )
            })

            stats["goals"] = confirmed_goals
            stats["goals_verified_by_protocol"] = True
            stats["goal_protocol_complete"] = True
            stats["goal_protocol_source_urls"] = sources
            corrections.append({
                "id": player_id,
                "name": player["name"],
                "sid": season_id,
                "goals": confirmed_goals,
                "audited_matches": len(matches_in_season),
                "sources": sources,
            })

    return corrections
