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
    player_career_extra = load("player_career_updates.json", {})
    stat_corrections = load("player_stat_corrections.json", {})
    goal_evidence = load("goal_evidence.json", {"players": [], "administrative_adjustments": []})
    own_goal_evidence = load("bosch_own_goal_evidence.json", {"events": []})
    match_protocol_index = load("match_protocol_audit_index.json", {})

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
    for incoming_season in league_extra.get("season_rows", []):
        if str(incoming_season.get("plp_id") or incoming_season.get("id")) == "148":
            incoming_season = {**incoming_season, "id": SEASON_2026, "name": "Orlik 2026"}
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
    known_ids = {row["id"] for row in matches}
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
        item = next((p for p in historic_players if p["id"] == player_id), None)
        if item is None:
            item = {
                "id": player_id, "name": stat.get("name") or f"Zawodnik #{player_id}",
                "profile_url": (profiles.get(player_id) or {}).get("profile_url") or "",
                "status": "PLP", "apps": None, "goals": None, "assists": None,
                "motm": None, "yellow": None, "red": None, "peak": "",
                "seasons_label": "", "orlik2026": None, "hala2526": None,
            }
            historic_players.append(item)
        detail = {key: stat.get(key) for key in ("apps", "goals", "assists", "motm")}
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
        if video_id and video_id not in video_by_id:
            video_by_id[video_id] = item
    manual = videos_extra.get("manual_bindings", {})
    for video_id, binding in manual.items():
        if video_id in video_by_id:
            video_by_id[video_id]["match_id"] = str(binding.get("match_id") or "") or None
            video_by_id[video_id]["segment"] = binding.get("segment") or ""
            video_by_id[video_id]["status"] = "matched_manual" if video_by_id[video_id]["match_id"] else "rejected"
    match_map = {match["id"]: match for match in matches}
    for video in video_by_id.values():
        match = match_map.get(str(video.get("match_id") or ""))
        if match and not any(existing.get("video_id") == video["id"] for existing in match["videos"]):
            match["videos"].append({
                "video_id": video["id"], "title": video.get("title", ""),
                "url": video.get("url", ""), "segment": video.get("segment", ""),
                "channel_name": video.get("channel", ""), "publish_date": video.get("date", ""),
            })

    validate_goal_evidence(goal_evidence, seasons, matches)
    add_verified_players(historic_players, profiles, goal_evidence, player_seasons_extra)

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

            if stats.get("origin") in {"plp_public_season", "plp_match_minimum"}:
                verified_stats["origin"] = stats["origin"]

            if canonical_id == SEASON_2026:
                verified_stats = latest_orlik(player.get("recap2026"), verified_stats)
                player["orlik2026"] = verified_stats
            elif canonical_id == "146":
                player["hala2526"] = verified_stats

            player.setdefault("season_stats", {})[canonical_id] = verified_stats

    from player_totals import bosch_totals

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
                    "origin":stat.get("origin") or "plp_season"})
        for season in seasons:
            sid = str(season["id"])
            if season["name"] in season_names or sid in season_stats:
                stat = season_stats.get(sid) or {}
                history.append({"sid": sid, "name": season["name"],
                                "apps": stat.get("apps"), "goals": stat.get("goals"),
                                "assists": stat.get("assists"), "motm": stat.get("motm"),
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
    administrative_adjustments = administrative_goals_by_season(goal_evidence)

    for season in seasons:
        if season.get("gf") is None:
            continue

        season_id = str(season["id"])
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

        if summed_player_goals != individual_goals:
            raise ValueError(
                f"Season/player protocol goal mismatch in {season['name']}: "
                f"{summed_player_goals} != {individual_goals}"
            )

        difference = season["gf"] - individual_goals - opponent_own_goals - administrative_goals

        if difference != 0:
            raise ValueError(f"Match reports leave {difference} goals unresolved in {season['name']}")

        goal_coverage.append({
            "sid": season_id,
            "season": season["name"],
            "team_goals": season["gf"],
            "attributed_goals": individual_goals,
            "administrative_goals": administrative_goals,
            "opponent_own_goals": opponent_own_goals,
            "administrative_events": official_corrections.get("events", []),
            "unattributed_goals": difference,
            "players_with_verified_stats": sum(
                type((player.get("season_stats", {}).get(season_id) or {}).get("goals")) is int
                for player in historic_players
            ),
            "source": "113 PLP direct match reports, scorer minute icons, own goals and administrative decisions",
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
            "match_protocol_audit": protocol_enrichment,
            "match_protocol_audit": match_protocol_summary,
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
    output["media"] = load("media_manifest.json", {"subjects": []})
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
