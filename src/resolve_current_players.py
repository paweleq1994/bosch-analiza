#!/usr/bin/env python3
"""Resolve new season leader names to verified, stable SportsPress player IDs."""
from __future__ import annotations

from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import sys
import unicodedata

from player_identity import has_bosch_season, match_public_profile, person_key

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "player_profile_map.json"
ROSTERS = ROOT / "data" / "player_rosters.json"
RECAP = ROOT / "data" / "orlik_2026_recap.json"
SPORTSPRESS = "https://podlaskaliga.pl/wp-json/sportspress/v2"
USER_AGENT = "Bosch-Scouting/1.0"
POST_ID_PATTERN = re.compile(r'(?:postid-|id=["\\\']post-|[?&]p=)(\d+)')
TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def fetch_json(url: str):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        return json.load(response)


def fetch_html(url: str) -> str:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def profile_name(payload: dict) -> str:
    title = payload.get("title") or ""
    if isinstance(title, dict):
        title = title.get("rendered") or ""
    return unescape(re.sub(r"<[^>]*>", " ", str(title))).strip()


def verified_profile(player_id: object, expected_name: str, fetch=fetch_json) -> dict | None:
    if not str(player_id).isdigit():
        return None

    player_id = int(player_id)
    payload = fetch(f"{SPORTSPRESS}/players/{player_id}")
    if person_key(profile_name(payload)) != person_key(expected_name):
        return None

    if not has_bosch_season(payload):
        return None

    profile_url = str(payload.get("link") or "")
    if not profile_url.startswith("https://podlaskaliga.pl/zawodnik/"):
        return None

    return {
        "player_id": player_id,
        "profile_url": profile_url,
        "public": True,
        "resolved_name": profile_name(payload),
        "source": "verified_current_roster",
    }


def candidate_slugs(name: str) -> list[str]:
    text = unicodedata.normalize("NFD", name.lower().replace("ł", "l"))
    ascii_name = "".join(character for character in text if unicodedata.category(character) != "Mn")
    tokens = re.sub(r"[^a-z0-9 ]", "", ascii_name).split()
    return ["-".join(reversed(tokens))] if len(tokens) == 2 else []


def find_profile(name: str, fetch=fetch_json, fetch_page=fetch_html) -> tuple[str, dict] | None:
    words = name.split()
    if len(words) < 2:
        return None

    surname = words[-1]
    url = SPORTSPRESS + "/players?" + urlencode({"search": surname, "per_page": 100})
    candidates: dict[str, dict] = {}

    try:
        rows = fetch(url)
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue

                if person_key(profile_name(row)) != person_key(name):
                    continue

                try:
                    verified = verified_profile(row.get("id"), name, fetch)
                    if verified:
                        candidates[str(verified["player_id"])] = verified
                except Exception:
                    continue
    except Exception:
        pass

    if not candidates:
        for slug in candidate_slugs(name):
            try:
                html = fetch_page(f"https://podlaskaliga.pl/zawodnik/{slug}/")
                match = TITLE_PATTERN.search(html)
                if not match:
                    continue

                html_title = re.split(r"\s+[–-]\s+Podlaska Liga", unescape(re.sub(r"<[^>]*>", " ", match.group(1))), maxsplit=1)[0]
                if person_key(html_title) != person_key(name):
                    continue

                shortlink = re.search(r'<link[^>]+rel=["\\\']shortlink["\\\'][^>]+href=["\\\'][^"\\\']*[?&]p=(\d+)', html, re.I)
                player_ids = {shortlink.group(1)} if shortlink else set(POST_ID_PATTERN.findall(html))
                if len(player_ids) != 1:
                    continue

                verified = verified_profile(next(iter(player_ids)), name, fetch)
                if verified:
                    candidates[str(verified["player_id"])] = verified
            except Exception:
                continue

    return next(iter(candidates.items())) if len(candidates) == 1 else None


def resolve(profiles: dict, leaders: list[dict], find=find_profile) -> tuple[dict, list[str]]:
    output = dict(profiles)
    warnings = []

    for row in leaders:
        name = str(row.get("name") or "").strip()
        if not name or match_public_profile(name, output):
            continue

        try:
            matched = find(name)
        except Exception as error:
            warnings.append(f"{name}: {type(error).__name__}")
            continue

        if matched:
            player_id, profile = matched
            existing = output.get(player_id)
            if existing and existing.get("public") and person_key(existing.get("resolved_name")) != person_key(name):
                warnings.append(f"{name}: ID collision {player_id}")
                continue
            output[player_id] = profile
        else:
            warnings.append(f"{name}: no verified PLP ID")

    return output, warnings


def roster_season(season, lists):
    """Read membership, including zeros, only in the team's actual competition.

    SportsPress also lists team members with zeroes in the other division.
    Those rows must never establish participation in that competition.
    """
    sid = str(season.get("plp_id") or season["id"])
    leagues = set(map(str, season.get("league_ids") or []))
    if not leagues:
        raise ValueError("Season has no verified league ID")
    members = {}
    for source in lists:
        if list(map(str, source.get("seasons") or [])) != [sid]:
            continue
        if not leagues.intersection(map(str, source.get("leagues") or [])):
            continue
        data = source.get("data")
        if not isinstance(data, dict):
            continue
        for pid, stat in data.items():
            if not str(pid).isdigit() or str(pid) == "0" or not isinstance(stat, dict):
                continue
            if str(stat.get("team")) != "6951" or not stat.get("name"):
                continue
            entry = members.setdefault(str(pid), {"name": clean_roster_name(stat["name"]),
                "listed_apps": None, "source_urls": []})
            if person_key(entry["name"]) != person_key(stat["name"]):
                raise ValueError(f"Roster identity collision: {pid}")
            apps = str(stat.get("appearances", ""))
            if apps.isdigit():
                entry["listed_apps"] = max(entry["listed_apps"] or 0, int(apps))
            url = source.get("link") or ""
            if url.startswith("https://podlaskaliga.pl/lista/") and url not in entry["source_urls"]:
                entry["source_urls"].append(url)
    if not members:
        raise ValueError("No source-linked Bosch roster")
    return {"plp_id": sid, "league_ids": sorted(leagues), "members": members}


def clean_roster_name(value):
    return unescape(re.sub(r"<[^>]*>", " ", str(value))).strip()


def refresh_rosters(seasons, previous, fetch=fetch_json):
    result = dict(previous)
    warnings = []
    for season in seasons:
        try:
            rows, page = [], 1
            while True:
                url = SPORTSPRESS + "/lists?" + urlencode({"seasons": season.get("plp_id") or season["id"], "per_page": 100, "page": page})
                batch = fetch(url)
                if not isinstance(batch, list):
                    raise ValueError("Invalid list response")
                rows.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            result[str(season["id"])] = roster_season(season, rows)
        except Exception as error:
            warnings.append(f"roster {season['id']}: {type(error).__name__}: {error}")
    return result, warnings


def main() -> None:
    existing = json.loads(PROFILES.read_text(encoding="utf-8"))
    recap = json.loads(RECAP.read_text(encoding="utf-8"))
    goal_evidence = json.loads((ROOT / "data" / "goal_evidence.json").read_text(encoding="utf-8"))
    extra_scorers = [
        {"name": entry["name"]}
        for entry in goal_evidence.get("players", [])
        if not entry.get("player_id")
    ]
    profiles, warnings = resolve(existing, recap.get("player_leaders", []) + extra_scorers)
    seasons = json.loads((ROOT / "data/league_updates.json").read_text(encoding="utf-8"))["season_rows"]
    old_rosters = json.loads(ROSTERS.read_text(encoding="utf-8")) if ROSTERS.exists() else {}
    rosters, roster_warnings = refresh_rosters(seasons, old_rosters)
    warnings.extend(roster_warnings)
    ROSTERS.write_text(json.dumps(rosters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for record in rosters.values():
        for pid, member in record["members"].items():
            if pid not in profiles:
                try:
                    public_profile = verified_profile(pid, member["name"])
                except Exception:
                    public_profile = None
                profiles[pid] = public_profile or {"player_id": int(pid), "resolved_name": member["name"],
                    "profile_url": "", "public": False, "source": "verified_official_roster",
                    "evidence_urls": member["source_urls"]}
    rendered = json.dumps(profiles, ensure_ascii=False, indent=2) + "\n"

    if PROFILES.read_text(encoding="utf-8") != rendered:
        PROFILES.write_text(rendered, encoding="utf-8")

    print("PLP current player identities:", len(profiles), "profiles;", len(warnings), "unresolved")
    for warning in warnings:
        print("PLP identity warning:", warning, file=sys.stderr)


if __name__ == "__main__":
    main()
