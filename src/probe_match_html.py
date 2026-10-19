#!/usr/bin/env python3
import json
import re
from urllib.request import Request, urlopen

BASE = "https://podlaskaliga.pl"
MATCHES = [
    ("7416", "/wydarzenie/bosch-service-tech-car-vs-fc-progress-bialystok/"),
    ("7851", "/wydarzenie/wiara-piasta-ii-vs-bosch-service-tech-car/"),
    ("9755", "/wydarzenie/bosch-service-tech-car-vs-vesta-3/"),
    ("12153", "/wydarzenie/juan-pablo-bialystok-vs-bosch-service-tech-car/"),
    ("9486", ""),
]

def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 BoschArchiveReader/1.0"}), timeout=18) as response:
        return response.read().decode("utf-8")

for match_id, path in MATCHES:
    try:
        event = json.loads(fetch(f"{BASE}/wp-json/sportspress/v2/events/{match_id}"))
        team = (event.get("performance") or {}).get("6951") or {}
        print("API", match_id, "keys", list(event), "team_count", len(team), "team_keys", list(team)[:16])
        print("API rows", json.dumps(list(team.items())[:3], ensure_ascii=False)[:1700])
        print("API attrs", json.dumps({"teams":event.get("teams"),"date":event.get("date"),"link":event.get("link")}, ensure_ascii=False)[:600])
    except Exception as error:
        print("API ERROR", match_id, type(error).__name__, str(error))

    if not path:
        continue

    try:
        html = fetch(BASE + path)
        print("HTML", match_id, "size", len(html), "table_class", re.findall(r'<table[^>]*class="[^"]*sp-event-performance[^"]*"[^>]*>', html)[:4])
        for marker in ("sp-event-performance", "data-assists", "data-appearances", "sp-event-statistics", "sp-player", "sp-event-performance-table"):
            pos = html.find(marker)
            if pos >= 0:
                print("HTML marker", match_id, marker, re.sub(r"\s+", " ", html[max(0, pos - 180):pos + 550])[:800])
        name_pos = html.find("Karolczuk Patryk")
        if name_pos > 0:
            print("HTML player", match_id, re.sub(r"\s+", " ", html[max(0, name_pos - 380):name_pos + 1700])[:2000])
    except Exception as error:
        print("HTML ERROR", match_id, type(error).__name__, str(error))
