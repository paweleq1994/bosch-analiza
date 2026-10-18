#!/usr/bin/env python3
"""Discover public historical PLP media, including detached WordPress attachments."""
from __future__ import annotations

from datetime import date
from html import unescape
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
import json
import os
import re
import unicodedata

from plp_photo_archive import get, valid

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "assets" / "data.json"
MANIFEST_PATH = ROOT / "data" / "media_manifest.json"
INDEX_PATH = ROOT / "data" / "media_discovery.json"
MEDIA_FIELDS = "id,post,source_url,mime_type,slug,title,alt_text,caption,description,date"
ALLOWED_EXTRAS = frozenset({
    "foto", "photo", "zdjecie", "portret", "portrait", "profilowe", "player", "profile",
})


def normalize(value: object) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    text = unicodedata.normalize("NFD", text.lower().replace("ł", "l"))
    text = "".join(letter for letter in text if unicodedata.category(letter) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def rendered(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("rendered") or "")

    return str(value or "")


def player_tokens(player_name: str) -> list[str]:
    return [
        word
        for word in normalize(player_name).split()
        if word not in {"gk", "bramkarz"}
    ]


def exact_person_label(value: str, name_tokens: list[str]) -> bool:
    tokens = normalize(value).split()

    if len(name_tokens) < 2 or len(tokens) < len(name_tokens):
        return False

    core = [
        token
        for token in tokens
        if token not in ALLOWED_EXTRAS and not token.isdigit()
    ]

    return core == name_tokens or core == list(reversed(name_tokens))


def possible_person_label(value: str, name_tokens: list[str]) -> bool:
    tokens = normalize(value).split()

    if len(name_tokens) < 2:
        return False

    return (
        all(word in tokens for word in name_tokens)
        and not exact_person_label(value, name_tokens)
    )


def classify_media(media: dict, players: list[dict]) -> tuple[list[dict], list[dict]]:
    media_id = str(media.get("id") or "")
    url = str(media.get("source_url") or "")

    if (
        not media_id.isdigit()
        or not valid(url)
        or not str(media.get("mime_type") or "").startswith("image/")
    ):
        return [], []

    filename = Path(unquote(urlsplit(url).path)).stem
    titles = {
        "filename": filename,
        "slug": str(media.get("slug") or ""),
        "title": rendered(media.get("title")),
        "alt": str(media.get("alt_text") or ""),
    }
    context = " ".join((
        rendered(media.get("caption")),
        rendered(media.get("description")),
    ))
    parent = str(media.get("post") or "")
    exact = []
    possible = []

    for player in players:
        player_id = str(player["id"])
        name_tokens = player_tokens(player["name"])

        if parent == player_id:
            evidence = "wordpress_parent"
        else:
            evidence = next((
                label
                for label, text in titles.items()
                if exact_person_label(text, name_tokens)
            ), None)

        if evidence:
            exact.append((player_id, evidence))
        elif possible_person_label(context, name_tokens):
            possible.append((player_id, "caption_or_description"))

    if len(exact) > 1:
        return [], []

    record = {
        "id": media_id,
        "url": url,
        "alt": str(media.get("alt_text") or ""),
        "published": str(media.get("date") or ""),
        "featured": False,
    }

    matches = [
        {"player_id": player_id, "evidence": evidence, "photo": record}
        for player_id, evidence in exact
    ]

    candidates = [
        {
            "player_id": player_id,
            "media_id": media_id,
            "url": url,
            "evidence": evidence,
        }
        for player_id, evidence in possible
    ]

    return matches, candidates


def scan_media(
    players: list[dict],
    previous: dict,
    fetch=get,
    max_pages: int = 10,
    current_day: str | None = None,
) -> tuple[dict, list[str]]:
    current_day = current_day or date.today().isoformat()
    state = {
        "next_page": max(1, int(previous.get("next_page") or 1)),
        "complete": bool(previous.get("complete")),
        "scanned_pages": int(previous.get("scanned_pages") or 0),
        "scanned_media": int(previous.get("scanned_media") or 0),
        "matches": list(previous.get("matches") or []),
        "candidates": list(previous.get("candidates") or []),
        "searches": int(previous.get("searches") or 0),
        "last_scan_date": previous.get("last_scan_date") or "",
        "club_scan_version": int(previous.get("club_scan_version") or 0),
        "historical_clubs_scanned": int(previous.get("historical_clubs_scanned") or 0),
    }
    warnings: list[str] = []
    previous_matches = {
        (row["player_id"], row["photo"]["id"]): row
        for row in state["matches"]
    }
    previous_candidates = {
        (row["player_id"], row["media_id"]): row
        for row in state["candidates"]
    }
    seen_ids: set[str] = set()

    def collect(rows: object) -> int:
        if not isinstance(rows, list):
            raise ValueError("Unexpected WordPress media API payload")

        new_count = 0

        for media in rows:
            if not isinstance(media, dict):
                continue

            media_id = str(media.get("id") or "")

            if media_id in seen_ids:
                continue

            seen_ids.add(media_id)
            new_count += 1
            matches, candidates = classify_media(media, players)

            for match in matches:
                previous_matches[(match["player_id"], match["photo"]["id"])] = match

            for candidate in candidates:
                previous_candidates[(candidate["player_id"], candidate["media_id"])] = candidate

        return new_count

    if state["last_scan_date"] == current_day and state["club_scan_version"] >= 2:
        return state, warnings

    unattached_players = [
        player for player in players
        if not player.get("has_photos")
        and len(player_tokens(player["name"])) >= 2
    ]

    for player in unattached_players:
        profile_url = str(player.get("profile_url") or "")
        profile_slug = urlsplit(profile_url).path.rstrip("/").split("/")[-1]
        name_tokens = player_tokens(player["name"])
        surname = normalize(profile_slug).split()[0] if profile_slug else name_tokens[0]

        try:
            rows = fetch("wp/v2/media", {
                "search": surname,
                "per_page": 100,
                "page": 1,
                "_fields": MEDIA_FIELDS,
            })
            state["searches"] += 1
            collect(rows)
        except Exception as error:
            warnings.append(f"Media search {surname}: {type(error).__name__}: {error}")

    club_players: dict[str, list[str]] = {}
    club_names: dict[str, str] = {}

    for player in unattached_players:
        for club in player.get("previous_teams") or []:
            club_name = str(club or "").strip()
            club_key = normalize(club_name)

            if not club_key or "bosch service tech car" in club_key:
                continue

            club_players.setdefault(club_key, []).append(str(player["id"]))
            club_names[club_key] = club_name

    for club_key in sorted(club_players):
        try:
            rows = fetch("wp/v2/media", {
                "search": club_names[club_key],
                "per_page": 100,
                "page": 1,
                "_fields": MEDIA_FIELDS,
            })
            state["historical_clubs_scanned"] += 1

            if not isinstance(rows, list):
                continue

            collect(rows)

            for media in rows:
                if not isinstance(media, dict):
                    continue

                media_id = str(media.get("id") or "")
                media_url = str(media.get("source_url") or "")

                if not media_id.isdigit() or not valid(media_url):
                    continue

                if not str(media.get("mime_type") or "").startswith("image/"):
                    continue

                metadata = " ".join((
                    Path(unquote(urlsplit(media_url).path)).stem,
                    str(media.get("slug") or ""),
                    rendered(media.get("title")),
                    rendered(media.get("caption")),
                    rendered(media.get("description")),
                    str(media.get("alt_text") or ""),
                ))

                if club_key not in normalize(metadata):
                    continue

                for player_id in club_players[club_key]:
                    previous_candidates[(player_id, media_id)] = {
                        "player_id": player_id,
                        "media_id": media_id,
                        "url": media_url,
                        "evidence": "historical_team_archive",
                        "team": club_names[club_key],
                    }
        except Exception as error:
            warnings.append(f"Previous club media {club_names[club_key]}: {type(error).__name__}: {error}")

    state["club_scan_version"] = 2

    if not state["complete"]:
        for page in range(state["next_page"], state["next_page"] + max_pages):
            try:
                rows = fetch("wp/v2/media", {
                    "per_page": 100,
                    "page": page,
                    "_fields": MEDIA_FIELDS,
                })

                if not isinstance(rows, list):
                    raise ValueError("Unexpected WordPress archive response")

                if not rows:
                    state["complete"] = True
                    break

                state["scanned_media"] += collect(rows)
                state["scanned_pages"] += 1
                state["next_page"] = page + 1

                if len(rows) < 100:
                    state["complete"] = True
                    break

            except HTTPError as error:
                if error.code == 400 and page > 1:
                    state["complete"] = True
                else:
                    warnings.append(f"Media archive page {page}: HTTP {error.code}")

                break
            except Exception as error:
                warnings.append(f"Media archive page {page}: {type(error).__name__}: {error}")
                break

    state["matches"] = sorted(
        previous_matches.values(),
        key=lambda item: (item["player_id"], int(item["photo"]["id"])),
    )
    state["candidates"] = sorted(
        previous_candidates.values(),
        key=lambda item: (item["player_id"], int(item["media_id"])),
    )[:100]
    state["last_scan_date"] = current_day

    return state, warnings


def main() -> None:
    database = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else {}
    available = {
        str(subject["id"])
        for subject in manifest.get("subjects", [])
        if subject.get("kind") == "players" and subject.get("photos")
    }
    players = [
        {
            "id": str(player["id"]),
            "name": player["name"],
            "profile_url": player.get("profile_url") or "",
            "has_photos": str(player["id"]) in available,
            "previous_teams": sorted({
                str(row.get("team") or "").strip()
                for row in (player.get("career_totals") or {}).get("season_rows") or []
                if row.get("team") and normalize(row["team"]) != normalize("Bosch Service Tech-Car")
            }),
        }
        for player in database.get("players", [])
        if str(player.get("id") or "").isdigit()
    ]
    pages = max(0, min(50, int(os.environ.get("PLP_MEDIA_SCAN_PAGES", "10"))))
    result, warnings = scan_media(players, existing, max_pages=pages)
    rendered_json = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if not INDEX_PATH.exists() or INDEX_PATH.read_text(encoding="utf-8") != rendered_json:
        INDEX_PATH.write_text(rendered_json, encoding="utf-8")

    print(
        "Public PLP media discovery:",
        result["scanned_pages"], "archive pages;",
        result["scanned_media"], "archive media;",
        result["searches"], "name searches;",
        result["historical_clubs_scanned"], "historical clubs searched;",
        len(result["matches"]), "verified metadata matches;",
        len(result["candidates"]), "unverified candidates;",
        "complete:", result["complete"],
    )

    for row in result["matches"]:
        print("Verified archive match:", row["player_id"], row["photo"]["url"], row["evidence"])

    for row in result["candidates"][:10]:
        print("Unverified archive mention:", row["player_id"], row["url"])

    for warning in warnings[:15]:
        print("PLP media discovery warning:", warning)


if __name__ == "__main__":
    main()
