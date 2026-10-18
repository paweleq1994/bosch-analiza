"""Consolidate duplicate PLP identities while retaining attributable source records."""
from __future__ import annotations

from collections import defaultdict

TOTAL_FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
SEASON_2026 = "orlik-2026"


def canonical_season(value: object) -> str:
    return SEASON_2026 if str(value) in ("148", SEASON_2026) else str(value)


def merge_numeric_rows(primary: dict, duplicate: dict) -> dict:
    combined = dict(primary)

    for field in TOTAL_FIELDS:
        first = primary.get(field)
        second = duplicate.get(field)

        if type(first) is int and type(second) is int:
            combined[field] = first + second
        elif type(first) is not int and type(second) is int:
            combined[field] = second

    return combined


def combine_season_statistics(main: dict, duplicate: dict) -> dict:
    result = {}

    for player in (main, duplicate):
        for season_id, stats in (player.get("season_stats") or {}).items():
            season_key = canonical_season(season_id)

            if season_key in result:
                result[season_key] = merge_numeric_rows(result[season_key], stats)
            else:
                result[season_key] = dict(stats)

    return result


def combine_career_rows(main: dict, duplicate: dict) -> dict | None:
    first = main.get("career_totals") or {}
    second = duplicate.get("career_totals") or {}

    if not first and not second:
        return None

    rows = {}

    for career in (first, second):
        for row in career.get("season_rows") or []:
            key = (canonical_season(row.get("sid")), str(row.get("team") or ""))

            if key in rows:
                rows[key] = merge_numeric_rows(rows[key], row)
            else:
                rows[key] = dict(row)

    merged = merge_numeric_rows(first, second)
    merged["season_rows"] = list(rows.values())
    merged["seasons"] = len({season_id for season_id, _ in rows})
    merged["teams"] = len({team for _, team in rows if team})
    merged["source"] = "PLP SportsPress — merged source identities"

    return merged


def merge_player_identities(players: list[dict], identity_merges: dict) -> list[dict]:
    indexed = {str(player["id"]): player for player in players}

    for primary_id, specification in identity_merges.items():
        primary = indexed.get(str(primary_id))

        if primary is None:
            raise ValueError(f"Missing canonical PLP identity: {primary_id}")

        for duplicate_id in specification.get("duplicate_ids") or []:
            duplicate = indexed.get(str(duplicate_id))

            if duplicate is None:
                raise ValueError(f"Missing duplicate PLP identity: {duplicate_id}")

            if duplicate is primary:
                raise ValueError("Duplicate cannot be its own canonical identity")

            if "rutkowski" not in str(primary.get("name", "")).lower() or "rutkowski" not in str(duplicate.get("name", "")).lower():
                raise ValueError(f"Unexpected player identity merge: {primary_id} / {duplicate_id}")

            season_stats = combine_season_statistics(primary, duplicate)
            career_totals = combine_career_rows(primary, duplicate)

            for field in TOTAL_FIELDS:
                main_value = primary.get(field)
                duplicate_value = duplicate.get(field)

                if type(main_value) is int and type(duplicate_value) is int:
                    primary[field] = main_value + duplicate_value
                elif type(main_value) is not int and type(duplicate_value) is int:
                    primary[field] = duplicate_value

            primary["season_stats"] = season_stats
            primary["bosch_totals"] = merge_numeric_rows(primary.get("bosch_totals") or {}, duplicate.get("bosch_totals") or {})
            primary["career_totals"] = career_totals
            primary["orlik2026"] = season_stats.get(SEASON_2026)
            primary["hala2526"] = season_stats.get("146")
            primary["stats_source"] = "PLP — merged duplicate player identities"
            primary["merged_source_profiles"] = list(dict.fromkeys(
                (primary.get("merged_source_profiles") or [])
                + [primary.get("profile_url"), duplicate.get("profile_url")]
            ))
            aliases = [str(alias) for alias in primary.get("aliases") or []]
            aliases.extend(str(alias) for alias in duplicate.get("aliases") or [])
            aliases.append(str(duplicate_id))
            primary["aliases"] = list(dict.fromkeys(alias for alias in aliases if alias != str(primary_id)))
            players.remove(duplicate)
            indexed.pop(str(duplicate_id))

    return players
