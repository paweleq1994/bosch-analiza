"""Reconcile archived Bosch player seasons without inventing missing statistics."""
from __future__ import annotations

import re
import unicodedata

BOSCH_TEAM_ID = "6951"
BOSCH_TEAM_NAME = "Bosch Service Tech-Car"
STAT_FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
PEAK_PATTERN = re.compile(
    r"^\s*(?P<season>[^:]+):\s*(?P<goals>\d+)G\s*\+\s*(?P<assists>\d+)A\s*$"
)


def season_name_key(name: object) -> str:
    normalized_name = unicodedata.normalize("NFD", str(name or "").lower())
    ascii_name = "".join(
        character for character in normalized_name
        if unicodedata.category(character) != "Mn"
    )

    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()


def nonnegative_number(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value

    return None


def archived_bosch_seasons(promotions: dict, player_ids: set[str]) -> dict[str, dict[str, dict]]:
    by_player: dict[str, dict[str, dict]] = {}

    for row in promotions.get("player_rows") or []:
        player_id = str(row.get("player_id") or "")
        season_id = str(row.get("sid") or "")

        if player_id not in player_ids:
            continue

        if str(row.get("team_id") or "") != BOSCH_TEAM_ID:
            continue

        if season_name_key(row.get("team_name")) != season_name_key(BOSCH_TEAM_NAME):
            continue

        if not season_id.isdigit():
            continue

        appearances = nonnegative_number(row.get("apps"))
        goals = nonnegative_number(row.get("goals"))
        assists = nonnegative_number(row.get("assists"))

        if appearances is None or appearances <= 0 or goals is None or assists is None:
            continue

        stats = {
            "apps": appearances,
            "goals": goals,
            "assists": assists,
            "motm": nonnegative_number(row.get("motm")),
            "yellow": nonnegative_number(row.get("yellow")),
            "red": nonnegative_number(row.get("red")),
            "origin": "plp_archived_season",
        }
        seasons = by_player.setdefault(player_id, {})
        previous = seasons.get(season_id)

        if previous is not None and previous != stats:
            raise ValueError(f"Conflicting PLP archived season for player {player_id}, season {season_id}")

        seasons[season_id] = stats

    return by_player


def apply_archived_seasons(
    player: dict,
    verified_archive: dict[str, dict],
    seasons: list[dict],
) -> None:
    season_stats = player.setdefault("season_stats", {})

    for season_id, stats in verified_archive.items():
        if season_id not in season_stats:
            season_stats[season_id] = dict(stats)

    peak_match = PEAK_PATTERN.fullmatch(str(player.get("peak") or ""))

    if peak_match is None:
        return

    matching_seasons = [
        season
        for season in seasons
        if season_name_key(season.get("name")) == season_name_key(peak_match.group("season"))
    ]

    if len(matching_seasons) != 1:
        return

    season_id = str(matching_seasons[0]["id"])
    existing = season_stats.get(season_id) or {}
    goals = int(peak_match.group("goals"))
    assists = int(peak_match.group("assists"))

    if any(
        nonnegative_number(existing.get(field)) not in (None, value)
        for field, value in (("goals", goals), ("assists", assists))
    ):
        return

    if type(existing.get("goals")) is int and type(existing.get("assists")) is int:
        return

    season_stats[season_id] = {
        **existing,
        "apps": existing.get("apps"),
        "goals": goals,
        "assists": assists,
        "origin": existing.get("origin") or "archived_peak",
    }


def breakdown_coverage(player: dict) -> dict:
    history = player.get("season_history") or []
    known_totals: dict[str, int] = {}
    unassigned_totals: dict[str, int | None] = {}

    for field in STAT_FIELDS:
        known = sum(
            entry[field]
            for entry in history
            if type(entry.get(field)) is int
        )
        full_total = player.get(field)
        known_totals[field] = known

        if type(full_total) is int:
            if known > full_total:
                raise ValueError(
                    f"Player {player.get('id')} has {known} seasonal {field}, above lifetime total {full_total}"
                )

            unassigned_totals[field] = full_total - known
        else:
            unassigned_totals[field] = None

    return {
        "by_season": known_totals,
        "unassigned": unassigned_totals,
        "partial": any(
            unassigned_totals[field] not in (0, None)
            for field in ("apps", "goals", "assists")
        ),
    }
