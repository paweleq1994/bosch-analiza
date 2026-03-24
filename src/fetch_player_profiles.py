from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
import json
import re
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
BOSCH_PATH = ROOT / "data" / "bosch_service_tech_car_data_v3.json"
PROMO_PATH = ROOT / "data" / "promoted_teams_analysis.json"
OUT_PATH = ROOT / "data" / "player_profile_map.json"
EVENT_CACHE_DIR = ROOT / "data" / "profile_cache" / "events"
USER_AGENT = "Mozilla/5.0"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
ROSTER_LINK_RE = re.compile(
    r'<a href="(https://podlaskaliga\.pl/zawodnik/[^"]+/)".*?<span class="player-name">(.*?)</span>',
    re.I | re.S,
)
EVENT_PLAYER_RE = re.compile(
    r'<a href="https://podlaskaliga\.pl/\?[^"]*post_type=sp_player[^"]*p=(\d+)[^"]*">(.*?)</a>',
    re.I | re.S,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_profile_name(value: object) -> str:
    text = unescape(str(value or "")).strip()
    text = re.sub(r"\s*[–-]\s*Podlaska Liga.*$", "", text, flags=re.I)
    return text.strip()


def clean_html_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split()).strip()


def gather_player_ids() -> dict[int, set[str]]:
    ids: dict[int, set[str]] = {}
    for path in (BOSCH_PATH, PROMO_PATH):
        data = load_json(path)
        for key in ("current_players", "overall_apps", "overall_points", "player_cards", "resolved_hidden_players", "player_rows"):
            for row in data.get(key, []):
                player_id = row.get("player_id")
                if not player_id:
                    continue
                ids.setdefault(int(player_id), set()).add(str(row.get("name") or ""))
    return ids


def fetch_public_profile(player_id: int) -> tuple[int, dict]:
    req = urllib.request.Request(f"https://podlaskaliga.pl/?p={player_id}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            final_url = response.geturl()
            html = response.read(6000).decode("utf-8", "ignore")
        match = TITLE_RE.search(html)
        title = clean_profile_name(match.group(1) if match else "")
        public = "/zawodnik/" in final_url
        return player_id, {
            "player_id": player_id,
            "profile_url": final_url if public else "",
            "public": public,
            "resolved_name": title if public else "",
            "source": "direct_id",
        }
    except Exception as exc:  # pragma: no cover - network behavior
        return player_id, {
            "player_id": player_id,
            "profile_url": "",
            "public": False,
            "resolved_name": "",
            "source": "direct_id",
            "error": type(exc).__name__,
        }


def fetch_text(url: str, cache_path: Path | None = None) -> str:
    if cache_path and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as response:
        html = response.read().decode("utf-8", "ignore")
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
    return html


def scrape_roster_name_map() -> dict[str, str]:
    promo = load_json(PROMO_PATH)
    roster_urls = {"https://podlaskaliga.pl/druzyna/bosch-service-tech-car/zawodnicy/"}
    for row in promo.get("promotions", []):
        link = str(row.get("team_link") or "").rstrip("/")
        if link:
            roster_urls.add(f"{link}/zawodnicy/")

    name_to_url: dict[str, str] = {}
    for url in sorted(roster_urls):
        try:
            html = fetch_text(url)
            for href, name in ROSTER_LINK_RE.findall(html):
                clean_name = " ".join(unescape(name).split())
                name_to_url.setdefault(clean_name, href)
        except Exception:
            continue
    return name_to_url


def scrape_event_hidden_name_map() -> dict[int, str]:
    promo = load_json(PROMO_PATH)
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    seen_urls: set[str] = set()

    for index, row in enumerate(promo.get("match_rows", [])):
        url = str(row.get("event_link") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            html = fetch_text(url, EVENT_CACHE_DIR / f"{index:04d}.html")
        except Exception:
            continue
        for player_id, raw_name in EVENT_PLAYER_RE.findall(html):
            name = clean_html_text(raw_name)
            if not name or "Zawodnik #" in name:
                continue
            counts[int(player_id)][name] += 1

    resolved: dict[int, str] = {}
    for player_id, options in counts.items():
        best_name, _ = sorted(options.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[0]
        resolved[player_id] = best_name
    return resolved


def build_profile_map() -> dict[str, dict]:
    player_ids = gather_player_ids()
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(fetch_public_profile, player_id) for player_id in sorted(player_ids)]
        for future in as_completed(futures):
            player_id, payload = future.result()
            results[str(player_id)] = payload

    roster_name_map = scrape_roster_name_map()
    event_hidden_name_map = scrape_event_hidden_name_map()
    bosch_hidden = {int(row["player_id"]): row["name"] for row in load_json(BOSCH_PATH).get("resolved_hidden_players", [])}

    for player_id, names in player_ids.items():
        entry = results[str(player_id)]
        if entry.get("public"):
            continue
        candidate_names = [name for name in names if name and "Zawodnik #" not in name]
        if player_id in bosch_hidden:
            candidate_names.insert(0, bosch_hidden[player_id])
            entry["resolved_name"] = bosch_hidden[player_id]
        for name in candidate_names:
            if name in roster_name_map:
                entry["profile_url"] = roster_name_map[name]
                entry["public"] = True
                entry["resolved_name"] = name
                entry["source"] = "team_roster_name"
                break
        if not entry.get("resolved_name") and player_id in event_hidden_name_map:
            entry["resolved_name"] = event_hidden_name_map[player_id]
            entry["source"] = "event_page_hidden"
    return results


def apply_resolved_names(value: object, profile_map: dict[str, dict]) -> object:
    if isinstance(value, dict):
        player_id = value.get("player_id")
        if player_id is not None:
            entry = profile_map.get(str(player_id), {})
            resolved_name = str(entry.get("resolved_name") or "").strip()
            current_name = str(value.get("name") or "")
            if resolved_name and (not current_name.strip() or "Zawodnik #" in current_name):
                value["name"] = resolved_name
        for key, item in list(value.items()):
            value[key] = apply_resolved_names(item, profile_map)
        return value
    if isinstance(value, list):
        return [apply_resolved_names(item, profile_map) for item in value]
    return value


def enrich_datasets(profile_map: dict[str, dict]) -> None:
    for path in (BOSCH_PATH, PROMO_PATH):
        data = load_json(path)
        enriched = apply_resolved_names(data, profile_map)
        path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> Path:
    profile_map = build_profile_map()
    OUT_PATH.write_text(json.dumps(profile_map, ensure_ascii=False, indent=2), encoding="utf-8")
    enrich_datasets(profile_map)
    return OUT_PATH


if __name__ == "__main__":
    print(main())
