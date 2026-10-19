#!/usr/bin/env python3
"""Probe documented public PLP endpoints before selecting a safe identity source."""
from __future__ import annotations

import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = "https://podlaskaliga.pl"
IDS = ("10321", "10603", "11895", "1594", "12285", "8655", "1960")
SOURCES = (
    ("/wp-json/sportspress/v2/players/{id}", "sports_api"),
    ("/wp-json/wp/v2/sp_player/{id}", "wp_api"),
    ("/?post_type=sp_player&p={id}", "public_post"),
    ("/?p={id}", "public_page"),
)
PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

def fetch(path: str) -> tuple[int, str, str]:
    try:
        with urlopen(Request(ROOT + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as response:
            body = response.read(220000).decode("utf-8", "replace")
            return response.status, response.geturl(), body
    except HTTPError as error:
        return error.code, error.geturl(), ""
    except (URLError, TimeoutError) as error:
        return 0, str(error), ""

def main() -> None:
    for player_id in IDS:
        for path, kind in SOURCES:
            status, url, body = fetch(path.format(id=player_id))
            title = PATTERN.search(body)
            payload = None
            if "api" in kind and status == 200:
                try:
                    data = json.loads(body)
                    payload = {
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "slug": data.get("slug"),
                        "link": data.get("link"),
                        "status": data.get("status"),
                        "keys": list(data)[:12],
                    }
                except (ValueError, AttributeError):
                    payload = "invalid"
            print(json.dumps({
                "id": player_id, "source": kind, "http": status,
                "url": url, "title": unescape(title.group(1))[:140] if title else "",
                "payload": payload,
            }, ensure_ascii=False), flush=True)
    status, url, body = fetch("/wydarzenie/vesta-vs-bosch-service-tech-car/")
    for marker in ("sp-event-performance", "sp-player", "Ciborowski", "player-10321", "10321"):
        index = body.lower().find(marker.lower())
        print(json.dumps({
            "event_marker": marker, "found": index >= 0,
            "snippet": re.sub(r"\s+", " ", body[max(0, index - 190):index + 650])[:850]
            if index >= 0 else "",
        }, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
