"""Resolve public PLP player identities without merging unrelated people."""
from __future__ import annotations

from html import unescape
import re
import unicodedata


def person_key(value: object) -> str:
    text = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    text = unicodedata.normalize("NFD", text.lower().replace("ł", "l"))
    ascii_name = "".join(char for char in text if unicodedata.category(char) != "Mn")
    tokens = re.sub(r"[^a-z0-9]+", " ", ascii_name).split()
    return " ".join(sorted(token for token in tokens if token not in {"gk", "bramkarz"}))


def legacy_player_id(value: object) -> str:
    text = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    text = unicodedata.normalize("NFD", text.lower())
    ascii_name = "".join(char for char in text if unicodedata.category(char) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return "new-" + slug


def match_public_profile(name: str, profiles: dict) -> tuple[str, dict] | None:
    key = person_key(name)
    if not key:
        return None

    matches = [
        (str(player_id), profile)
        for player_id, profile in profiles.items()
        if str(player_id).isdigit()
        and profile.get("public")
        and person_key(profile.get("resolved_name")) == key
    ]
    return matches[0] if len(matches) == 1 else None


def has_bosch_season(profile: dict) -> bool:
    for season_rows in (profile.get("statistics") or {}).values():
        if not isinstance(season_rows, dict):
            continue

        for season_id, stats in season_rows.items():
            if str(season_id) in {"0", "-1"} or not isinstance(stats, dict):
                continue

            if "bosch-service-tech-car" in str(stats.get("team") or "").lower():
                return True

    return False
