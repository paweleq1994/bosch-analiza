#!/usr/bin/env python3
"""Discover Bosch players from source-linked PLP fixtures without guessing identity."""
from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://podlaskaliga.pl"
OUTPUT = DATA / "match_player_identities.json"
ROSTER = DATA / "player_profile_map.json"
EVIDENCE = DATA / "match_player_evidence.json"
USER_AGENT = "Bosch-Service-Tech-Car-Archive/1.0"


def verified_plp_url(url: str, prefix: str | None = None) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "podlaskaliga.pl"
        and (prefix is None or parsed.path.startswith(prefix))
    )


def fetch(url: str, json_only: bool = False):
    if not verified_plp_url(url):
        raise ValueError(f"Untrusted PLP URL: {url}")
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=23) as response:
        if json_only:
            return json.load(response)
        return response.read(1700000).decode("utf-8", "replace")


class PlayerAnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_id = None
        self.characters = []
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        href = dict(attrs).get("href") or ""
        parsed = urlsplit(unescape(href))
        query = parse_qs(parsed.query)
        if parsed.hostname != "podlaskaliga.pl" or query.get("post_type") != ["sp_player"]:
            return

        player_ids = query.get("p") or []
        if len(player_ids) != 1 or not player_ids[0].isdigit():
            return

        self.current_id = player_ids[0]
        self.characters = []

    def handle_data(self, data):
        if self.current_id is not None:
            self.characters.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_id is not None:
            name = " ".join("".join(self.characters).split())
            if len(name.split()) >= 2:
                self.anchors.append((self.current_id, name))
            self.current_id = None
            self.characters = []


def event_identity(player_id: str, urls: list[str], get=fetch):
    evidence = []
    for url in urls:
        try:
            parser = PlayerAnchorParser()
            parser.feed(get(url))
            names = {name for found_id, name in parser.anchors if found_id == player_id}
            if len(names) == 1:
                evidence.append({"source_url": url, "name": next(iter(names))})
            if len(evidence) >= 3:
                break
        except (HTTPError, OSError, ValueError):
            continue

    names = {entry["name"] for entry in evidence}
    if len(names) == 1:
        return next(iter(names)), evidence
    return None, evidence


def resolve(evidence: dict, roster: dict, previous: dict, get=fetch) -> dict:
    by_id = {}
    for match in evidence.get("matches") or []:
        url = str(match.get("source_url") or "")
        if not verified_plp_url(url, "/wydarzenie/"):
            continue
        for player in match.get("players") or []:
            player_id = str(player.get("player_id") or "")
            if player_id.isdigit():
                urls = by_id.setdefault(player_id, [])
                if url not in urls:
                    urls.append(url)

    output = dict(previous.get("players") or {})
    unresolved = {}
    known = set(roster) | set(output)

    for player_id, urls in sorted(by_id.items(), key=lambda item: int(item[0])):
        if player_id in known:
            continue

        api_url = f"{BASE}/wp-json/sportspress/v2/players/{player_id}"
        try:
            payload = get(api_url, json_only=True)
            if str(payload.get("id")) != player_id or payload.get("status") != "publish":
                raise ValueError("API returned mismatching or unpublished player")
            name = unescape(str((payload.get("title") or {}).get("rendered") or "")).strip()
            public_url = str(payload.get("link") or "")
            if len(name.split()) < 2 or not verified_plp_url(public_url, "/zawodnik/"):
                raise ValueError("API returned missing or untrusted profile")
            output[player_id] = {
                "name": name,
                "public_url": public_url,
                "source": "plp_sportspress_player_id",
                "evidence_urls": urls[:3],
                "verified": True,
            }
            continue
        except (HTTPError, OSError, ValueError, AttributeError, TypeError):
            pass

        name, details = event_identity(player_id, urls, get=get)
        if name:
            output[player_id] = {
                "name": name,
                "public_url": "",
                "source": "plp_official_match_page_linked_id",
                "evidence_urls": [item["source_url"] for item in details],
                "verified": True,
            }
        else:
            unresolved[player_id] = {
                "reason": "No unique source-linked player name in public match HTML or public API",
                "match_urls": urls,
                "candidate_names": sorted({item["name"] for item in details}),
            }

    return {"players": output, "unresolved": unresolved}


def update_profile_map(resolved: dict, mapping: dict) -> dict:
    result = dict(mapping)
    for player_id, identity in resolved.get("players", {}).items():
        if not player_id.isdigit() or not identity.get("verified"):
            continue
        previous = result.get(player_id) or {}
        prior_name = str(previous.get("resolved_name") or "").strip()
        name = identity["name"]
        if prior_name and prior_name != name:
            # Never silently repoint a numeric PLP identity.
            raise ValueError(f"Conflicting name for PLP ID {player_id}: {prior_name} / {name}")
        public_url = identity["public_url"]
        result[player_id] = {
            **previous,
            "player_id": int(player_id),
            "resolved_name": name,
            "profile_url": public_url or previous.get("profile_url") or "",
            "public": bool(public_url),
            "source": identity["source"],
            "source_match_urls": identity["evidence_urls"],
        }
    return result


def write_json(path: Path, data: dict) -> bool:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    previous = (
        json.loads(OUTPUT.read_text(encoding="utf-8"))
        if OUTPUT.exists() else {"players": {}}
    )
    result = resolve(evidence, roster, previous)
    updated = update_profile_map(result, roster)
    write_json(OUTPUT, result)
    write_json(ROSTER, updated)
    print(
        f"Source-verified new player identities: {len(result['players'])}; "
        f"unresolved IDs: {len(result['unresolved'])}",
        flush=True,
    )
    for player_id, value in sorted(result["players"].items()):
        print(f"VERIFIED {player_id}: {value['name']} [{value['source']}]", flush=True)
    for player_id, value in sorted(result["unresolved"].items()):
        print(f"UNRESOLVED {player_id}: {value['reason']}", flush=True)


if __name__ == "__main__":
    main()
