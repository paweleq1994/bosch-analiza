"""Reconcile player statistics from season-level PLP records without double counting."""
from __future__ import annotations

from html import unescape
import re

STAT_FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
TEAM_RE = re.compile(r"/druzyna/([^/'\"?#]+)", re.I)
CANONICAL_SEASONS = {"148": "orlik-2026"}


def season_id(identifier):
    return CANONICAL_SEASONS.get(str(identifier), str(identifier))


def total_fields(rows):
    """Unknown fields remain unknown instead of silently turning into zero."""
    entries = list(rows)
    if not entries:
        return {key: None for key in STAT_FIELDS}
    return {
        key: sum(entry[key] for entry in entries)
        if all(type(entry.get(key)) is int for entry in entries) else None
        for key in STAT_FIELDS
    }


def career_from_profile(profile, parse_number):
    """Merge duplicated league sections by (season, team); preserve transfers."""
    unique = {}
    teams = set()
    for by_season in (profile.get("statistics") or {}).values():
        if not isinstance(by_season, dict):
            continue
        for sid, entry in by_season.items():
            if str(sid) in ("0", "-1") or not isinstance(entry, dict):
                continue
            apps = parse_number(entry.get("appearances"))
            if apps is None:
                continue
            raw_team = str(entry.get("team") or "")
            match = TEAM_RE.search(raw_team)
            team = match.group(1).lower() if match else re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", raw_team)).strip()).lower()
            if not team or team == "-":
                continue
            key = (str(sid), team)
            stats = {
                "apps": apps,
                "goals": parse_number(entry.get("goals")),
                "assists": parse_number(entry.get("assists")),
                "motm": parse_number(entry.get("pikarzmeczu")),
                "yellow": parse_number(entry.get("yellowcards")),
                "red": parse_number(entry.get("redcards")),
            }
            previous = unique.get(key)
            if previous is not None and previous != stats:
                if previous["apps"] == 0 and apps > 0:
                    unique[key] = stats
                elif apps == 0 and previous["apps"] > 0:
                    continue
                else:
                    raise ValueError(f"Contradictory PLP career entry for season {sid} and team {team}")
            else:
                unique[key] = stats

            teams.add(team)
    if not unique:
        return None
    return {
        **total_fields(unique.values()),
        "source": "PLP SportsPress",
        "seasons": len({key[0] for key in unique}),
        "teams": len(teams),
    }


def bosch_totals(seasons):
    """Sum every verified Bosch season, including supercups and Orlik 2026."""
    if not seasons:
        return None
    ids = {}
    for sid, row in seasons.items():
        canonical_id = season_id(sid)
        values = {name: row.get(name) for name in STAT_FIELDS}
        if canonical_id in ids and ids[canonical_id] != values:
            raise ValueError(f"Conflicting PLP Bosch season alias: {canonical_id}")
        ids[canonical_id] = values
    return total_fields(ids.values())
