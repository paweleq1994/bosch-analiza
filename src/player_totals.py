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
    descriptions = {}
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
            label = " ".join(
                unescape(re.sub(r"<[^>]+>", " ", raw_team)).split()
            ) or team

            previous = unique.get(key)
            if previous is not None and previous != stats:
                if previous["apps"] == 0 and apps > 0:
                    unique[key] = stats
                    descriptions[key] = {"name": str(entry.get("name") or sid), "team": label}
                elif apps == 0 and previous["apps"] > 0:
                    continue
                else:
                    raise ValueError(f"Contradictory PLP career entry for season {sid} and team {team}")
            else:
                unique[key] = stats
                descriptions[key] = {"name": str(entry.get("name") or sid), "team": label}

            teams.add(team)
    if not unique:
        return None
    history = [
        {
            "sid": season_id,
            "name": descriptions[(season_id, team)]["name"],
            "team": descriptions[(season_id, team)]["team"],
            **stats,
        }
        for (season_id, team), stats in sorted(
            unique.items(),
            key=lambda row: (
                int(row[0][0]) if str(row[0][0]).isdigit() else -1,
                str(row[0][0]),
                row[0][1],
            ),
            reverse=True,
        )
    ]

    return {
        **total_fields(unique.values()),
        "source": "PLP SportsPress",
        "seasons": len({key[0] for key in unique}),
        "teams": len(teams),
        "season_rows": history,
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


def reconcile_public_supercups(seasons, careers, snapshots):
    """Use public cup totals only with an unambiguous same-season club record.

    REST league aggregates can return zero for cups without league taxonomy.
    Replace that season once; never add an all-club career total to Bosch.
    """
    records = []
    for identifier, snapshot in snapshots.items():
        source = str(snapshot.get("source_url") or "")
        if not source.startswith("https://podlaskaliga.pl/zawodnik/"):
            continue
        api_rows = (careers.get(identifier) or {}).get("season_rows") or []
        for public in snapshot.get("season_rows") or []:
            name = str(public.get("name") or "")
            if "superpuchar" not in name.lower() or not public.get("apps"):
                continue
            if any(type(public.get(field)) is not int or public[field] < 0 for field in STAT_FIELDS):
                continue
            key = re.sub(r"[^a-z0-9]", "", name.lower())
            matching = [row for row in api_rows if re.sub(r"[^a-z0-9]", "", str(row.get("name") or "").lower()) == key]
            record = {"player_id": identifier, "season": name, "source_url": source,
                      "public": {field: public[field] for field in STAT_FIELDS}}
            if len(matching) != 1:
                records.append({**record, "status": "club_scope_unverified"})
                continue
            club = matching[0].get("team")
            sid = str(matching[0].get("sid") or "")
            record.update({"season_id": sid, "club": club})
            if club != "Bosch Service Tech-Car":
                records.append({**record, "status": "other_club_excluded"})
                continue
            if not sid.isdigit() or sid == "0":
                records.append({**record, "status": "season_identity_unverified"})
                continue
            current = (seasons.get(identifier) or {}).get(sid) or {}
            before = {field: current.get(field) for field in STAT_FIELDS}
            record["before"] = before
            if any(type(before[field]) is int and before[field] > public[field] for field in STAT_FIELDS):
                records.append({**record, "status": "existing_source_exceeds_html"})
                continue
            if all(before[field] == public[field] for field in STAT_FIELDS):
                records.append({**record, "status": "already_included"})
                continue
            seasons.setdefault(identifier, {})[sid] = {
                **current, **record["public"], "name": name,
                "origin": "plp_public_supercup", "source_url": source,
                "captured_at": snapshot.get("captured_at"),
            }
            records.append({**record, "status": "restored_from_public_html"})
    return records


def confirm_bosch_totals(player):
    """Retire an old minimum flag only when club rows and public HTML agree."""
    if not player.get("stats_minimum"):
        return False
    career = player.get("career_totals") or {}
    rows = career.get("season_rows") or []
    public = career.get("public_season_rows") or []
    club_rows = [row for row in rows if row.get("team") == "Bosch Service Tech-Car"]
    if not club_rows or not public or not str(career.get("source_url") or "").startswith("https://podlaskaliga.pl/zawodnik/"):
        return False
    for row in club_rows:
        # A combined public season cannot independently verify a club split
        # when the player represented several teams in the same competition.
        if sum(other.get("sid") == row.get("sid") for other in rows) != 1:
            return False
        matching = [other for other in public if other.get("name") == row.get("name")]
        if len(matching) != 1 or any(type(row.get(field)) is not int or row[field] != matching[0].get(field) for field in STAT_FIELDS):
            return False
        season = (player.get("season_stats") or {}).get(season_id(row["sid"])) or {}
        if any(season.get(field) != row[field] for field in STAT_FIELDS):
            return False
    totals = total_fields(club_rows)
    if any(player.get(field) != totals[field] or (player.get("bosch_totals") or {}).get(field) != totals[field]
           or (player.get("season_coverage", {}).get("unassigned") or {}).get(field) != 0 for field in STAT_FIELDS):
        return False
    player["stats_minimum"] = False
    player["stats_source"] = "PLP — sezony Boscha potwierdzone publiczną tabelą kariery"
    player["bosch_totals_verified"] = {"source_url": career["source_url"], "season_ids": [row["sid"] for row in club_rows]}
    return True
