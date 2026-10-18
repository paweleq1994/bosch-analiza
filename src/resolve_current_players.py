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

from player_identity import has_bosch_season, match_public_profile, person_key

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "player_profile_map.json"
RECAP = ROOT / "data" / "orlik_2026_recap.json"
SPORTSPRESS = "https://podlaskaliga.pl/wp-json/sportspress/v2"
USER_AGENT = "Bosch-Scouting/1.0"
POST_ID_PATTERN = re.compile(r'(?:postid-|id=["\\\']post-|[?&]p=)(\\d+)')
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
    tokens = re.sub(r"[^a-z0-9 ]", "", name.lower().replace("ł", "l")).split()
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

                html_title = re.split(r"\\s+[–-]\\s+Podlaska Liga", unescape(re.sub(r"<[^>]*>", " ", match.group(1))), maxsplit=1)[0]
                if person_key(html_title) != person_key(name):
                    continue

                player_ids = set(POST_ID_PATTERN.findall(html))
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


def main() -> None:
    existing = json.loads(PROFILES.read_text(encoding="utf-8"))
    recap = json.loads(RECAP.read_text(encoding="utf-8"))
    profiles, warnings = resolve(existing, recap.get("player_leaders", []))
    rendered = json.dumps(profiles, ensure_ascii=False, indent=2) + "\\n"

    if PROFILES.read_text(encoding="utf-8") != rendered:
        PROFILES.write_text(rendered, encoding="utf-8")

    print("PLP current player identities:", len(profiles), "profiles;", len(warnings), "unresolved")
    for warning in warnings:
        print("PLP identity warning:", warning, file=sys.stderr)


if __name__ == "__main__":
    main()
