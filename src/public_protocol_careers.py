"""Recover protocol minima and explicitly attributed, club-scope-confirmed careers."""
from collections import defaultdict
from html import unescape
import re

from collect_match_player_evidence import event_stat, official_url
from player_identity import person_key

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
    bosch_coverage = source.get("bosch_event_coverage") or {}
    bosch_event_ids = set(map(str, bosch_coverage.get("event_ids") or []))
    bosch_coverage_verified = bool(bosch_event_ids) and (
        bosch_coverage.get("team_id") == "6951"
        and bosch_coverage.get("total_events") == len(bosch_event_ids)
        and bosch_coverage.get("events_with_bosch_performance") == len(bosch_event_ids)
        and bosch_coverage.get("unknown_player_ids") == []
    )
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
                       "bosch_public_events_reviewed": len(bosch_event_ids),
                       "bosch_protocol_coverage_verified": bosch_coverage_verified and all(row["event_id"] in bosch_event_ids for row in review["matches"]),
                       "limitation": "Publiczne protokoły nie obejmują usuniętych lub prywatnych wydarzeń ani nieznanych dawnych identyfikatorów osoby."})
        review["matches"].sort(key=lambda e: (e["date"], e["event_id"]))
    return dict(output)


def reconstruct_confirmed_bosch_career(player, confirmation):
    """Lift a protocol minimum only with explicit, identity-bound club-scope evidence."""
    pid = str(player["id"])
    member = (confirmation.get("players") or {}).get(pid)
    if not member or player.get("career_totals"):
        return False
    if (confirmation.get("source_type") != "user_confirmation"
            or confirmation.get("scope") != "entire_plp_career_only_bosch"
            or str(confirmation.get("team_id")) != "6951"
            or not confirmation.get("confirmed_at") or not confirmation.get("statement")
            or person_key(member["name"]) != person_key(player["name"])):
        raise ValueError("Invalid Bosch-only career scope confirmation")
    review = player.get("public_protocol_review") or {}
    totals = review.get("totals")
    coverage = player.get("season_coverage") or {}
    if (not totals or not review.get("matches") or not review.get("bosch_protocol_coverage_verified")
            or any(row["team_id"] != "6951" for row in review["matches"])
            or any(row["date"] > confirmation["confirmed_at"] for row in review["matches"])
            or totals != review.get("bosch_totals")
            or any(player.get(field) != value for field, value in totals.items())
            or any(coverage.get("unassigned", {}).get(field) != 0 for field in totals)
            or coverage.get("by_season") != totals):
        # New seasons can arrive before this dated archive is refreshed.
        # Keep the minimum visible instead of freezing synchronization or claiming a stale full career.
        review["reconstruction_pending"] = "Bilans lub zakres drużyn wymaga ponownego uzgodnienia z datowanym przeglądem protokołów."
        return False
    scope = {key: confirmation[key] for key in
             ("source_type", "scope", "team_id", "confirmed_at", "statement")}
    note = ("Kariera zrekonstruowana z publicznych protokołów PLP. Użytkownik potwierdził "
            f"{scope['confirmed_at']}, że zawodnik grał w PLP wyłącznie w Boschu. Liczby pochodzą z protokołów; "
            "zakres klubowy z tego potwierdzenia. Aktualny publiczny profil pozostaje niedostępny.")
    player["career_totals"] = {**totals, "source": "Rekonstrukcja: protokoły PLP i potwierdzony zakres klubowy",
        "reconstructed": True, "as_of": confirmation["confirmed_at"], "teams": 1, "team_id": "6951", "scope_confirmation": scope,
        "source_urls": list(dict.fromkeys(row["source_url"] for row in review["matches"])),
        "protocol_captured_at": review["captured_at"], "note": note}
    player["bosch_totals"] = dict(totals)
    player["stats_minimum"] = False
    player["stats_source"] = "Rekonstrukcja wszystkich występów Boscha z protokołów PLP"
    review.update({"scope": "reconstructed_career_with_confirmed_club_scope",
                   "whole_career_verified": True, "scope_confirmation": scope,
                   "reconstruction_note": note})
    return True
