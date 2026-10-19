#!/usr/bin/env python3
"""Crawl public PLP sitemap indexes and confirm archived player URLs by WordPress post ID.

Sitemap slug similarities are candidates only. They do not prove identity.
HTTP 401/404 and unavailable sources are recorded explicitly.
"""
from __future__ import annotations

from html import unescape
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from player_identity import person_key

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "plp_source_crawl.json"
REPORT = ROOT / "reports/plp-source-crawl.md"
PROFILES = DATA / "player_profile_map.json"
PORTAL = ROOT / "docs/assets/data.json"
ROOT_URL = "https://podlaskaliga.pl"
MAX_INDEXES = 40
MAX_LISTED = 30000
SEED_PATHS = (
    "/wp-sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap.xml",
    "/player-sitemap.xml",
    "/wp-sitemap-posts-sp_player-1.xml",
)


def trusted(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname in {
        "podlaskaliga.pl", "www.podlaskaliga.pl",
    }


def fetch(url: str) -> tuple[int, bytes]:
    if not trusted(url):
        raise ValueError("Untrusted sitemap URL")
    try:
        with urlopen(Request(url, headers={"User-Agent": "BoschArchive/1.0"}), timeout=11) as result:
            return result.status, result.read(2000001)
    except HTTPError as error:
        return error.code, b""
    except (URLError, TimeoutError):
        return 0, b""


def parse_sitemap(payload: bytes) -> tuple[list[str], dict[str, list[str]]]:
    if len(payload) > 2000000:
        raise ValueError("Oversized sitemap")
    root = ET.fromstring(payload)
    kind = root.tag.rsplit("}", 1)[-1].lower()
    if kind not in {"sitemapindex", "urlset"}:
        raise ValueError("Unexpected sitemap XML root")

    nested = []
    found = {}

    for node in root:
        loc_node = next(
            (child for child in node if child.tag.rsplit("}", 1)[-1] == "loc"), None,
        )
        if loc_node is None or not loc_node.text or not trusted(loc_node.text.strip()):
            continue

        location = loc_node.text.strip()
        if kind == "sitemapindex":
            nested.append(location)
            continue

        images = [
            entry.text.strip()
            for image in node
            if image.tag.rsplit("}", 1)[-1] == "image"
            for entry in image
            if entry.tag.rsplit("}", 1)[-1] == "loc"
            and entry.text
            and trusted(entry.text.strip())
        ]
        found[location] = images

    return nested, found


def scan(get=fetch, pause=lambda: time.sleep(0.15)) -> dict:
    queue = [ROOT_URL + path for path in SEED_PATHS]
    encountered = set()
    pages = {}
    status = []

    while queue and len(encountered) < MAX_INDEXES and len(pages) < MAX_LISTED:
        url = queue.pop(0)
        if url in encountered or not trusted(url):
            continue
        encountered.add(url)
        code, response = get(url)
        entry = {"url": url, "http_status": code}
        status.append(entry)
        if code == 200:
            try:
                nested, listed = parse_sitemap(response)
                queue.extend(candidate for candidate in nested if candidate not in encountered)
                pages.update(listed)
                entry["listed"] = len(listed)
                entry["children"] = len(nested)
            except (ValueError, ET.ParseError) as error:
                entry["error"] = str(error)
        pause()

    return {"sitemaps": status, "pages": pages, "truncated": bool(queue) or len(pages) >= MAX_LISTED}


def discover_players(index: dict, players: list[dict], get=fetch) -> dict:
    urls = [
        url for url in index["pages"]
        if urlsplit(url).path.startswith("/zawodnik/")
    ]
    identified = {}
    missing = {}

    for player in players:
        player_id = str(player["id"])
        if player.get("profile_url"):
            continue
        expected_name = person_key(player["name"])
        candidates = [
            url for url in urls
            if person_key(urlsplit(url).path.strip("/").split("/")[-1].replace("-", " ")) == expected_name
        ]
        unique_urls = sorted(set(candidates))
        verified_url = None
        status = []

        for url in unique_urls[:4]:
            code, body = get(url)
            signature = set(re.findall(rb"\bpostid-(\d+)\b", body))
            if code == 200 and player_id.encode("ascii") in signature:
                verified_url = url
                break
            status.append({"url": url, "http_status": code, "verified_post_id": False})

        if verified_url:
            identified[player_id] = {
                "name": player["name"],
                "url": verified_url,
                "proof": "WordPress body postid equals verified PLP player ID",
                "sitemap_images": index["pages"].get(verified_url) or [],
            }
        else:
            missing[player_id] = {
                "name": player["name"],
                "candidate_urls": unique_urls,
                "checks": status,
                "evidence_urls": ((player.get("verified_identity_source") or {}).get("evidence_urls") or [])[:3],
                "reason": (
                    "Sitemap does not prove numeric player identity"
                    if unique_urls
                    else "No public sitemap could be downloaded; player existence cannot be ruled out"
                    if not index.get("pages") and not any(
                        item.get("http_status") == 200
                        for item in index.get("sitemaps") or []
                    )
                    else "No matching player URL in the accessible sitemap index"
                ),
            }

    return {"verified": identified, "missing": missing}


def render_report(index: dict, identities: dict) -> str:
    report = [
        "# PLP — audyt publicznych map witryny i archiwalnych profili Boscha",
        "",
        "Wyszukiwanie objęło wskazane niżej mapy XML i ich dostępne podrzędne strony.",
        "Przypisanie profilu wymaga zgodności oficjalnego WordPress post ID z ID PLP.",
        "Podobieństwo nazwiska lub miniatury nie potwierdza tożsamości.",
        "Kod HTTP 0 oznacza problem połączenia, a nie dowód nieistnienia strony.",
        "",
        f"- Sitemapy sprawdzone: **{len(index['sitemaps'])}**",
        f"- Publiczne adresy z sitemap: **{len(index['pages'])}**",
        f"- Dopasowania potwierdzone numerem postu: **{len(identities['verified'])}**",
        f"- Profile nadal bez publicznego źródła: **{len(identities['missing'])}**",
        f"- Przegląd ograniczony limitem: **{'TAK' if index['truncated'] else 'NIE'}**",
        "",
        "## Sprawdzone indeksy XML",
        "",
        "| Sitemap | HTTP | Liczba URL |",
        "|---|---:|---:|",
    ]
    for row in index["sitemaps"]:
        report.append(
            f"| [{row['url']}]({row['url']}) | {row['http_status']} | {row.get('listed', 0)} |"
        )

    report += ["", "## Profile znalezione i potwierdzone", ""]
    if not identities["verified"]:
        report.append("Brak nowych, w pełni potwierdzonych źródeł.")
    for player_id, item in identities["verified"].items():
        report.append(f"- **{item['name']} (ID {player_id})** — [{item['url']}]({item['url']})")

    report += ["", "## Profile bez dostępnego, potwierdzonego publicznego adresu", ""]
    for player_id, item in identities["missing"].items():
        report.append(
            f"- **{item['name']} (ID {player_id})** — {item['reason']}. "
            f"Kandydackie adresy: {len(item['candidate_urls'])}; "
            f"źródła meczowe: {len(item['evidence_urls'])}"
        )

    report += [
        "",
        "## Ograniczenia",
        "",
        "Nieosiągalne w publicznym serwisie profile (401/404) nie mogą być",
        "odtwarzane jako pełne kariery bez osobnego źródła. Dane o występach",
        "w meczach i osiągniętych golach pozostają w archiwum protokołów.",
        "Zdjęcia z sitemap traktujemy jako kandydatów, nie potwierdzone portrety.",
        "",
    ]
    return "\n".join(report)


def save(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != payload:
        path.write_text(payload, encoding="utf-8")


def main() -> None:
    db = json.loads(PORTAL.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
    index = scan()
    recovered = discover_players(index, db["players"])
    for player_id, item in recovered["verified"].items():
        row = profiles.get(player_id) or {}
        profiles[player_id] = {
            **row,
            "resolved_name": item["name"],
            "profile_url": item["url"],
            "public": True,
            "source": "plp_sitemap_verified_post_id",
        }

    save(PROFILES, json.dumps(profiles, ensure_ascii=False, indent=2) + "\n")
    save(OUTPUT, json.dumps({
        "sitemaps": index["sitemaps"],
        "listed_url_count": len(index["pages"]),
        "truncated": index["truncated"],
        "verified": recovered["verified"],
        "missing": recovered["missing"],
    }, ensure_ascii=False, indent=2) + "\n")
    save(REPORT, render_report(index, recovered))
    print(
        f"PLP sitemap sources: {len(index['pages'])} URLs; "
        f"newly proven profiles={len(recovered['verified'])}; "
        f"still missing={len(recovered['missing'])}",
        flush=True,
    )


if __name__ == "__main__":
    main()
