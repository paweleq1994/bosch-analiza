#!/usr/bin/env python3
"""Build the zero-cost static Bosch portal from versioned source data."""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import json
import re
import unicodedata

from player_identity import legacy_player_id, match_public_profile, person_key
from merge_player_identities import merge_player_identities
from integrate_match_protocols import integrate_match_protocols
from protocol_goals import enrich_from_protocols
from backfill_match_player_stats import backfill_seasons
from complete_verified_goal_zeros import complete_protocol_goal_fields
from integrate_verified_match_players import attach_verified_identities, minimum_match_totals
from media_identity import canonicalize_player_media
from goal_reconciliation import add_verified_players, administrative_goals_by_season, validate_goal_evidence
from reconcile_player_history import apply_archived_seasons, archived_bosch_seasons, breakdown_coverage

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "docs" / "assets" / "data.json"
BOSCH = "Bosch Service Tech-Car"
SEASON_2026 = "orlik-2026"
FIXTURES_URL = "https://podlaskaliga.pl/druzyna/bosch-service-tech-car/terminarz/"


def load(name: str, default=None):
    path = DATA / name
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(value: str) -> str:
    value = unescape(re.sub(r"<[^>]*>", "", str(value or "")))
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def match_row(row: dict) -> dict:
    return {
        "id": str(row.get("id") or row.get("event_id") or ""),
        "sid": str(row.get("sid") or ""),
        "season": row.get("season") or "",
        "date": str(row.get("date") or "")[:10],
        "opponent": row.get("display_opponent") or row.get("opponent") or "",
        "opponent_id": row.get("opponent_id"),
        "match": row.get("match") or "",
        "gf": int(row.get("gf") or 0),
        "ga": int(row.get("ga") or 0),
        "halftime": row.get("halftime") or "",
        "event_link": row.get("event_link") or "",
        "videos": row.get("links") or [],
    }


def main() -> None:
    report = load("bosch_service_tech_car_data_v3.json")
    archive = load("bosch_service_tech_car_video_library_v3.json")
    recap = load("orlik_2026_recap.json")
    profiles = load("player_profile_map.json")
    promotions = load("promoted_teams_analysis.json")
    scouting = load("orlik_2026_opponents.json")
    videos_extra = load("video_updates.json", {"videos": [], "manual_bindings": {}})
    league_extra = load("league_updates.json", {"matches": []})
    player_seasons_extra = load("player_season_updates.json", {})
    # Partial archival corrections do not establish a complete player profile.
    profile_stat_ids = set(player_seasons_extra)
    player_career_extra = load("player_career_updates.json", {})
    public_html_careers = load("player_html_career_snapshot.json", {"players": {}}).get("players", {})
    stat_corrections = load("player_stat_corrections.json", {})
    goal_evidence = load("goal_evidence.json", {"players": [], "administrative_adjustments": []})
    own_goal_evidence = load("bosch_own_goal_evidence.json", {"events": []})
    match_protocol_index = load("match_protocol_audit_index.json", {})
    match_performance = load("match_player_evidence.json", {"matches": []})

    for player_id, correction in stat_corrections.items():
        url = str(correction.get("source_url") or "")

        if not url.startswith("https://podlaskaliga.pl/zawodnik/"):
            raise ValueError(f"Unverified player correction source: {player_id}")

        player_seasons = player_seasons_extra.setdefault(str(player_id), {})

        for season_id, correction_stats in (correction.get("seasons") or {}).items():
            previous = player_seasons.get(str(season_id)) or {}

            if any(
                isinstance(previous.get(field), int)
                and previous[field] > correction_stats.get(field, previous[field])
                for field in ("apps", "goals", "assists")
            ):
                continue

            player_seasons[str(season_id)] = {**previous, **correction_stats}


    seasons = [
        {
            "id": str(row["sid"]),
            "name": row["season"],
            "position": row.get("pos"),
            "points": row.get("points"),
            "matches": row.get("matches"),
            "wins": row.get("wins"),
            "draws": row.get("draws"),
            "losses": row.get("losses"),
            "gf": row.get("gf"),
            "ga": row.get("ga"),
            "clean_sheets": row.get("clean_sheets"),
            "table": row.get("table_title"),
            "origin": "official_archive",
        }
        for row in report.get("season_rows", [])
    ]
    stats = recap.get("stats", {})
    if stats.get("matches") == 15 and stats.get("points") == 35:
        seasons.append({
            "id": SEASON_2026,
            "name": "Orlik 2026",
            "position": stats.get("position"),
            "points": stats.get("points"),
            "matches": stats.get("matches"),
            "wins": stats.get("wins"),
            "draws": stats.get("draws"),
            "losses": stats.get("losses"),
            "gf": stats.get("goals_for"),
            "ga": stats.get("goals_against"),
            "clean_sheets": stats.get("clean_sheets"),
            "table": "II Liga – Orlik 2026",
            "origin": "official_recap",
        })
    # The SportsPress season 148 is the same edition as the archived Orlik 2026.
    # Prefer the stable public ID and keep official scores and links.
    archived_season_counts = {str(row["id"]): row["matches"] for row in seasons}
    growing_season_ids = set()
    for incoming_season in league_extra.get("season_rows", []):
        if str(incoming_season.get("plp_id") or incoming_season.get("id")) == "148":
            incoming_season = {**incoming_season, "id": SEASON_2026, "name": "Orlik 2026"}
        sid = str(incoming_season["id"])
        if sid not in archived_season_counts or incoming_season["matches"] > archived_season_counts[sid]:
            growing_season_ids.add(sid)
        index = next((i for i, item in enumerate(seasons) if str(item["id"]) == str(incoming_season["id"])), None)
        if index is None:
            seasons.append(incoming_season)
        else:
            seasons[index] = {**seasons[index], **incoming_season}
    matches = [match_row(row) for row in archive.get("match_rows", [])]
    for idx, row in enumerate(recap.get("matches", []), start=1):
        matches.append({
            "id": f"orlik26-{idx}",
            "sid": SEASON_2026,
            "season": "Orlik 2026",
            "date": row["date"],
            "opponent": row["opponent"],
            "opponent_id": None,
            "match": f"{BOSCH} — {row['opponent']}",
            "gf": row["goals_for"],
            "ga": row["goals_against"],
            "halftime": "",
            "event_link": FIXTURES_URL,
            "videos": [],
        })
    archived_match_ids = {row["id"] for row in matches}
    match_positions = {item["id"]: index for index, item in enumerate(matches)}
    for row in league_extra.get("matches", []):
        clean = match_row(row)
        if str(row.get("plp_season_id") or row.get("sid")) == "148":
            counterpart = next((m for m in matches if m["sid"] == SEASON_2026 and m["date"] == clean["date"] and normalized(m["opponent"]) == normalized(clean["opponent"])), None)
            if counterpart is not None:
                clean["id"] = counterpart["id"]
            clean["sid"] = SEASON_2026
            clean["season"] = "Orlik 2026"
        if not clean["id"]:
            continue
        index = match_positions.get(clean["id"])
        if index is None:
            match_positions[clean["id"]] = len(matches)
            matches.append(clean)
        else:
            videos = matches[index].get("videos") or clean["videos"]
            matches[index] = {**matches[index], **clean, "videos": videos}
    matches.sort(key=lambda row: (row["date"], row["id"]))
    last_played = {str(row["sid"]): row["date"] for row in matches}
    seasons.sort(key=lambda row: (last_played.get(str(row["id"]), ""), str(row["id"])))

    historic_players = []
    player_by_name = {}
    for row in report.get("player_cards", []):
        player_id = str(row["player_id"])
        profile = profiles.get(player_id) or {}
        item = {
            "id": player_id,
            "name": profile.get("resolved_name") or row["name"],
            "profile_url": profile.get("profile_url") if profile.get("public") else "",
            "status": row.get("status") or "",
            "apps": row.get("apps") or 0,
            "goals": row.get("goals") or 0,
            "assists": row.get("assists") or 0,
            "motm": row.get("motm") or 0,
            "yellow": row.get("yellow") or 0,
            "red": row.get("red") or 0,
            "peak": row.get("peak") or "",
            "seasons_label": row.get("seasons_label") or "",
            "orlik2026": None,
            "hala2526": None,
        }
        historic_players.append(item)
        player_by_name[person_key(item["name"])] = item
        player_by_name[person_key(row["name"])] = item
    for row in report.get("current_players", []):
        item = next((player for player in historic_players if player["id"] == str(row.get("player_id"))), None)
        if item:
            item["hala2526"] = {
                "apps": row.get("apps", 0), "goals": row.get("goals", 0),
                "assists": row.get("assists", 0), "motm": row.get("motm", 0),
            }
    for row in recap.get("player_leaders", []):
        player_name = str(row.get("name") or "")
        item = player_by_name.get(person_key(player_name))
        legacy_id = legacy_player_id(player_name)

        if item is None:
            resolved_profile = match_public_profile(player_name, profiles)
            profile_id, profile = resolved_profile if resolved_profile else (legacy_id, {})
            item = next((player for player in historic_players if player["id"] == profile_id), None)

            if item is None:
                item = {
                    "id": profile_id,
                    "name": player_name,
                    "profile_url": profile.get("profile_url") or "",
                    "status": "Orlik 2026",
                    "apps": None,
                    "goals": None,
                    "assists": None,
                    "motm": None,
                    "yellow": None,
                    "red": None,
                    "peak": "",
                    "seasons_label": "",
                    "hala2526": None,
                    "orlik2026": None,
                }
                historic_players.append(item)

            player_by_name[person_key(player_name)] = item

        aliases = item.setdefault("aliases", [])
        if legacy_id != item["id"] and legacy_id not in aliases:
            aliases.append(legacy_id)

        item["recap2026"] = {
            "apps": row.get("appearances"),
            "goals": row.get("goals"),
            "assists": row.get("assists"),
        }
        item["orlik2026"] = dict(item["recap2026"])

    for stat in league_extra.get("player_seasons", []):
        player_id, season_id = str(stat.get("id") or ""), str(stat.get("sid") or "")
        if not player_id or not season_id:
            continue
        if season_id not in growing_season_ids:
            # Existing profile/archive imports and protocol backfills already
            # reconcile historical seasons, including unassigned totals. A
            # newly parseable match table must not replace that richer history.
            continue
        item = next((p for p in historic_players if p["id"] == player_id), None)
        if item is None:
            if not (profiles.get(player_id) or {}).get("resolved_name"):
                # Preserve the ID in source evidence and the unmatched-ID audit
                # until the existing identity resolver provides a real name.
                continue
            item = {
                "id": player_id, "name": stat.get("name") or f"Zawodnik #{player_id}",
                "profile_url": (profiles.get(player_id) or {}).get("profile_url") or "",
                "status": "PLP", "apps": None, "goals": None, "assists": None,
                "motm": None, "yellow": None, "red": None, "peak": "",
                "seasons_label": "", "orlik2026": None, "hala2526": None,
            }
            historic_players.append(item)
        detail = {key: stat.get(key) for key in ("apps", "goals", "assists", "motm", "yellow", "red")}
        detail.update({key: stat[key] for key in ("origin", "match_performance_verified", "match_performance_sources") if key in stat})
        # A newly discovered season can precede the profile API refresh. Keep
        # its verified match aggregates in the same totals/history pipeline.
        existing_details = player_seasons_extra.setdefault(player_id, {})
        if season_id not in existing_details and not (season_id == SEASON_2026 and "148" in existing_details):
            existing_details[season_id] = dict(detail)
        item.setdefault("season_stats", {})[season_id] = detail
        if season_id in (SEASON_2026, "148"):
            item["orlik2026"] = detail
        if season_id == "146":
            item["hala2526"] = detail

    video_by_id = {}
    for match in matches:
        for item in match.get("videos", []):
            video_id = item.get("video_id")
            if video_id:
                video_by_id[video_id] = {
                    "id": video_id,
                    "title": item.get("title", ""),
                    "url": item.get("url", f"https://www.youtube.com/watch?v={video_id}"),
                    "date": item.get("publish_date") or item.get("upload_date") or "",
                    "channel": item.get("channel_name") or "",
                    "segment": item.get("segment") or "",
                    "match_id": match["id"],
                    "status": "matched_archive",
                }
    for item in archive.get("unmatched_rows", []):
        video_id = item.get("video_id")
        if video_id and video_id not in video_by_id:
            video_by_id[video_id] = {
                "id": video_id, "title": item.get("title", ""),
                "url": item.get("url", f"https://www.youtube.com/watch?v={video_id}"),
                "date": item.get("publish_date") or "",
                "channel": item.get("channel_name") or "",
                "segment": "", "match_id": None, "status": "unmatched",
            }
    for item in videos_extra.get("videos", []):
        video_id = item.get("id")
        if video_id:
            previous = video_by_id.get(video_id, {})
            # Metadata refreshes also apply to films already in the archive.
            video_by_id[video_id] = {**previous, **{k: v for k, v in item.items() if v not in (None, "")}}
    manual = videos_extra.get("manual_bindings", {})
    for video_id, binding in manual.items():
        if video_id in video_by_id:
            video_by_id[video_id]["match_id"] = str(binding.get("match_id") or "") or None
            video_by_id[video_id]["segment"] = binding.get("segment", video_by_id[video_id].get("segment") or "")
            video_by_id[video_id]["status"] = "matched_manual" if video_by_id[video_id]["match_id"] else "rejected"
            for key in ("review_reason", "reviewed_at", "review_category", "verification_source"):
                if key in binding:
                    video_by_id[video_id][key] = binding[key]
    original_video_details = {str(v.get("video_id")): v for match in matches for v in match["videos"]}
    for match in matches:
        match["videos"] = [v for v in match["videos"]
                           if str((video_by_id.get(str(v.get("video_id"))) or {}).get("match_id") or "") == str(match["id"])]
    match_map = {match["id"]: match for match in matches}
    for video in video_by_id.values():
        match = match_map.get(str(video.get("match_id") or ""))
        if match and not any(existing.get("video_id") == video["id"] for existing in match["videos"]):
            match["videos"].append({
                **original_video_details.get(video["id"], {}),
                "video_id": video["id"], "title": video.get("title", ""),
                "url": video.get("url", ""), "segment": video.get("segment", ""),
                "channel_name": video.get("channel", ""), "publish_date": video.get("date", ""),
                **({"length_seconds": video["length_seconds"]} if type(video.get("length_seconds")) is int else {}),
            })

    validate_goal_evidence(goal_evidence, seasons, matches)
    add_verified_players(historic_players, profiles, goal_evidence, player_seasons_extra)
    verified_identities = load("match_player_identities.json", {"players": {}, "unresolved": {}})
    identity_audit = attach_verified_identities(historic_players, verified_identities, match_performance)

    # A registered squad member need not have appeared in any protocol.
    rosters = load("player_rosters.json", {})
    for roster in rosters.values():
        for pid, member in roster.get("members", {}).items():
            if any(p["id"] == pid for p in historic_players):
                continue
            profile = profiles.get(pid) or {}
            historic_players.append({"id": pid, "name": profile.get("resolved_name") or member["name"],
                "profile_url": profile.get("profile_url") if profile.get("public") else "",
                "status": "Zgłoszony do kadry PLP", "apps": None, "goals": None,
                "assists": None, "motm": None, "yellow": None, "red": None,
                "peak": "", "seasons_label": "", "orlik2026": None, "hala2526": None,
                "verified_identity_source": {"evidence_urls": member["source_urls"]}})

    def latest_orlik(recap_stats: dict | None, official_stats: dict | None) -> dict:
        if not recap_stats:
            return dict(official_stats or {})

        if not official_stats:
            return dict(recap_stats)

        fields = ("apps", "goals", "assists")
        known_comparisons = [
            (recap_stats.get(field), official_stats.get(field))
            for field in fields
            if isinstance(recap_stats.get(field), int)
        ]
        if known_comparisons and all(
            not isinstance(official_value, int) or recap_value >= official_value
            for recap_value, official_value in known_comparisons
        ) and any(
            not isinstance(official_value, int) or recap_value > official_value
            for recap_value, official_value in known_comparisons
        ):
            return {
                **official_stats,
                **recap_stats,
                "motm": None,
                "yellow": None,
                "red": None,
            }

        return dict(official_stats)

    for player in historic_players:
        details = player_seasons_extra.get(str(player["id"])) or {}

        for season_id, stats in details.items():
            canonical_id = SEASON_2026 if season_id == "148" else str(season_id)
            verified_stats = {
                key: stats.get(key)
                for key in ("apps", "goals", "assists", "motm", "yellow", "red")
            }

            if stats.get("origin") in {"plp_public_season", "plp_match_minimum", "plp_match_performance", "plp_archived_public_season"}:
                verified_stats["origin"] = stats["origin"]
            for key in ("match_performance_verified", "match_performance_sources", "source_url", "captured_at"):
                if key in stats:
                    verified_stats[key] = stats[key]

            if canonical_id == SEASON_2026:
                verified_stats = latest_orlik(player.get("recap2026"), verified_stats)
                player["orlik2026"] = verified_stats
            elif canonical_id == "146":
                player["hala2526"] = verified_stats

            player.setdefault("season_stats", {})[canonical_id] = verified_stats

    from player_totals import bosch_totals

    additional_match_totals = {}
    for match in match_performance.get("matches") or []:
        if str(match["match_id"]) in archived_match_ids:
            continue
        for row in match.get("players") or []:
            additions = additional_match_totals.setdefault(str(row["player_id"]), {})
            for field, source_field in (("apps", "appearance"), ("goals", "goals"), ("assists", "assists"),
                                        ("motm", "motm"), ("yellow", "yellow"), ("red", "red")):
                value = row.get(source_field)
                if type(value) is int and value >= 0:
                    additions[field] = additions.get(field, 0) + value

    for player in historic_players:
        details = player_seasons_extra.get(str(player["id"])) or {}
        verified_seasons = {
            SEASON_2026 if str(season_id) == "148" else str(season_id): dict(stats)
            for season_id, stats in details.items()
        }
        recap_stats = player.get("recap2026")

        if recap_stats and verified_seasons:
            verified_seasons[SEASON_2026] = latest_orlik(
                recap_stats,
                verified_seasons.get(SEASON_2026),
            )

        calculated = bosch_totals(verified_seasons)

        if str(player["id"]) not in profile_stat_ids and verified_seasons:
            # A new season does not make a previously incomplete Bosch archive
            # complete. Retain its older documented balance and add only the
            # disjoint new seasons, leaving unknown source values unknown.
            for field in ("apps", "goals", "assists", "motm", "yellow", "red"):
                additions = [stats.get(field) for sid, stats in verified_seasons.items()
                             if sid in growing_season_ids and sid not in archived_season_counts]
                extra = additional_match_totals.get(str(player["id"]), {}).get(field)
                if additions and all(type(v) is int for v in additions):
                    extra = max(extra or 0, sum(additions))
                if type(player.get(field)) is int and type(extra) is int:
                    player[field] += extra
            player["stats_minimum"] = True
            calculated = None

        if calculated:
            player["bosch_totals"] = calculated

            for field in ("apps", "goals", "assists", "motm", "yellow", "red"):
                player[field] = calculated[field]
        else:
            player["bosch_totals"] = None

        profile_id = str(player["id"])
        career = player_career_extra.get(profile_id)
        correction = stat_corrections.get(profile_id)

        if correction and career and career.get("teams") == 1:
            career = {**career}
            season_rows = [dict(record) for record in career.get("season_rows", [])]

            for season_id, correction_stats in correction["seasons"].items():
                match = next(
                    (record for record in season_rows if str(record["sid"]) == str(season_id)),
                    None,
                )

                if match is not None:
                    match.update(correction_stats)

            for field in ("apps", "goals", "assists", "motm", "yellow", "red"):
                if all(isinstance(record.get(field), int) for record in season_rows):
                    career[field] = sum(record[field] for record in season_rows)

            career["season_rows"] = season_rows
            career["source"] = "PLP SportsPress i publiczna tabela całej kariery"

        public_career = public_html_careers.get(profile_id)
        if public_career:
            source_totals = public_career["totals"]
            if any(type(source_totals.get(field)) is not int or source_totals[field] < 0 for field in ("apps", "goals", "assists", "motm", "yellow", "red")):
                raise ValueError(f"Invalid HTML career total: {profile_id}")
            if any(sum(row[field] for row in public_career["season_rows"]) != source_totals[field] for field in ("apps", "goals", "assists", "motm", "yellow", "red")):
                raise ValueError(f"HTML career rows do not add up: {profile_id}")
            career = {
                **(career or {}),
                **source_totals,
                "source": "PLP publiczna tabela kariery HTML",
                "source_url": public_career["source_url"],
                "html_captured_at": public_career["captured_at"],
                "public_season_rows": public_career["season_rows"],
                "seasons": len(public_career["season_rows"]),
            }
        player["career_totals"] = career
        player["stats_source"] = "PLP SportsPress i tabela całej kariery" if correction else (
            "PLP SportsPress i aktualny raport Orlik 2026"
            if recap_stats and verified_seasons
            else "PLP SportsPress"
            if calculated
            else "Niepełne archiwum — historyczne dane"
        )

        if player.get("stats_minimum") and not calculated:
            player["stats_source"] = "Protokół PLP — potwierdzone minimum, niepełne dane sezonu"
        elif any(
            stats.get("origin") == "plp_public_season"
            for stats in verified_seasons.values()
        ):
            player["stats_source"] = "PLP — publiczny profil i statystyki sezonowe"

    historic_players = merge_player_identities(
        historic_players,
        load("player_identity_merges.json", {}),
    )

    archive_rows = archived_bosch_seasons(
        promotions,
        {str(player["id"]) for player in historic_players},
    )

    for player in historic_players:
        apply_archived_seasons(
            player,
            archive_rows.get(str(player["id"]), {}),
            seasons,
        )

        if player["bosch_totals"] is None and any(
            str(row.get("origin") or "").startswith(("plp_archived", "archived_peak"))
            for row in player.get("season_stats", {}).values()
        ):
            player["stats_source"] = "Historyczne zestawienia PLP i Bosch, niepełny podział sezonów"

    match_protocol_summary = integrate_match_protocols(
        historic_players,
        matches,
        match_protocol_index,
    )
    goalkeeper_aliases = {
        str(duplicate): str(canonical)
        for canonical, configuration in load("player_identity_merges.json", {}).items()
        for duplicate in configuration.get("duplicate_ids") or []
    }

    for player in historic_players:
        if player.get("merged_source_profiles"):
            player["alternate_profile_urls"] = list(player["merged_source_profiles"])

    protocol_enrichment = enrich_from_protocols(
        matches,
        historic_players,
        profiles,
        match_protocol_index,
        goalkeeper_aliases,
        own_goal_evidence,
    )

    # Protocol-only players can be created after the initial career pass.
    for player in historic_players:
        if player.get("career_totals"):
            continue
        public_career = public_html_careers.get(str(player["id"]))
        if public_career:
            player["career_totals"] = {
                **public_career["totals"],
                "source": "PLP publiczna tabela kariery HTML",
                "source_url": public_career["source_url"],
                "html_captured_at": public_career["captured_at"],
                "public_season_rows": public_career["season_rows"],
                "seasons": len(public_career["season_rows"]),
            }

    for player in historic_players:
        public_rows = (player.get("career_totals") or {}).get("public_season_rows") or []
        if public_rows:
            career = player["career_totals"]
            career["html_identity_delta"] = career["apps"] - sum(row["apps"] for row in public_rows)

    match_backfill = backfill_seasons(historic_players, matches, match_performance)
    minimum_match_totals(historic_players, match_performance)
    box_scores = {str(record["match_id"]): record for record in match_performance["matches"]}
    known_names = {str(player["id"]): player["name"] for player in historic_players}
    for match in matches:
        record = box_scores.get(str(match["id"]))
        if record is None:
            match["player_performance"] = []
            match["player_performance_source"] = None
            continue
        match["player_performance"] = [
            {
                **entry,
                "name": known_names.get(str(entry["player_id"])) or
                    (profiles.get(str(entry["player_id"])) or {}).get("resolved_name") or
                    ("Zawodnik PLP #" + str(entry["player_id"])),
                "identity_verified": str(entry["player_id"]) in known_names,
            }
            for entry in record["players"]
        ]
        match["player_performance_source"] = record["source_url"]

    derived_protocol_goals = complete_protocol_goal_fields(historic_players, matches)

    aliases = {str(alias): p["id"] for p in historic_players for alias in p.get("aliases", [])}
    for sid, roster in rosters.items():
        for source_pid, member in roster.get("members", {}).items():
            pid = aliases.get(source_pid, source_pid)
            player = next((p for p in historic_players if p["id"] == pid), None)
            if player is None:
                continue
            stats = player.setdefault("season_stats", {})
            # Historical list team fields can refer to the current club.
            # A past season requires independent player-season evidence.
            if sid not in stats and sid != seasons[-1]["id"]:
                continue
            player.setdefault("roster_seasons", {})[sid] = member
            if sid not in stats:
                # A zero in an official squad list is valid for this season,
                # never evidence that the player's entire career is zero.
                has_appearance = any(str(m["sid"]) == sid and any(str(p["player_id"]) == pid for p in m.get("player_performance", [])) for m in matches)
                zero = member.get("listed_apps") == 0 and not has_appearance
                stats[sid] = {field: 0 if zero else None for field in ("apps", "goals", "assists", "motm", "yellow", "red")}
                stats[sid].update({"origin": "plp_roster", "source_urls": member["source_urls"]})

    # Keep direct reds identical to PLP. A second yellow is a separate,
    # match-derived dismissal and cannot be inferred from season yellow totals.
    for match in matches:
        for entry in match.get("player_performance", []):
            entry["second_yellow"] = int(type(entry.get("yellow")) is int and entry["yellow"] >= 2)
            entry["dismissals"] = int(entry["red"] > 0 or entry["second_yellow"] > 0) if type(entry.get("red")) is int else None
    for player in historic_players:
        entries = [entry for match in matches for entry in match.get("player_performance", []) if str(entry["player_id"]) == player["id"]]
        player["second_yellow"] = sum(entry["second_yellow"] for entry in entries)
        player["discipline_source"] = "Zachowane ligowe protokoły PLP"

    # Explicitly expose historical participation even when detailed PLP totals
    # were not captured in the original archive.
    for player in historic_players:
        details = player_seasons_extra.get(str(player["id"])) or {}
        season_names = [part.strip() for part in (player.get("seasons_label") or "").split(",") if part.strip()]
        season_stats = player.setdefault("season_stats", {})
        if player.get("hala2526"):
            season_stats["146"] = player["hala2526"]
        if player.get("orlik2026"):
            season_stats[SEASON_2026] = player["orlik2026"]
        history = []
        for sid, stat in details.items():
            if str(sid) in ("119","127","140","145") and (stat.get("apps") or 0)>0:
                history.append({"sid":str(sid),"name":stat.get("name") or ("Superpuchar "+str(sid)),
                    "apps":stat.get("apps"),"goals":stat.get("goals"),
                    "assists":stat.get("assists"),"motm":stat.get("motm"),
                    "yellow":stat.get("yellow"),"red":stat.get("red"),
                    "origin":stat.get("origin") or "plp_season",
                    **{key: stat[key] for key in ("source_url", "captured_at") if key in stat}})
        for season in seasons:
            sid = str(season["id"])
            if season["name"] in season_names or sid in season_stats:
                stat = season_stats.get(sid) or {}
                history.append({"sid": sid, "name": season["name"],
                                "apps": stat.get("apps"), "goals": stat.get("goals"),
                                "assists": stat.get("assists"), "motm": stat.get("motm"),
                                "yellow": stat.get("yellow"), "red": stat.get("red"),
                                "origin": stat.get("origin") or (
                                    "plp_season" if any(
                                        type(stat.get(field)) is int
                                        for field in ("apps", "goals", "assists")
                                    ) else "participation_only"
                                )})
        player["season_history"] = history
        player["season_coverage"] = breakdown_coverage(player)
        player.pop("recap2026", None)

    goal_coverage = []
    verified_goal_match_ids = {str(item["id"]) for item in match_protocol_index.get("matches") or []}
    administrative_adjustments = administrative_goals_by_season(goal_evidence)

    for season in seasons:
        if season.get("gf") is None:
            continue

        season_id = str(season["id"])
        season_matches = [match for match in matches if str(match["sid"]) == season_id]
        pending_matches = [match for match in season_matches if str(match["id"]) not in verified_goal_match_ids]
        audited_team_goals = sum(match["gf"] for match in season_matches if str(match["id"]) in verified_goal_match_ids)
        pending_team_goals = sum(match["gf"] for match in pending_matches)
        recorded = protocol_enrichment["seasons"].get(season_id) or {}
        individual_goals = recorded.get("player_goals", 0)
        opponent_own_goals = recorded.get("opponent_own_goals", 0)
        administrative_goals = recorded.get("administrative_goals", 0)
        official_corrections = administrative_adjustments.get(season_id) or {}

        if administrative_goals != official_corrections.get("goals", 0):
            raise ValueError(f"Administrative goal evidence does not match in {season_id}")

        summed_player_goals = sum(
            stats["goals"]
            for player in historic_players
            for stats in [player.get("season_stats", {}).get(season_id) or {}]
            if type(stats.get("goals")) is int and (type(stats.get("apps")) is not int or stats["apps"] > 0)
        )

        if not pending_matches and summed_player_goals != individual_goals:
            raise ValueError(
                f"Season/player protocol goal mismatch in {season['name']}: "
                f"{summed_player_goals} != {individual_goals}"
            )

        difference = audited_team_goals - individual_goals - opponent_own_goals - administrative_goals

        if difference != 0:
            raise ValueError(f"Match reports leave {difference} goals unresolved in {season['name']}")

        goal_coverage.append({
            "sid": season_id,
            "season": season["name"],
            "team_goals": season["gf"],
            "audited_team_goals": audited_team_goals,
            "pending_match_goals": pending_team_goals,
            "pending_match_count": len(pending_matches),
            "pending_match_ids": [str(match["id"]) for match in pending_matches],
            "attributed_goals": individual_goals,
            "administrative_goals": administrative_goals,
            "opponent_own_goals": opponent_own_goals,
            "administrative_events": official_corrections.get("events", []),
            "unattributed_goals": difference,
            "players_with_verified_stats": sum(
                type((player.get("season_stats", {}).get(season_id) or {}).get("goals")) is int
                for player in historic_players
            ),
            "source": "PLP individually verified match scorers, own goals and administrative decisions; pending new fixtures separated",
        })

    # One source of truth for repeated historical leaderboard rows.
    deduped_promotions = {}
    for row in promotions.get("promotions", []):
        key = (str(row.get("sid") or ""), str(row.get("team_id") or ""))
        if key not in deduped_promotions:
            deduped_promotions[key] = row

    from dedupe_portal import dedupe
    output = {
        "meta": {
            "title": "Bosch Service Tech-Car",
            "source_updated": recap.get("generated_at") or report.get("generated_at", ""),
            "seasons_count": len(seasons),
            "archive_generated": report.get("generated_at", ""),
            "video_archive_generated": archive.get("generated_at", ""),
        },
        "seasons": seasons,
        "matches": matches,
        "players": historic_players,
        "videos": sorted(video_by_id.values(), key=lambda item: item.get("date") or "", reverse=True),
        "analysis": {
            "state_rows": report.get("state_rows", []),
            "close_game_rows": report.get("close_game_rows", []),
            "continuity_rows": report.get("continuity_rows", []),
            "concentration_rows": report.get("concentration_rows", []),
            "tier_split_current": report.get("tier_split_current", []),
            "tier_split_peak": report.get("tier_split_peak", []),
            "halftime_all": report.get("halftime_all", []),
            "promotion_summary": promotions.get("summary", {}),
            "player_goal_coverage": goal_coverage,
            "match_protocol_audit": {**match_protocol_summary, **protocol_enrichment},
            "match_player_backfill": match_backfill,
            "verified_identity_audit": identity_audit,
            "verified_zero_goal_completion": derived_protocol_goals,
            "promotions": list(deduped_promotions.values()),
            "scouting": [
                {
                    "name": item.get("team_name"), "team_id": item.get("team_id"),
                    "threat_score": item.get("threat_score"),
                    "threat_level": item.get("threat_level"),
                    "summary": (item.get("scouting") or {}).get("summary", ""),
                    "plan": (item.get("scouting") or {}).get("bosch_plan", [])[:2],
                }
                for item in scouting.get("opponents", [])
            ],
        },
        "sources": {
            "plp": FIXTURES_URL,
            "github": "https://github.com/paweleq1994/bosch-analiza",
        },
    }
    historical_team_media = load("media_discovery.json", {"candidates": []})
    output["analysis"]["historical_team_media_candidates"] = [
        {
            "player_id": str(item["player_id"]),
            "media_id": str(item["media_id"]),
            "url": item["url"],
            "team": item["team"],
            "evidence": "historical_team_archive_unverified_person",
        }
        for item in historical_team_media.get("candidates") or []
        if item.get("evidence") == "historical_team_archive"
        and str(item.get("url") or "").startswith("https://podlaskaliga.pl/wp-content/uploads/")
    ]
    from video_goal_evidence import validate as verified_goal_video_cues
    output["analysis"]["verified_goal_video_cues"] = verified_goal_video_cues(
        output,
        load("video_goal_evidence.json", {"entries": []}),
    )
    output["media"] = canonicalize_player_media(
        load("media_manifest.json", {"subjects": []}),
        goalkeeper_aliases,
    )
    output, duplicate_warnings = dedupe(output)
    if duplicate_warnings:
        print("Deduplication audit:", "; ".join(duplicate_warnings))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Portal data: {len(seasons)} seasons, {len(matches)} matches, {len(historic_players)} players, {len(video_by_id)} videos")


if __name__ == "__main__":
    main()
