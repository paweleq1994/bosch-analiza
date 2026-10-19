"""Preserve original event-level PLP facts independently of player profile API."""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "match_player_evidence.json"
BOSCH_ID = "6951"
FIELDS = {
    "goals": "goals",
    "assists": "assists",
    "motm": "pikarzmeczu",
    "yellow": "yellowcards",
    "red": "redcards",
    "own_goals": "samobje",
}
MINUTE_PATTERN = re.compile(r"^\s*(\d+)(?:\s*\(([^)]*)\))?\s*$")


def event_stat(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value

    if value is None or str(value).strip() == "":
        return 0

    matched = MINUTE_PATTERN.fullmatch(str(value))

    return int(matched.group(1)) if matched else None


def official_url(value: object) -> bool:
    parsed = urlsplit(str(value or ""))
    return parsed.scheme == "https" and parsed.hostname == "podlaskaliga.pl"


def get_event(event_id: str) -> dict:
    url = f"https://podlaskaliga.pl/wp-json/sportspress/v2/events/{event_id}"

    with urlopen(Request(url, headers={"User-Agent": "BoschArchiveAudit/1.0"}), timeout=12) as response:
        return json.load(response)


def extract_match(match: dict, event: dict, canonical_aliases: dict[str, str]) -> dict:
    if str(event.get("id")) != str(match["event_id"]):
        raise ValueError(f"Wrong source event for {match['id']}")

    source_url = str(event.get("link") or "")
    expected_url = str(match["event_link"])

    if not official_url(source_url) or source_url.rstrip("/") != expected_url.rstrip("/"):
        raise ValueError(f"Unverified event link: {match['id']}")

    if BOSCH_ID not in [str(item) for item in event.get("teams") or []]:
        raise ValueError(f"Not a Bosch fixture: {match['id']}")

    if str(event.get("date") or "")[:10] != match["date"]:
        raise ValueError(f"Event date mismatch: {match['id']}")

    performances = (event.get("performance") or {}).get(BOSCH_ID)

    if not isinstance(performances, dict) or not performances:
        raise ValueError(f"Missing performance table: {match['id']}")

    result = []
    seen_ids = set()

    for original_id, entry in performances.items():
        if not str(original_id).isdigit() or str(original_id) == "0" or not isinstance(entry, dict):
            continue

        presence = str(entry.get("status") or "").strip().lower()

        if presence not in ("lineup", "sub", "substitute"):
            continue

        player_id = canonical_aliases.get(str(original_id), str(original_id))

        if player_id in seen_ids:
            raise ValueError(f"Duplicate canonical player in fixture {match['id']}: {player_id}")

        seen_ids.add(player_id)
        stats = {name: event_stat(entry.get(key)) for name, key in FIELDS.items()}
        result.append({
            "player_id": player_id,
            "source_player_id": str(original_id),
            "appearance": 1,
            **stats,
        })

    if not result:
        raise ValueError(f"No confirmed match appearances in fixture {match['id']}")

    return {
        "match_id": str(match["id"]),
        "event_id": str(match["event_id"]),
        "season_id": str(match["sid"]),
        "date": match["date"],
        "source_url": source_url,
        "players": sorted(result, key=lambda item: item["player_id"]),
    }


def collect_matches(
    matches: list[dict], source_index: dict, fetch=get_event, workers: int = 4
) -> tuple[dict, list[str]]:
    """Refresh independent verified fixtures with bounded concurrency."""
    by_id = {str(row["id"]): row for row in source_index["matches"]}
    aliases = {"13060": "7284"}

    def inspect(match: dict) -> tuple[dict | None, str | None]:
        match_id = str(match["id"])
        evidence = by_id.get(match_id)

        if not match.get("event_id") or not official_url(match.get("event_link")):
            return None, f"{match_id}: missing verified fixture/event link"

        if evidence and str(evidence["event_url"]).rstrip("/") != str(match["event_link"]).rstrip("/"):
            return None, f"{match_id}: source URL disagrees with verified archive"

        try:
            source_event = fetch(str(match["event_id"]))
            return extract_match(match, source_event, aliases), None
        except Exception as error:
            return None, f"{match_id}: {type(error).__name__}: {error}"

    sorted_matches = sorted(matches, key=lambda row: (row["date"], str(row["id"])))
    output = []
    errors = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # map preserves the deterministic archive ordering even if requests finish out of order.
        for record, error in executor.map(inspect, sorted_matches):
            if record is not None:
                output.append(record)
            if error is not None:
                errors.append(error)

    return {"matches": output}, errors

def main() -> None:
    league = json.loads((DATA / "league_updates.json").read_text(encoding="utf-8"))
    index = json.loads((DATA / "match_protocol_audit_index.json").read_text(encoding="utf-8"))
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"matches": []}
    collected, errors = collect_matches(league["matches"], index)
    previous_by_id = {row["match_id"]: row for row in previous["matches"]}
    merged = dict(previous_by_id)

    for record in collected["matches"]:
        merged[record["match_id"]] = record

    expected = {str(item["id"]) for item in index["matches"]}
    missing = sorted(expected - set(merged))
    known_fixtures = {str(item["id"]) for item in league["matches"]}
    unexpected = sorted(set(merged) - (expected | known_fixtures))

    if missing or unexpected:
        raise RuntimeError(f"Untrusted evidence: missing historical={missing}; unknown={unexpected}; errors={errors[:12]}")

    snapshot = {"matches": [merged[key] for key in sorted(merged)]}
    rendered = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"

    if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
        OUT.write_text(rendered, encoding="utf-8")

    print(f"Verified source match player evidence: {len(merged)} fixtures, refreshed={len(collected['matches'])}, errors={len(errors)}")
    for error in errors[:15]:
        print("WARNING", error)


if __name__ == "__main__":
    main()
