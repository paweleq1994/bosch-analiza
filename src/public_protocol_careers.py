"""Recover source-linked career minima without claiming deleted profiles are complete."""
from collections import defaultdict
from html import unescape
import re

from collect_match_player_evidence import event_stat, official_url

FIELDS = {"goals": "goals", "assists": "assists", "motm": "pikarzmeczu",
          "yellow": "yellowcards", "red": "redcards"}


def review_public_protocols(source):
    if not source:
        return {}
    total = source.get("public_events_total")
    pages = source.get("page_counts") or {}
    if (type(total) is not int or total <= 0 or source.get("unique_event_ids") != total
            or len(pages) != source.get("pages") or sum(pages.values()) != total):
        raise ValueError("Incomplete public protocol archive review")
    targets = set(source.get("target_player_ids") or [])
    output = defaultdict(lambda: {"matches": [], "totals": dict.fromkeys(("apps", *FIELDS), 0),
                                  "bosch_totals": dict.fromkeys(("apps", *FIELDS), 0)})
    seen = set()
    for event in source.get("records") or []:
        eid = str(event.get("id"))
        if eid in seen or not official_url(event.get("link")) or event.get("status") != "publish":
            raise ValueError("Invalid or duplicate public career protocol")
        if event.get("api_url") != "https://podlaskaliga.pl/wp-json/sportspress/v2/events/" + eid:
            raise ValueError("Career protocol API identity mismatch")
        seen.add(eid)
        appeared = set()
        for team, players in event.get("performance", {}).items():
            if str(team) not in set(map(str, event.get("teams") or [])):
                raise ValueError("Career protocol team mismatch")
            for pid, raw in players.items():
                if pid not in targets:
                    raise ValueError("Unexpected career identity")
                if raw.get("status") not in {"lineup", "sub", "substitute"}:
                    continue
                if pid in appeared:
                    raise ValueError("Career identity appears on both teams")
                appeared.add(pid)
                stats = {"apps": 1, **{field: event_stat(raw.get(key)) for field, key in FIELDS.items()}}
                if any(type(v) is not int or v < 0 for v in stats.values()):
                    raise ValueError("Uncertain career protocol statistics")
                review = output[pid]
                for field, value in stats.items():
                    review["totals"][field] += value
                    if str(team) == "6951":
                        review["bosch_totals"][field] += value
                review["matches"].append({"event_id": eid, "date": event["date"][:10],
                    "title": unescape(re.sub("<[^>]*>", "", event["title"]["rendered"])),
                    "team_id": str(team), "season_ids": event.get("seasons") or [],
                    "source_url": event["link"], **stats})
    for review in output.values():
        review.update({"scope": "minimum_from_all_published_protocols", "whole_career_verified": False,
                       "archive_events_reviewed": total, "captured_at": source["captured_at"],
                       "limitation": "Publiczne protokoły nie obejmują usuniętych lub prywatnych wydarzeń ani nieznanych dawnych identyfikatorów osoby."})
        review["matches"].sort(key=lambda e: (e["date"], e["event_id"]))
    return dict(output)
