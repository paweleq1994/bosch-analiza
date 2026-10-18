#!/usr/bin/env python3
"""Build the zero-cost static Bosch portal from versioned source data."""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import json
import re
import unicodedata

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


def person_key(value: str) -> str:
    return " ".join(sorted(token for token in normalized(value).split() if token not in {"gk", "bramkarz"}))


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
    for incoming_season in league_extra.get("season_rows", []):
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
        item = player_by_name.get(person_key(row.get("name", "")))
        if item is None:
            item = {
                "id": "new-" + normalized(row["name"]).replace(" ", "-"),
                "name": row["name"], "profile_url": "", "status": "Orlik 2026",
                "apps": None, "goals": None, "assists": None, "motm": None,
                "yellow": None, "red": None, "peak": "", "seasons_label": "",
                "hala2526": None, "orlik2026": None,
            }
            historic_players.append(item)
            player_by_name[person_key(row["name"])] = item
        item["orlik2026"] = {
            "apps": row.get("appearances", 0),
            "goals": row.get("goals", 0),
            "assists": row.get("assists", 0),
        }

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
        if season_id == SEASON_2026:
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
            "promotions": promotions.get("promotions", []),
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
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Portal data: {len(seasons)} seasons, {len(matches)} matches, {len(historic_players)} players, {len(video_by_id)} videos")


if __name__ == "__main__":
    main()
