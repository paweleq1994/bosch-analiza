#!/usr/bin/env python3
"""Synchronize public YouTube Atom feeds and match new videos conservatively."""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "video_channels.json"
OVERRIDES = ROOT / "data" / "video_updates.json"
SITE = ROOT / "docs" / "assets" / "data.json"
AGENT = "BoschKnowledgeBase/1.0 (+https://github.com/paweleq1994/bosch-analiza)"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def fetch(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    request = Request(url, headers={"User-Agent": AGENT})
    with urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())
    items = []
    for entry in root.findall("atom:entry", ATOM):
        video_id = entry.findtext("yt:videoId", default="", namespaces=ATOM)
        if not VIDEO_ID.fullmatch(video_id):
            continue
        items.append({
            "id": video_id,
            "title": unescape(entry.findtext("atom:title", default="", namespaces=ATOM)),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "date": entry.findtext("atom:published", default="", namespaces=ATOM)[:10],
            "channel": entry.findtext("atom:author/atom:name", default="", namespaces=ATOM),
            "segment": "",
            "match_id": None,
            "status": "unmatched",
        })
    return items


def match_video(video: dict, matches: list[dict]) -> str | None:
    title = normalize(video["title"])
    if not any(name in title for name in ("bosch", "tech car", "techcar")):
        return None
    possible = []
    for match in matches:
        rival = normalize(match["opponent"])
        if len(rival) < 5 or rival not in title:
            continue
        score = f"{match['gf']}:{match['ga']}"
        reverse_score = f"{match['ga']}:{match['gf']}"
        has_score = bool(re.search(r"\b" + re.escape(score) + r"\b", video["title"]))
        has_reverse_score = bool(re.search(r"\b" + re.escape(reverse_score) + r"\b", video["title"]))
        if has_score or has_reverse_score:
            possible.append(match["id"])
    return possible[0] if len(possible) == 1 else None


def main() -> None:
    config = load(SOURCES, {"channels": []})
    updates = load(OVERRIDES, {"videos": [], "manual_bindings": {}})
    site = load(SITE, {"matches": []})
    matches = site.get("matches") or []
    existing = {video["id"]: video for video in updates.get("videos", [])}
    historic = {video.get("id") for video in site.get("videos", [])}
    errors = []
    detected = 0
    for source in config.get("channels", []):
        channel_id = source.get("channel_id", "")
        if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id):
            errors.append(f"Invalid channel id for {source.get('name', '?')}")
            continue
        try:
            items = fetch(channel_id)
        except Exception as error:
            errors.append(f"{source.get('name', channel_id)}: {type(error).__name__} {error}")
            continue
        for video in items:
            if video["id"] in existing or video["id"] in historic:
                continue
            associated_match = match_video(video, matches)
            if associated_match:
                video["match_id"] = associated_match
                video["status"] = "matched_auto"
            else:
                video["status"] = "needs_review"
            existing[video["id"]] = video
            detected += 1
    if errors:
        print("Feed errors:", "; ".join(errors), file=sys.stderr)
    if errors and not config.get("channels"):
        raise RuntimeError("Video channels are not configured")
    updated = {
        "videos": sorted(existing.values(), key=lambda row: (row.get("date") or "", row["id"])),
        "manual_bindings": updates.get("manual_bindings", {}),
    }
    rendered = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if not OVERRIDES.exists() or rendered != OVERRIDES.read_text(encoding="utf-8"):
        OVERRIDES.write_text(rendered, encoding="utf-8")
    print(f"Video scan: {detected} new videos, {len(errors)} source warnings")


if __name__ == "__main__":
    main()
