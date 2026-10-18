"""Merge confirmed duplicate PLP identities without losing season-specific source records."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from urllib.parse import urlsplit

from player_totals import STAT_FIELDS


def merge_stat_fields(primary: dict, secondary: dict) -> dict:
    merged = deepcopy(primary)

    for field in STAT_FIELDS:
        first = primary.get(field)
        second = secondary.get(field)

        if type(first) is int and type(second) is int:
            merged[field] = first + second
        elif first is None or second is None:
            merged[field] = None
        else:
            raise ValueError(f"Cannot merge conflicting PLP statistics: {field}")

    return merged


def merge_verified_seasons(
    primary: dict[str, dict],
    duplicate: dict[str, dict],
) -> dict[str, dict]:
    updated = deepcopy(primary)

    for season_id, duplicate_stats in duplicate.items():
        if season_id in updated:
            updated[season_id] = merge_stat_fields(updated[season_id], duplicate_stats)
        else:
            updated[season_id] = deepcopy(duplicate_stats)

        updated[season_id]["origin"] = "plp_confirmed_identity_merge"

    return updated


def merge_career_summaries(primary: dict | None, duplicate: dict | None) -> dict | None:
    if not primary and not duplicate:
        return None

    if not primary:
        return deepcopy(duplicate)

    if not duplicate:
        return deepcopy(primary)

    if primary.get("teams") != 1 or duplicate.get("teams") != 1:
        raise ValueError("Cannot combine PLP career records across unverified club transfers")

    season_index = {
        (str(row["sid"]), str(row.get("team") or "")): deepcopy(row)
        for row in primary.get("season_rows") or []
    }

    for row in duplicate.get("season_rows") or []:
        key = (str(row["sid"]), str(row.get("team") or ""))

        if key in season_index:
            season_index[key] = merge_stat_fields(season_index[key], row)
        else:
            season_index[key] = deepcopy(row)

    rows = sorted(
        season_index.values(),
        key=lambda row: (int(row["sid"]) if str(row["sid"]).isdigit() else -1, row["team"]),
        reverse=True,
    )
    merged = merge_stat_fields(primary, duplicate)
    merged["season_rows"] = rows
    merged["seasons"] = len({str(row["sid"]) for row in rows})
    merged["teams"] = 1
    merged["source"] = "PLP SportsPress — confirmed duplicate-profile merge"

    return merged


def merge_confirmed_players(
    players: list[dict],
    season_updates: dict,
    career_updates: dict,
    groups: list[dict],
) -> dict[str, str]:
    by_id = {str(player["id"]): player for player in players}
    aliases: dict[str, str] = {}
    removed_ids: set[str] = set()

    for group in groups:
        canonical_id = str(group["canonical_id"])
        canonical = by_id.get(canonical_id)

        if canonical is None or not canonical_id.isdigit():
            raise ValueError(f"Missing primary identity for profile merge: {canonical_id}")

        canonical["name"] = group["canonical_name"]
        source_links = set(canonical.get("alternate_profile_urls") or [])
        canonical_aliases = set(canonical.get("aliases") or [])

        for old_id in group["duplicate_ids"]:
            duplicate_id = str(old_id)
            duplicate = by_id.get(duplicate_id)

            if duplicate is None or not duplicate_id.isdigit() or duplicate_id == canonical_id:
                raise ValueError(f"Invalid duplicate identity: {duplicate_id}")

            if duplicate_id in removed_ids or duplicate_id in aliases:
                raise ValueError(f"Duplicate profile already merged: {duplicate_id}")

            old_url = duplicate.get("profile_url") or ""

            if old_url and urlsplit(old_url).hostname != "podlaskaliga.pl":
                raise ValueError(f"Untrusted duplicate-profile link: {old_url}")

            aliases[duplicate_id] = canonical_id
            canonical_aliases.add(duplicate_id)
            canonical_aliases.update(duplicate.get("aliases") or [])
            source_links.add(old_url)
            season_updates[canonical_id] = merge_verified_seasons(
                season_updates.get(canonical_id) or {},
                season_updates.get(duplicate_id) or {},
            )
            career_updates[canonical_id] = merge_career_summaries(
                career_updates.get(canonical_id),
                career_updates.get(duplicate_id),
            )
            removed_ids.add(duplicate_id)

        canonical["aliases"] = sorted(canonical_aliases)
        canonical["alternate_profile_urls"] = sorted(link for link in source_links if link)
        canonical["identity_merge_source"] = "user_confirmed_duplicate_PLp"

    players[:] = [player for player in players if str(player["id"]) not in removed_ids]

    return aliases
