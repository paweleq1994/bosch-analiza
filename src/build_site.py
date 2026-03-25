from __future__ import annotations

from html import unescape
from pathlib import Path
import json
import re
import unicodedata
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "bosch_service_tech_car_data_v3.json"
VIDEO_PATH = ROOT / "data" / "bosch_service_tech_car_video_library_v3.json"
PROMO_PATH = ROOT / "data" / "promoted_teams_analysis.json"
ORLIK2026_PATH = ROOT / "data" / "orlik_2026_opponents.json"
PROFILE_PATH = ROOT / "data" / "player_profile_map.json"
REFERENCE_PATH = ROOT / "data" / "reference_map.json"
OUT_PATH = ROOT / "docs" / "index.html"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"
USER_AGENT = "Mozilla/5.0"
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = TAG_RE.sub("", text).replace("\xa0", " ")
    return " ".join(text.split()).strip()


def norm_key(value: object) -> str:
    text = unicodedata.normalize("NFD", clean_text(value))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


def rendered_title(value: object) -> str:
    if isinstance(value, dict):
        return clean_text(value.get("rendered") or value.get("raw") or "")
    return clean_text(value)


def request_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def add_team_reference(reference: dict, team_id: object, name: object = "", link: object = "") -> None:
    if team_id in (None, ""):
        return
    key = str(team_id)
    row = reference["teams"]["by_id"].setdefault(key, {"id": int(team_id), "name": "", "link": ""})
    clean_name = clean_text(name)
    clean_link = clean_text(link)
    if clean_name and not row["name"]:
        row["name"] = clean_name
    if clean_link and not row["link"]:
        row["link"] = clean_link
    for candidate in {clean_name, row["name"]} - {""}:
        reference["teams"]["by_name"][norm_key(candidate)] = key


def add_table_reference(reference: dict, payload: dict) -> None:
    table_id = payload.get("id")
    if table_id in (None, ""):
        return
    key = str(table_id)
    title = rendered_title(payload.get("title"))
    link = clean_text(payload.get("link"))
    seasons = [int(s) for s in payload.get("seasons", []) if str(s).isdigit()]
    row = reference["tables"]["by_id"].setdefault(key, {"id": int(table_id), "title": "", "link": "", "seasons": []})
    if title and not row["title"]:
        row["title"] = title
    if link and not row["link"]:
        row["link"] = link
    if seasons:
        row["seasons"] = sorted({*row.get("seasons", []), *seasons})
    for season_id in row.get("seasons", []):
        if row["title"]:
            reference["tables"]["by_season_title"][f"{season_id}|{norm_key(row['title'])}"] = key


def collect_teams_from_table(reference: dict, payload: dict, team_ids: set[int]) -> None:
    for team_id, row in (payload.get("data") or {}).items():
        if not str(team_id).isdigit():
            continue
        numeric_id = int(team_id)
        team_ids.add(numeric_id)
        if isinstance(row, dict):
            add_team_reference(reference, numeric_id, row.get("name"))


def search_team_rows(name: str) -> list[dict]:
    if not clean_text(name):
        return []
    queries = [clean_text(name)]
    ascii_name = "".join(ch for ch in unicodedata.normalize("NFD", clean_text(name)) if unicodedata.category(ch) != "Mn")
    if ascii_name and ascii_name not in queries:
        queries.append(ascii_name)
    for query in queries:
        try:
            data = request_json(f"{BASE}/teams?search={urllib.parse.quote(query)}&per_page=30")
        except Exception:
            continue
        if isinstance(data, list) and data:
            return data
    return []


def build_reference_map(report: dict, video: dict, promo: dict, orlik2026: dict) -> dict:
    reference = {"teams": {"by_id": {}, "by_name": {}}, "tables": {"by_id": {}, "by_season_title": {}}}
    team_ids: set[int] = {6951}
    season_ids: set[int] = set()
    table_ids: set[int] = set()
    team_names: set[str] = set()

    def add_team_name(value: object) -> None:
        clean_name = clean_text(value)
        if clean_name:
            team_names.add(clean_name)

    for row in report.get("season_rows", []):
        if str(row.get("sid", "")).isdigit():
            season_ids.add(int(row["sid"]))
        add_team_name("Bosch Service Tech-Car")

    for row in report.get("benchmark", []):
        if str(row.get("season_id", "")).isdigit():
            season_ids.add(int(row["season_id"]))
        add_team_name(row.get("second_name"))

    for row in report.get("head_to_head", []):
        add_team_name(row.get("opponent"))

    for row in report.get("best_results", []) + report.get("worst_results", []):
        add_team_name(row.get("opponent"))

    for row in video.get("season_rows", []):
        if str(row.get("sid", "")).isdigit():
            season_ids.add(int(row["sid"]))

    for row in video.get("match_rows", []) + video.get("matched_rows", []):
        if str(row.get("sid", "")).isdigit():
            season_ids.add(int(row["sid"]))
        if str(row.get("opponent_id", "")).isdigit():
            team_ids.add(int(row["opponent_id"]))
            add_team_reference(reference, row["opponent_id"], row.get("display_opponent"))
            add_team_reference(reference, row["opponent_id"], row.get("opponent"))
            for alias in row.get("opponent_aliases", []) or []:
                add_team_reference(reference, row["opponent_id"], alias)
        add_team_name(row.get("opponent"))
        add_team_name(row.get("display_opponent"))

    for row in video.get("recommended_rows", []):
        match = row.get("match") or {}
        if str(match.get("sid", "")).isdigit():
            season_ids.add(int(match["sid"]))
        if str(match.get("opponent_id", "")).isdigit():
            team_ids.add(int(match["opponent_id"]))
            add_team_reference(reference, match["opponent_id"], match.get("display_opponent"))
            add_team_reference(reference, match["opponent_id"], match.get("opponent"))
            for alias in match.get("opponent_aliases", []) or []:
                add_team_reference(reference, match["opponent_id"], alias)
        add_team_name(match.get("opponent"))
        add_team_name(match.get("display_opponent"))

    for row in promo.get("promotions", []):
        if str(row.get("sid", "")).isdigit():
            season_ids.add(int(row["sid"]))
        if str(row.get("team_id", "")).isdigit():
            team_ids.add(int(row["team_id"]))
            add_team_reference(reference, row["team_id"], row.get("team_name"), row.get("team_link"))
        add_team_name(row.get("team_name"))
        post = row.get("first_post_top_tier") or {}
        if str(post.get("table_id", "")).isdigit():
            table_ids.add(int(post["table_id"]))
        for hist in row.get("league_history", []):
            if str(hist.get("table_id", "")).isdigit():
                table_ids.add(int(hist["table_id"]))
            if str(hist.get("team_id", "")).isdigit():
                team_ids.add(int(hist["team_id"]))
            add_team_name(hist.get("team_name"))

    for row in promo.get("match_rows", []):
        if str(row.get("sid", "")).isdigit():
            season_ids.add(int(row["sid"]))
        if str(row.get("team_id", "")).isdigit():
            team_ids.add(int(row["team_id"]))
            add_team_reference(reference, row["team_id"], row.get("team_name"))
        if str(row.get("opponent_id", "")).isdigit():
            team_ids.add(int(row["opponent_id"]))
            add_team_reference(reference, row["opponent_id"], row.get("opponent"))
        add_team_name(row.get("team_name"))
        add_team_name(row.get("opponent"))

    for row in promo.get("player_rows", []):
        if str(row.get("team_id", "")).isdigit():
            team_ids.add(int(row["team_id"]))
        add_team_name(row.get("team_name"))

    for row in orlik2026.get("excluded_promoted", []) + orlik2026.get("bottom_two_watch", []):
        if str(row.get("team_id", "")).isdigit():
            team_ids.add(int(row["team_id"]))
            add_team_reference(reference, row["team_id"], row.get("name"))
        add_team_name(row.get("name"))

    for row in orlik2026.get("opponents", []):
        if str(row.get("team_id", "")).isdigit():
            team_ids.add(int(row["team_id"]))
            add_team_reference(reference, row["team_id"], row.get("team_name"), row.get("team_link"))
        add_team_name(row.get("team_name"))
        bosch_match = row.get("bosch_hall_match") or {}
        if str(bosch_match.get("opponent_id", "")).isdigit():
            team_ids.add(int(bosch_match["opponent_id"]))

    source = orlik2026.get("source") or {}
    if str(source.get("hall_table_id", "")).isdigit():
        table_ids.add(int(source["hall_table_id"]))
    if str(source.get("orlik_2025_table_id", "")).isdigit():
        table_ids.add(int(source["orlik_2025_table_id"]))

    fetched_table_ids: set[int] = set()
    for season_id in sorted(season_ids):
        try:
            rows = request_json(f"{BASE}/tables?seasons={season_id}&per_page=100")
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for payload in rows:
            if not isinstance(payload, dict):
                continue
            add_table_reference(reference, payload)
            table_id = payload.get("id")
            if str(table_id).isdigit():
                fetched_table_ids.add(int(table_id))
            collect_teams_from_table(reference, payload, team_ids)

    for table_id in sorted(table_ids - fetched_table_ids):
        try:
            payload = request_json(f"{BASE}/tables/{table_id}")
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        add_table_reference(reference, payload)
        collect_teams_from_table(reference, payload, team_ids)

    for team_id in sorted(team_ids):
        try:
            payload = request_json(f"{BASE}/teams/{team_id}")
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        add_team_reference(reference, team_id, rendered_title(payload.get("title")), payload.get("link"))

    unresolved_names = [name for name in sorted(team_names) if norm_key(name) not in reference["teams"]["by_name"]]
    for name in unresolved_names:
        candidates = search_team_rows(name)
        best = None
        target = norm_key(name)
        for payload in candidates:
            rendered = rendered_title(payload.get("title"))
            if norm_key(rendered) == target:
                best = payload
                break
        if best is None and len(candidates) == 1:
            best = candidates[0]
        if isinstance(best, dict) and best.get("id") is not None:
            add_team_reference(reference, best["id"], rendered_title(best.get("title")), best.get("link"))

    return reference


TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kompendium Wiedzy o Bosch Service Tech-Car</title>
  <style>
    :root{--bg:#f3f7fb;--panel:#fff;--soft:#eef5ff;--ink:#132238;--muted:#5b6b7d;--line:#d6e0ea;--blue:#1d4ed8;--teal:#0f766e;--orange:#ea580c;--red:#dc2626;--gold:#b7791f;--shadow:0 14px 40px rgba(19,34,56,.08);--mobile-toolbar-h:74px}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at top left,rgba(37,99,235,.08),transparent 26%),linear-gradient(180deg,#eef4fb 0%,#fafcff 100%);color:var(--ink);font-family:Aptos,Bahnschrift,"Segoe UI",sans-serif;line-height:1.45}
    a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
    .shell{width:min(98vw,1920px);margin:0 auto;padding:18px 0 48px}
    .hero{background:linear-gradient(135deg,#0b1324 0%,#0f766e 48%,#2563eb 100%);color:#fff;border-radius:28px;padding:30px 30px 24px;box-shadow:var(--shadow)}
    .hero h1{margin:0 0 8px;font-size:clamp(2rem,3.4vw,3.8rem);line-height:1.02;letter-spacing:-.03em}
    .hero p{margin:0;max-width:1120px;color:rgba(255,255,255,.92)}
    .hero-stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:20px}
    .hero-card,.panel,.mini-card{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:14px 16px}
    .hero-label,.k,.toolbar label,.toolbar-fly label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:inherit;opacity:.78;font-weight:700}
    .hero-value,.v{margin-top:6px;font-size:1.35rem;font-weight:800}
    body.toolbar-lock{overflow:hidden}
    .toolbar-sentinel{height:1px}
    .toolbar{position:relative;z-index:20;margin-top:16px;padding:14px;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}
    .toolbar-mobile,.toolbar-backdrop,.toolbar-fly{display:none}
    .toolbar-mobile-bar{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .toolbar-mobile-copy{min-width:0}
    .toolbar-mobile-label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .toolbar-toggle{display:inline-grid;place-items:center;width:46px;min-width:46px;min-height:46px;border-radius:14px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:800;padding:0;cursor:pointer}
    .toolbar-toggle-box{display:grid;gap:4px;width:18px}
    .toolbar-toggle-box span{display:block;height:2px;border-radius:99px;background:var(--ink);transition:transform .18s ease,opacity .18s ease}
    .toolbar.open .toolbar-toggle-box span:nth-child(1){transform:translateY(6px) rotate(45deg)}
    .toolbar.open .toolbar-toggle-box span:nth-child(2){opacity:0}
    .toolbar.open .toolbar-toggle-box span:nth-child(3){transform:translateY(-6px) rotate(-45deg)}
    .toolbar-summary{font-size:.92rem;color:var(--muted);padding:2px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .toolbar-panel{display:block}
    .toolbar-panel-head{display:none}
    .toolbar-panel-title{margin-top:4px;font-size:1.05rem;font-weight:800;letter-spacing:-.02em}
    .toolbar-close{display:inline-grid;place-items:center;width:42px;min-width:42px;min-height:42px;border-radius:12px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-size:1.35rem;line-height:1;cursor:pointer;padding:0}
    .toolbar-compact{align-items:center;justify-content:space-between;gap:14px}
    .toolbar-compact-copy{min-width:0}
    .toolbar-compact-title{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .toolbar-compact-summary{margin-top:3px;font-size:.95rem;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .toolbar-compact-actions{display:flex;gap:8px;align-items:center;flex-shrink:0}
    .toolbar-compact-btn{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 14px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:800;cursor:pointer}
    .toolbar-range{margin-bottom:14px}
    .range-block{padding:14px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%)}
    .range-help{margin-top:6px;color:var(--muted);font-size:.92rem}
    .range-row{display:grid;gap:8px;margin-top:12px}
    .range-title{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .chip-group{display:flex;gap:8px;flex-wrap:wrap}
    .chip-btn{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:0 12px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
    .chip-btn.active{background:#e9f1ff;border-color:#7aa6ff;color:#163f94;box-shadow:inset 0 0 0 1px rgba(29,78,216,.18)}
    .toolbar-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:end}
    .control{display:grid;gap:6px}
    .section-tools input,.section-tools select,.section-tools button{min-height:46px;border-radius:14px;border:1px solid var(--line);background:#fff;padding:0 14px;font:inherit;color:var(--ink)}
    .section-tools button{font-weight:800;cursor:pointer}
    .promo-toolbar{grid-template-columns:1.4fr repeat(4,minmax(0,1fr))}
    .promo-toolbar .chip-group{min-height:46px;align-items:center}
    .promo-toolbar .chip-btn{min-width:0}
    .promo-toolbar .control:last-child button{width:100%}
    .toolbar input,.toolbar select,.toolbar button,.toolbar-fly input,.toolbar-fly select,.toolbar-fly button{min-height:46px;border-radius:14px;border:1px solid var(--line);background:#fff;padding:0 14px;font:inherit;color:var(--ink)}
    .toolbar button,.toolbar-fly button{font-weight:800;cursor:pointer}
    .nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
    .nav a{padding:10px 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);font-weight:700}
    .toolbar-fly{position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:130;width:min(880px,calc(100vw - 28px))}
    .toolbar-fly.active{display:block}
    .toolbar-fly-shell{padding:10px 12px;background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:18px;box-shadow:0 14px 36px rgba(19,34,56,.12)}
    .toolbar-fly.open .toolbar-fly-shell{box-shadow:0 18px 40px rgba(19,34,56,.12),0 34px 84px rgba(19,34,56,.22)}
    .toolbar-fly .toolbar-compact{display:flex}
    .toolbar-fly-panel{display:none}
    .toolbar-fly.open .toolbar-fly-panel{display:block;margin-top:12px}
    .section{margin-top:18px;background:var(--panel);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow);overflow:visible}
    .head{padding:24px 24px 0}.head h2{margin:0;font-size:1.45rem;letter-spacing:-.02em}.head p{margin:8px 0 0;color:var(--muted)}
    .body{padding:18px 24px 24px}
    .cards,.season-grid,.player-grid,.chart-grid,.split,.dense-grid,.promotion-grid{display:grid;gap:14px}
    .cards>*,.season-grid>*,.player-grid>*,.chart-grid>*,.split>*,.dense-grid>*,.promotion-grid>*{min-width:0}
    .cards{grid-template-columns:repeat(5,1fr)}
    .card,.season-card,.player-card{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .value{margin-top:8px;font-size:1.42rem;font-weight:800;letter-spacing:-.03em}
    .sub{margin-top:8px;color:var(--muted);font-size:.94rem}
    .season-grid{grid-template-columns:repeat(4,1fr);margin-top:14px}
    .player-grid{grid-template-columns:repeat(6,1fr);margin-top:14px}
    .chart-grid{grid-template-columns:repeat(2,1fr)}
    .split,.dense-2{grid-template-columns:1fr 1fr}
    .split-wide{grid-template-columns:minmax(0,1.3fr) minmax(320px,.9fr)}
    .dense-3{grid-template-columns:repeat(3,1fr)}
    .promotion-grid{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:16px}
    .season-card{cursor:pointer;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
    .season-card:hover{transform:translateY(-2px);border-color:rgba(29,78,216,.45);box-shadow:0 12px 28px rgba(29,78,216,.12)}
    .season-card.active{border-color:rgba(29,78,216,.7);background:linear-gradient(180deg,#f7fbff 0%,#eef5ff 100%)}
    .tags,.identity-badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.identity-badges{margin-top:0;align-items:center}.tag{display:inline-flex;align-items:center;justify-self:start;width:fit-content;max-width:100%;white-space:nowrap;column-gap:8px;padding:7px 12px;border-radius:999px;font-size:.82rem;font-weight:800;border:1px solid var(--line);background:#fff}.tag-value{white-space:nowrap;display:inline-flex;align-items:center}.blue{background:#eef4ff;border-color:#bfd4ff;color:#1e40af}.teal{background:#ecfdf5;border-color:#9de5d6;color:#0f766e}.orange{background:#fff7ed;border-color:#fdba74;color:#9a3412}.red{background:#fef2f2;border-color:#fca5a5;color:#991b1b}.gold{background:#fff7e6;border-color:#f6c36f;color:#8a5c00}
    .table-card,.chart,.chapter-note{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .table-top{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.table-top h3{margin:0;font-size:1rem}.meta{color:var(--muted);font-size:.9rem}
    .table-wrap{overflow-x:auto;overflow-y:visible;border:1px solid var(--line);border-radius:14px;background:#fff}
    .table-wrap.scroller{max-height:620px;overflow-y:auto}
    table{width:100%;border-collapse:collapse;font-size:.94rem}thead th{position:sticky;top:0;z-index:1;background:#eef5fb;color:#17324c;border-bottom:1px solid var(--line)}
    th,td{padding:10px 10px;text-align:left;vertical-align:top;border-bottom:1px solid #eef3f8;overflow-wrap:break-word}tbody tr:nth-child(even) td{background:#fbfdff}tbody tr:hover td{background:#f4f9ff}
    td a{white-space:nowrap;display:inline-block}
    td[data-label="ID"],td[data-label="Link"]{white-space:nowrap;min-width:76px}
    td[data-label="Orlik 2025"],td[data-label="Bosch na hali"],td[data-label="Bosch na orliku"]{min-width:168px}
    td[data-label="Najkrótszy plan"]{min-width:260px}
    th button{all:unset;cursor:pointer;font-weight:800;display:inline-flex;align-items:center;gap:6px}.sort{display:inline-flex;width:12px;justify-content:center;color:var(--muted)}
    .status{display:inline-flex;justify-self:start;width:fit-content;max-width:100%;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:800}.obecny{background:#dcfce7;color:#166534}.arch{background:#fff7ed;color:#9a3412}.win{background:#dcfce7;color:#166534}.draw{background:#eff6ff;color:#1d4ed8}.loss{background:#fef2f2;color:#991b1b}
    .cell-stack{display:grid;gap:4px;min-width:0}
    .cell-line{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .cell-k{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:800}
    .cell-note{font-size:.84rem;color:var(--muted);line-height:1.4;overflow-wrap:anywhere}
    .delta-up{color:#0f766e;font-weight:700}
    .delta-down{color:#9a3412;font-weight:700}
    .tag-sep{opacity:.55}
    .chart h3{margin:0 0 12px;font-size:1rem}.chart svg{display:block;width:100%;height:auto}
    .metric-bars{display:grid;gap:12px}
    .metric-bar{display:grid;gap:6px}
    .metric-bar-label{font-size:.92rem;font-weight:800;color:var(--ink)}
    .metric-bar-sub{display:block;margin-top:2px;font-size:.78rem;color:var(--muted);font-weight:600}
    .metric-bar-main{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center}
    .metric-bar-track{height:16px;border-radius:999px;background:#eef3f8;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(19,34,56,.04)}
    .metric-bar-fill{height:100%;border-radius:999px;min-width:10px}
    .metric-bar-value{min-width:52px;text-align:right;font-size:.9rem;font-weight:800;color:#425466}
    .chapter-note{margin-top:16px;background:linear-gradient(180deg,#f8fbff 0%,#eef5ff 100%);border-color:#cadeff}.chapter-note strong{display:block;margin-bottom:6px;font-size:.84rem;letter-spacing:.08em;text-transform:uppercase;color:#18406b}.chapter-note p{margin:.4rem 0 0;overflow-wrap:anywhere}
    .term{display:inline-flex;align-items:center;border-bottom:1px dashed rgba(19,34,56,.38);cursor:help;font-weight:800}
    .term:focus-visible{outline:2px solid rgba(37,99,235,.35);outline-offset:3px;border-radius:4px}
    .tooltip-layer{position:fixed;left:0;top:0;max-width:min(340px,calc(100vw - 24px));padding:10px 12px;border-radius:12px;background:#0b1324;color:#fff;box-shadow:0 14px 28px rgba(11,19,36,.26);font-size:12px;font-weight:600;line-height:1.45;opacity:0;pointer-events:none;transform:translateY(4px);transition:opacity .12s ease,transform .12s ease;z-index:9999}
    .tooltip-layer.show{opacity:1;transform:translateY(0)}
    .empty{padding:18px;text-align:center;color:var(--muted);background:#fff;border:1px dashed var(--line);border-radius:14px}
    .reco-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    .reco-card{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .reco-card h3{margin:0 0 8px;font-size:1rem}
    .reco-card p{margin:8px 0 0;color:var(--muted);overflow-wrap:anywhere}
    .analysis-stack{display:grid;gap:12px}
    .analysis-row{padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:#fff}
    .analysis-row strong{display:block;font-size:.82rem;letter-spacing:.08em;text-transform:uppercase;color:#18406b}
    .analysis-row p{margin:.45rem 0 0;color:var(--muted);overflow-wrap:anywhere}
    .scout-card{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .scout-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
    .scout-head h3{margin:0;font-size:1.1rem}
    .scout-sub{margin-top:8px;color:var(--muted);font-size:.95rem}
    .scout-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}
    .scout-block{padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:#fff}
    .scout-block h4{margin:0;font-size:.92rem}
    .scout-block ul{margin:8px 0 0;padding-left:18px}
    .scout-block li{margin-top:6px;color:var(--muted);overflow-wrap:anywhere}
    .foot{margin-top:12px;color:var(--muted);font-size:.9rem}
    @media (max-width:1480px){.split,.split-wide{grid-template-columns:1fr}}
    @media (max-width:1280px){.cards{grid-template-columns:repeat(3,1fr)}.season-grid{grid-template-columns:repeat(2,1fr)}.player-grid{grid-template-columns:repeat(3,1fr)}.chart-grid,.dense-2,.dense-3,.reco-grid,.promotion-grid{grid-template-columns:1fr}.hero-stats{grid-template-columns:repeat(2,1fr)}.toolbar-grid,.promo-toolbar{grid-template-columns:1fr 1fr}}
    @media (max-width:900px){.shell{width:100%!important;padding:0!important}.hero,.section{margin-left:10px;margin-right:10px}.hero{margin-top:calc(var(--mobile-toolbar-h) + 22px);padding:24px 20px 20px}.toolbar-sentinel{display:none}.toolbar-fly{display:none!important}.toolbar{position:fixed;top:10px;left:10px;right:10px;z-index:120;margin:0;padding:0;background:transparent;border:none;border-radius:0;box-shadow:none;backdrop-filter:none}.toolbar-mobile{display:block;position:relative;z-index:3;padding:10px 12px;background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 34px rgba(19,34,56,.12)}.toolbar.open .toolbar-mobile{box-shadow:0 16px 36px rgba(19,34,56,.16)}.toolbar-mobile-copy{max-width:calc(100% - 62px)}.toolbar-mobile-bar{min-height:52px}.toolbar-summary{padding-top:4px;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.toolbar-toggle{width:48px;min-width:48px;min-height:48px;border-radius:16px;box-shadow:0 8px 20px rgba(19,34,56,.08)}.toolbar-backdrop{display:block;position:fixed;inset:0;z-index:1;background:rgba(11,19,36,.38);opacity:0;pointer-events:none;transition:opacity .18s ease}.toolbar.open .toolbar-backdrop{opacity:1;pointer-events:auto}.toolbar-panel{display:block;position:fixed;z-index:2;top:calc(var(--mobile-toolbar-h) + 18px);left:10px;right:10px;bottom:10px;width:auto;padding:16px 14px 20px;background:rgba(255,255,255,.985);border:1px solid var(--line);border-radius:22px;box-shadow:0 20px 48px rgba(19,34,56,.18);overflow:auto;transform:translateY(14px);opacity:0;pointer-events:none;transition:transform .2s ease,opacity .2s ease}.toolbar.open .toolbar-panel{transform:translateY(0);opacity:1;pointer-events:auto}.toolbar-panel-head{display:block;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid #eef3f8}.toolbar-close{display:none}.toolbar-grid{grid-template-columns:1fr}.toolbar-panel .nav{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.toolbar-panel .nav a{display:flex;align-items:center;justify-content:center;width:100%;min-width:0;border-radius:14px;text-align:center;white-space:normal;overflow-wrap:anywhere}.head,.body{padding-left:16px;padding-right:16px}.cards{grid-template-columns:1fr 1fr}.season-grid,.player-grid,.scout-grid{grid-template-columns:1fr}.tag,.status{width:auto;max-width:100%;white-space:normal;overflow-wrap:anywhere;line-height:1.25}.sub,.range-help,.toolbar-panel-title,.toolbar-summary,.chapter-note,.reco-card,.scout-card{overflow-wrap:anywhere}}
    @media (max-width:720px){.cards{grid-template-columns:1fr}.hero-stats{grid-template-columns:1fr 1fr}.table-wrap{overflow:auto;-webkit-overflow-scrolling:touch}.table-wrap table{min-width:720px}.table-wrap.scroller{max-height:min(60vh,520px);overflow:auto;-webkit-overflow-scrolling:touch}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <h1>Kompendium Wiedzy o Bosch Service Tech-Car</h1>
      <p>Interaktywne kompendium wiedzy o drużynie Bosch Service Tech-Car, oparte na danych Podlaskiej Ligi Piłkarskiej i publicznym materiale wideo. Można tu filtrować po sezonie, wyszukiwać zawodników i sortować tabele po kliknięciu.</p>
      <div class="hero-stats" id="hero-stats"></div>
    </header>

    <div class="toolbar-sentinel" id="toolbar-sentinel" aria-hidden="true"></div>
    <div class="toolbar" id="toolbar">
      <div class="toolbar-mobile">
        <div class="toolbar-mobile-bar">
          <div class="toolbar-mobile-copy">
            <div class="toolbar-mobile-label">Menu mobilne</div>
            <div class="toolbar-summary" id="toolbar-summary"></div>
          </div>
          <button id="toolbar-toggle" class="toolbar-toggle" type="button" aria-expanded="false" aria-controls="toolbar-panel" aria-label="Otwórz filtry i nawigację">
            <span class="toolbar-toggle-box" aria-hidden="true"><span></span><span></span><span></span></span>
          </button>
        </div>
      </div>
      <div class="toolbar-backdrop" id="toolbar-backdrop"></div>
      <div class="toolbar-panel-inline" id="toolbar-panel-inline">
      <div class="toolbar-panel" id="toolbar-panel">
        <div class="toolbar-panel-head">
          <div>
            <div class="toolbar-mobile-label">Menu</div>
            <div class="toolbar-panel-title">Filtry i nawigacja</div>
          </div>
          <button id="toolbar-close" class="toolbar-close" type="button" aria-label="Zamknij menu">×</button>
        </div>
        <div class="toolbar-range">
          <div class="range-block">
            <div class="toolbar-mobile-label">Zakres statystyk zbiorczych</div>
            <div class="range-help">Łącz dowolnie grupy sezonów, lata i konkretne sezony. Strona przeliczy zbiorcze podsumowanie dla aktywnego zakresu.</div>
            <div class="range-row">
              <div class="range-title">Szybkie grupy</div>
              <div class="chip-group" id="group-chips"></div>
            </div>
            <div class="range-row">
              <div class="range-title">Roczniki</div>
              <div class="chip-group" id="year-chips"></div>
            </div>
            <div class="range-row">
              <div class="range-title">Konkretne sezony</div>
              <div class="chip-group" id="season-chips"></div>
            </div>
            <div class="range-row">
              <div class="chip-group">
                <button id="range-all" class="chip-btn" type="button">Wszystkie sezony</button>
              </div>
            </div>
          </div>
        </div>
        <div class="toolbar-grid">
          <div class="control">
            <label for="query-filter">Wyszukiwanie</label>
            <input id="query-filter" type="search" placeholder="Szukaj zawodnika, rywala, sezonu, meczu...">
          </div>
          <div class="control">
            <label for="status-filter">Status Zawodnika</label>
            <select id="status-filter">
              <option value="all">Wszyscy</option>
              <option value="obecny">Tylko obecni</option>
              <option value="archiwalny">Tylko archiwalni</option>
            </select>
          </div>
          <div class="control">
            <label for="video-filter">Filtr Wideo</label>
            <select id="video-filter">
              <option value="all">Wszystko</option>
              <option value="with">Tylko z wideo</option>
              <option value="without">Tylko bez wideo</option>
              <option value="full">Tylko pełne mecze</option>
            </select>
          </div>
          <div class="control">
            <label>&nbsp;</label>
            <button id="reset-filters" type="button">Resetuj filtry</button>
          </div>
        </div>
        <nav class="nav">
          <a href="#overview">Przegląd</a>
          <a href="#seasons">Sezony</a>
          <a href="#splits">Splity</a>
          <a href="#control">Kontrola</a>
          <a href="#players">Zawodnicy</a>
          <a href="#matches">Mecze</a>
          <a href="#opponents">Rywalizacja</a>
          <a href="#promotions">Wzorce awansu</a>
          <a href="#orlik2026">Scouting Orlik 2026</a>
          <a href="#video">Wideo</a>
          <a href="#recommendations">Rekomendacje</a>
        </nav>
      </div>
      </div>
    </div>

    <div class="toolbar-fly" id="toolbar-fly" aria-hidden="true">
      <div class="toolbar-fly-shell">
        <div class="toolbar-compact">
          <div class="toolbar-compact-copy">
            <div class="toolbar-compact-title">Aktywny zakres</div>
            <div class="toolbar-compact-summary" id="toolbar-fly-summary"></div>
          </div>
          <div class="toolbar-compact-actions">
            <button id="toolbar-desktop-toggle" class="toolbar-compact-btn" type="button" aria-expanded="false" aria-controls="toolbar-panel">Rozwiń filtry</button>
          </div>
        </div>
        <div class="toolbar-fly-panel" id="toolbar-fly-panel"></div>
      </div>
    </div>

    <section class="section" id="overview">
      <div class="head"><h2>Przegląd</h2><p>Najważniejsze karty i legenda skrótów. Wybór sezonu przelicza karty sezonowe i filtruje tabele, które mają sens sezonowy.</p></div>
      <div class="body">
        <div class="cards" id="summary-cards"></div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Legenda Skrótów</h3><div class="meta">Skróty używane w całym dashboardzie</div></div>
          <div id="legend-table"></div>
        </div>
        <div class="dense-grid dense-2" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Słownik Pojęć</h3><div class="meta">Rozwinięcie nieoczywistych terminów analitycznych</div></div>
            <div id="concept-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Odzyskane Profile Ukryte</h3><div class="meta">Anonimowe ID rozpoznane po archiwalnych składach</div></div>
            <div id="hidden-table"></div>
          </div>
        </div>
        <div class="chapter-note" id="overview-note"></div>
      </div>
    </section>

    <section class="section" id="seasons">
      <div class="head"><h2>Sezony</h2><p>Kliknij kartę sezonu, aby ustawić filtr dla całej strony. Tabele można sortować kliknięciem w nagłówek kolumny.</p></div>
      <div class="body">
        <div class="chart-grid">
          <div class="chart"><h3>Punkty w sezonach</h3><div id="points-chart"></div></div>
          <div class="chart"><h3>PPG w sezonach</h3><div id="ppg-chart"></div></div>
          <div class="chart"><h3>Pierwszy gol Bosch</h3><div id="first-goal-chart"></div></div>
          <div class="chart"><h3>Pokrycie wideo</h3><div id="video-chart"></div></div>
        </div>
        <div class="season-grid" id="season-cards"></div>
        <div class="split split-wide" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Sezony ligowe</h3><div class="meta" id="season-meta"></div></div>
            <div id="season-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Scorecard awansu</h3><div class="meta">Najkrótsza odpowiedź: ile brakuje do I ligi?</div></div>
            <div id="scorecard-table"></div>
          </div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Benchmark Awansu</h3><div class="meta">Bosch kontra próg 2. miejsca</div></div>
            <div id="benchmark-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Peak vs Bieżący Sezon</h3><div class="meta">Najmocniejszy Bosch kontra obecny poziom</div></div>
            <div id="peak-table"></div>
          </div>
        </div>
        <div class="chapter-note" id="seasons-note"></div>
      </div>
    </section>

    <section class="section" id="splits">
      <div class="head"><h2>Splity i Fazy Gry</h2><p>Ten rozdział rozbija Bosch na porównania hali z orlikiem, mecze z górą i dołem tabeli, stany do przerwy, sposób zapisu meczu w bazie ligi oraz rozkład minut goli. To tutaj opisane są mniej oczywiste pojęcia typu <span class="term" tabindex="0" data-tip="Split to po prostu podział danych na porównywalne grupy. Split konkurencyjności rozbija mecze na rywali z górnej i dolnej połowy tabeli, żeby sprawdzić, czy zespół daje liczby także przeciw mocniejszym.">split konkurencyjności</span>.</p></div>
      <div class="body">
        <div class="chart-grid">
          <div class="chart"><h3>Rozkład Minut Goli · Historia</h3><div id="timing-all-chart"></div></div>
          <div class="chart"><h3>Rozkład Minut Goli · Bieżący Sezon</h3><div id="timing-current-chart"></div></div>
          <div class="chart"><h3>Peak vs Teraz</h3><div id="peak-chart"></div></div>
          <div class="chart"><h3>Split Powierzchni</h3><div id="surface-chart"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Hala vs Orlik</h3><div class="meta">Historia Bosch według powierzchni</div></div><div id="surface-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Slot zapisu · Historia</h3><div class="meta">Bosch jako 1. lub 2. zespół w technicznym wpisie meczu w bazie ligi</div></div><div id="slot-all-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Slot zapisu · Bieżący Sezon</h3><div class="meta">Czy techniczny sposób zapisania meczu coś zmienia w obecnej kampanii</div></div><div id="slot-current-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Stan do Przerwy · Historia</h3><div class="meta">Jak wynik po pierwszej połowie przekłada się na punkty</div></div><div id="halftime-all-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Stan do Przerwy · Bieżący Sezon</h3><div class="meta">Czy Bosch umie odwracać słabsze pierwsze połowy</div></div><div id="halftime-current-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Split Konkurencyjności · Bieżący</h3><div class="meta">Top half kontra Bottom half</div></div><div id="tier-current-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Split Konkurencyjności · Peak</h3><div class="meta">Jak wyglądał Bosch w swoim historycznym maksimum</div></div><div id="tier-peak-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Peak vs Teraz · Tabela</h3><div class="meta">Najważniejsze luki jakościowe rozpisane wprost</div></div><div id="peak-compare-table"></div></div>
        </div>
        <div class="chapter-note" id="splits-note"></div>
      </div>
    </section>

    <section class="section" id="control">
      <div class="head"><h2>Kontrola Meczu</h2><p>Jak Bosch wchodzi w mecz, jak punktuje w spotkaniach stykowych i jak szeroko rozłożona jest produkcja.</p></div>
      <div class="body">
        <div class="split">
          <div class="table-card"><div class="table-top"><h3>Pierwszy gol i reakcja</h3><div class="meta">Sezony ligowe</div></div><div id="state-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Mecze stykowe</h3><div class="meta">Remisy i mecze rozstrzygnięte jedną bramką</div></div><div id="close-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Ciągłość kadry</h3><div class="meta">Stabilność rdzenia</div></div><div id="continuity-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Koncentracja produkcji</h3><div class="meta">Jak szeroko rozłożone są gole i punkty</div></div><div id="concentration-table"></div></div>
        </div>
        <div class="chapter-note" id="control-note"></div>
      </div>
    </section>

    <section class="section" id="players">
      <div class="head"><h2>Zawodnicy</h2><p>Bieżący liderzy oraz pełna tabela zawodników z możliwością wyszukiwania i filtrowania po statusie.</p></div>
      <div class="body">
        <div class="player-grid" id="current-player-cards"></div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Najwięcej występów</h3><div class="meta">Historia Bosch</div></div><div id="apps-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Największa produkcja ofensywna</h3><div class="meta">Historia Bosch</div></div><div id="points-table"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Karty zawodników</h3><div class="meta">Sortowalne i filtrowalne</div></div>
          <div id="player-cards-table"></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Partnerstwa Zawodników</h3><div class="meta">Które duety dają najwięcej punktów na mecz</div></div>
          <div id="partnership-table"></div>
        </div>
        <div class="chapter-note" id="players-note"></div>
      </div>
    </section>

    <section class="section" id="matches">
      <div class="head"><h2>Pełny Log Meczów</h2><p>Oficjalne mecze Bosch w jednej bazie: wynik, rezultat, stan do przerwy, sposób zapisu meczu w bazie ligi, pokrycie wideo i link do wydarzenia. To główna tabela robocza do filtrowania całej historii.</p></div>
      <div class="body">
        <div class="table-card">
          <div class="table-top"><h3>Oficjalne Mecze Bosch</h3><div class="meta">Chronologia całej historii dostępnej w publicznej bazie danych ligi</div></div>
          <div id="match-log-table"></div>
        </div>
        <div class="chapter-note" id="matches-note"></div>
      </div>
    </section>

    <section class="section" id="opponents">
      <div class="head"><h2>Rywalizacja</h2><p>Head-to-head, najlepsze i najgorsze wyniki oraz benchmark awansu.</p></div>
      <div class="body">
        <div class="table-card"><div class="table-top"><h3>Head-to-head</h3><div class="meta">Najczęściej spotykani rywale</div></div><div id="h2h-table"></div></div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Najwyższe zwycięstwa</h3><div class="meta">Top dodatnich rekordów</div></div><div id="best-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Najcięższe porażki</h3><div class="meta">Top ujemnych rekordów</div></div><div id="worst-table"></div></div>
        </div>
        <div class="chapter-note" id="opponents-note"></div>
      </div>
    </section>

    <section class="section" id="promotions">
      <div class="head"><h2>Wzorce Awansu do I Ligi</h2><p>Profil każdej drużyny, która wywalczyła awans z II ligi w analizowanym okresie. To benchmark pokazujący, jak wyglądał realny awans: tempo punktowe, bufor nad 3. miejscem, profil meczów, liderzy i pierwszy późniejszy ślad w I lidze.</p></div>
      <div class="body">
        <div class="table-card section-tools">
          <div class="table-top"><h3>Filtry benchmarku awansu</h3><div class="meta" id="promotion-filter-meta"></div></div>
          <div class="toolbar-grid promo-toolbar">
            <div class="control">
              <label>Powierzchnia</label>
              <div class="chip-group" id="promotion-surface-chips"></div>
            </div>
            <div class="control">
              <label for="promotion-rank-filter">Miejsce awansu</label>
              <select id="promotion-rank-filter">
                <option value="all">1. i 2. miejsce</option>
                <option value="1">Tylko 1. miejsce</option>
                <option value="2">Tylko 2. miejsce</option>
              </select>
            </div>
            <div class="control">
              <label for="promotion-buffer-filter">Bufor nad 3. miejscem</label>
              <select id="promotion-buffer-filter">
                <option value="all">Dowolny bufor</option>
                <option value="tight">Na styku: do 2 pkt</option>
                <option value="safe">Wyraźny bufor: 4+ pkt</option>
              </select>
            </div>
            <div class="control">
              <label for="promotion-profile-filter">Profil zespołu</label>
              <select id="promotion-profile-filter">
                <option value="all">Dowolny profil</option>
                <option value="defense_top2">Obrona top2 ligi</option>
                <option value="attack_top2">Atak top2 ligi</option>
                <option value="balanced_top2">Atak i obrona top2</option>
                <option value="wide_attack">Szeroka produkcja goli</option>
              </select>
            </div>
            <div class="control">
              <label>&nbsp;</label>
              <button id="promotion-reset" type="button">Resetuj benchmark</button>
            </div>
          </div>
        </div>
        <div class="cards" id="promotion-summary-cards" style="margin-top:16px"></div>
        <div class="chart-grid" style="margin-top:16px">
          <div class="chart"><h3>PPG drużyn awansujących</h3><div class="meta">punkty na mecz w sezonie zakończonym awansem</div><div id="promotion-ppg-chart"></div></div>
          <div class="chart"><h3>Zapas punktowy nad 3. miejscem</h3><div class="meta">przewaga nad pierwszym miejscem nieawansującym</div><div id="promotion-gap-chart"></div></div>
          <div class="chart"><h3>Gole stracone na mecz</h3><div class="meta">średnia liczba goli straconych w sezonie awansowym</div><div id="promotion-defense-chart"></div></div>
    <div class="chart"><h3>Śr. pkt w meczach stykowych</h3><div class="meta">średnia liczba punktów zdobywanych w meczach stykowych, czyli w remisach i spotkaniach rozstrzygniętych jedną bramką</div><div id="promotion-close-chart"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Tabela wzorców awansu</h3><div class="meta">Każdy wiersz pokazuje drużynę, która awansowała z II ligi. Kolumna „Miejsce awansu” dotyczy tej konkretnej ekipy, a nie Bosch.</div></div>
          <div id="promotion-benchmark-table"></div>
        </div>
        <div class="promotion-grid" id="promotion-cards"></div>
        <div class="dense-grid dense-2" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Liderzy awansu</h3><div class="meta">Zawodnicy, którzy ciągnęli promowane drużyny</div></div><div id="promotion-player-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Ścieżka ligowa ekip, które awansowały</h3><div class="meta">To nie jest historia Bosch. Każdy wiersz pokazuje, jak konkretna promowana drużyna została sklasyfikowana w jednej z tabel dostępnych w bazie ligi, także po awansie.</div></div><div id="promotion-history-table"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Mecze drużyn awansujących</h3><div class="meta">Pełny log spotkań sezonów zakończonych awansem</div></div>
          <div id="promotion-match-table"></div>
        </div>
        <div class="chapter-note" id="promotions-note"></div>
      </div>
    </section>
    <section class="section" id="orlik2026">
      <div class="head"><h2>Scouting Orlik 2026</h2><p>Prognoza przyszłej stawki Bosch na podstawie obecnej hali II ligi i ostatniego sezonu orlikowego. To rozdział praktyczny: kto może być najgroźniejszy, gdzie Bosch powinien szukać przewagi i które mecze trzeba potraktować jak obowiązek punktowy.</p></div>
      <div class="body">
        <div class="cards" id="orlik2026-summary-cards"></div>
        <div class="dense-grid dense-2" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Założenia scenariusza Bosch</h3><div class="meta">Przyjęte do tej analizy przyszłościowej</div></div>
            <div id="orlik2026-assumptions"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Globalny plan na lato</h3><div class="meta">Jak Bosch może wykorzystać szerszą kadrę</div></div>
            <div id="orlik2026-tips"></div>
          </div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Mapa rywali Orlika 2026</h3><div class="meta">Prognozowana stawka po wyjęciu dwóch drużyn awansujących do I ligi</div></div>
          <div id="orlik2026-table"></div>
        </div>
        <div class="chart-grid" style="margin-top:16px">
          <div class="chart"><h3>Poziom zagrożenia rywali</h3><div id="orlik2026-threat-chart"></div></div>
          <div class="chart"><h3>PPG rywali na Orliku 2025</h3><div class="meta">ostatni znany poziom punktowy na otwartym boisku; dopisek pokazuje różnicę względem obecnej hali</div><div id="orlik2026-shift-chart"></div></div>
        </div>
        <div class="promotion-grid" id="orlik2026-cards" style="margin-top:16px"></div>
        <div class="chapter-note" id="orlik2026-note"></div>
      </div>
    </section>

    <section class="section" id="video">
      <div class="head"><h2>Wideo</h2><p>Biblioteka publicznych nagrań Bosch: pokrycie sezonów, rekomendowane materiały i pełna lista sparowanych meczów.</p></div>
      <div class="body">
        <div class="split">
          <div class="table-card"><div class="table-top"><h3>Pokrycie sezonów wideo</h3><div class="meta">Ile oficjalnych meczów ma publiczny materiał</div></div><div id="video-season-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Profil Kanałów</h3><div class="meta">Które źródło daje ile materiału i z jakiego okresu</div></div><div id="channel-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Priorytetowe mecze do obejrzenia</h3><div class="meta">Najcenniejsze analitycznie materiały</div></div><div id="recommended-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Materiały niedopasowane</h3><div class="meta">Filmy Bosch bez pewnego przypisania do oficjalnego meczu</div></div><div id="unmatched-table"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px"><div class="table-top"><h3>Oficjalne mecze dopasowane do wideo</h3><div class="meta">Pełna biblioteka publicznych nagrań Bosch</div></div><div id="matched-table"></div></div>
        <div class="chapter-note" id="video-note"></div>
        <div class="foot">Wynik zawsze jest zapisany z perspektywy Bosch. Zapis „Bosch jako 1. zespół / 2. zespół” oznacza wyłącznie kolejność drużyn w technicznym wpisie meczu w bazie ligi.</div>
      </div>
    </section>

    <section class="section" id="recommendations">
      <div class="head"><h2>Rekomendacje</h2><p>Końcowe wnioski wdrożeniowe pod awans do I ligi. To sekcja decyzyjna: co poprawić, po co i po czym poznamy postęp.</p></div>
      <div class="body">
        <div class="reco-grid" id="recommendation-cards"></div>
        <div class="chapter-note" id="recommendations-note"></div>
      </div>
    </section>
  </div>
  <div id="global-tooltip" class="tooltip-layer" aria-hidden="true"></div>

  <script id="report-data" type="application/json">__REPORT_JSON__</script>
  <script id="video-data" type="application/json">__VIDEO_JSON__</script>
  <script id="promotion-data" type="application/json">__PROMO_JSON__</script>
  <script id="orlik2026-data" type="application/json">__ORLIK2026_JSON__</script>
  <script id="profile-data" type="application/json">__PROFILE_JSON__</script>
  <script id="reference-data" type="application/json">__REFERENCE_JSON__</script>
  <script>
    const REPORT=JSON.parse(document.getElementById('report-data').textContent);
    const VIDEO=JSON.parse(document.getElementById('video-data').textContent);
    const PROMO=JSON.parse(document.getElementById('promotion-data').textContent);
    const ORLIK2026=JSON.parse(document.getElementById('orlik2026-data').textContent);
    const PROFILE=JSON.parse(document.getElementById('profile-data').textContent);
    const REFERENCE=JSON.parse(document.getElementById('reference-data').textContent);
    const LEGEND=[["KPI","kluczowy wskaźnik efektywności"],["PPG","punkty na mecz"],["Pkt","punkty"],["Poz.","pozycja danej drużyny w konkretnej tabeli"],["Miejsce awansu","pozycja tej konkretnej drużyny w tabeli II ligi sezonu awansowego"],["M","mecze"],["W / R / P","wygrane / remisy / porażki"],["RB","różnica bramek"],["CS","clean sheets, czyli czyste konta"],["G","gole"],["A","asysty"],["G+A","gole plus asysty"],["G+A/M","gole plus asysty na mecz"],["MVP","piłkarz meczu"],["Top6","liczba oznaczeń top6 w publicznej bazie ligi"],["ŻK / CZK","żółte kartki / czerwone kartki"],["HT","wynik do przerwy"],["API ligi","techniczny interfejs i baza danych strony ligi"],["1. gol Bosch %","odsetek meczów, w których Bosch zdobył pierwszą bramkę"],["PPG po 1:0","średnia punktów po strzeleniu pierwszego gola"],["PPG po 0:1","średnia punktów po stracie pierwszego gola"],["Top half / Bottom half","górna i dolna połowa tabeli"],["Pkt/mecz stykowy","średnia liczba punktów zdobywanych w meczach stykowych"]];
    const TERMS={KPI:'Kluczowy wskaźnik efektywności. W tym raporcie to liczba, która szybko mówi, czy Bosch jest blisko poziomu awansu.',PPG:'Punkty na mecz. Pozwala porównywać sezony o różnej liczbie spotkań.',Pkt:'Punkty w tabeli ligowej.','Poz.':'Pozycja tej drużyny w konkretnej tabeli. W większości sekcji chodzi o Bosch, ale w rozdziale o awansach może chodzić o inną ekipę, która weszła do I ligi.','Miejsce awansu':'Pozycja tej konkretnej drużyny awansującej w tabeli II ligi sezonu awansowego. To nie jest pozycja Bosch, chyba że wiersz dotyczy Bosch Service Tech-Car.',M:'Liczba meczów.','W / R / P':'Wygrane, remisy i porażki.',RB:'Różnica bramek, czyli gole strzelone minus gole stracone.',CS:'Clean sheets, czyli mecze bez straconej bramki.',G:'Gole zawodnika lub drużyny.',A:'Asysty zawodnika.','G+A':'Gole plus asysty, czyli pełna produkcja ofensywna zawodnika.','G+A/M':'Średnia produkcja goli i asyst na jeden mecz.',MVP:'Piłkarz meczu według publicznych oznaczeń ligi.',Top6:'Dodatkowe wyróżnienie w publicznej bazie ligi.',API:'API to techniczny sposób, w jaki strona ligi udostępnia dane. W praktyce możesz czytać to po prostu jako bazę danych strony ligi.','API ligi':'Techniczny interfejs i baza danych strony ligi. W tym projekcie to źródło oficjalnych meczów, tabel i profili.','ŻK / CZK':'Żółte i czerwone kartki.',HT:'Wynik do przerwy. Pozwala ocenić, jak drużyna wchodzi w spotkanie.','1. gol Bosch %':'Odsetek meczów, w których Bosch zdobył pierwszą bramkę.','PPG po 1:0':'Średnia punktów, gdy Bosch strzela pierwszy gol.','PPG po 0:1':'Średnia punktów, gdy pierwszy gol strzela rywal.','Top half / Bottom half':'Górna i dolna połowa tabeli.','Mecz stykowy':'Remis albo mecz rozstrzygnięty jedną bramką. To najlepszy test zarządzania detalem.','Mecze stykowe':'Remisy albo mecze rozstrzygnięte jedną bramką. Pokazują, jak drużyna radzi sobie w końcówkach i pod presją.','Pkt/mecz stykowy':'Średnia liczba punktów zdobywanych w meczach stykowych, czyli w remisach oraz spotkaniach rozstrzygniętych jedną bramką.','Split konkurencyjności':'Podział meczów na rywali z górnej i dolnej połowy tabeli.','Ciągłość kadry':'Odsetek zawodników, którzy wrócili z poprzedniego sezonu.','Ciągłość':'Skrót od ciągłości kadry, czyli procentu zawodników zachowanych z poprzedniego sezonu.','Koncentracja produkcji':'Pokazuje, czy gole i punkty są szeroko rozłożone, czy skupione w kilku nazwiskach.','Slot API':'Informacja techniczna o tym, czy Bosch był zapisany jako pierwszy czy drugi zespół w bazie ligi. Nie mówi nic o sile drużyny, tylko o kolejności zapisu meczu.',Slot:'Skrót od sposobu zapisu meczu w bazie ligi. Pokazuje techniczną kolejność drużyn w danych.','Profil niepubliczny':'Zawodnik odzyskany z anonimowego identyfikatora ligi.','Archiwalny':'Zawodnik bez występu w bieżącym sezonie Hala 2025/2026.','Benchmark awansu':'Poziom drużyny z 2. miejsca, czyli realnego progu wejścia wyżej.','Wypuszczone pkt':'Punkty oddane po objęciu prowadzenia. To koszt niedomkniętych meczów.','Top1 goli':'Odsetek wszystkich goli Bosch strzelonych przez najlepszego strzelca.','Top3 goli':'Odsetek wszystkich goli Bosch strzelonych przez trzech najskuteczniejszych zawodników.','Top5 G+A':'Odsetek całej produkcji goli i asyst wygenerowanej przez pięciu najlepszych zawodników.','Gole/m':'Gole strzelone na mecz.','Stracone/m':'Gole stracone na mecz.','Pokrycie %':'Odsetek oficjalnych meczów, które mają publicznie dostępne wideo.',Segmenty:'Liczba dopasowanych fragmentów lub części materiału wideo do konkretnego spotkania.','Poz. w tej tabeli':'Pozycja tej konkretnej drużyny w pokazanej tabeli historycznej. W rozdziale o awansach nie dotyczy Bosch, tylko promowanej ekipy z danego wiersza.'};
    const CONCEPTS=[['Mecz stykowy','Remis albo mecz rozstrzygnięty jedną bramką.','To najlepszy test jakości końcówki i zarządzania detalem.'],['Split konkurencyjności','Podział meczów na rywali z górnej i dolnej połowy tabeli.','Pokazuje, czy Bosch daje liczby także przeciw mocniejszym.'],['Ciągłość kadry','Odsetek zawodników, którzy wrócili z poprzedniego sezonu.','Im wyższa, tym łatwiej o automatyzmy i stabilność.'],['Koncentracja produkcji','Jak duża część goli i G+A pochodzi od małej grupy zawodników.','Pokazuje, czy Bosch jest szeroki ofensywnie, czy zależny od kilku nazwisk.'],['API ligi','Techniczna baza danych i interfejs strony ligi.','W tym raporcie oznacza źródło oficjalnych meczów, tabel i profili.'],['Slot API','Układ techniczny rekordu: Bosch jako 1. albo 2. zespół.','Pomaga sprawdzić, czy sposób zapisu meczu nie myli interpretacji.'],['Benchmark awansu','Poziom drużyny z 2. miejsca.','To najprostsza odpowiedź, ile brakuje Bosch do realnej walki o awans.'],['Wypuszczone pkt','Punkty oddane mimo wcześniejszego prowadzenia.','To najszybsze źródło poprawy bez rewolucji kadrowej.'],['Pokrycie wideo','Odsetek meczów z publicznym nagraniem.','Im wyższe pokrycie, tym łatwiej łączyć liczby z realnym obrazem gry.']];
    LEGEND.push(['Nad 3.','przewaga punktowa nad pierwszym miejscem nieawansującym']);
    LEGEND.push(['Atak rank','miejsce w lidze pod względem liczby goli strzelonych']);
    LEGEND.push(['Obrona rank','miejsce w lidze pod względem najmniejszej liczby goli straconych']);
    LEGEND.push(['Ślad po awansie','pierwszy późniejszy wpis zespołu w I lidze widoczny w bazie']);
    LEGEND.push(['Poziom zagrożenia','syntetyczna ocena trudności rywala w prognozie Orlika 2026']);
    TERMS['Nad 3.']='Przewaga punktowa nad pierwszym miejscem, które nie dawało awansu. To prosty miernik, jak bezpieczny był awans.';
    TERMS['Atak rank']='Miejsce drużyny w lidze pod względem liczby strzelonych goli. 1 oznacza najlepszy atak w tej tabeli.';
    TERMS['Obrona rank']='Miejsce drużyny pod względem najmniejszej liczby straconych goli. 1 oznacza najszczelniejszą obronę.';
    TERMS['Ślad po awansie']='Pierwszy późniejszy wpis tej drużyny w tabeli I ligi, jaki udało się znaleźć w publicznej bazie.';
    TERMS['Poziom zagrożenia']='Autorska ocena trudności rywala w prognozie Orlika 2026. Łączy aktualne miejsce i PPG z hali, ślad z Orlika 2025, formę, liderów oraz to, jak Bosch wyglądał z tym zespołem na hali.';
    TERMS['Wzorzec awansu']='Profil liczbowy drużyny, która naprawdę awansowała, więc punkt odniesienia dla Bosch.';
    TERMS['Historia ligowa']='Wszystkie wpisy tej drużyny w tabelach ligowych znalezione w publicznej bazie strony ligi.';
    CONCEPTS.push(['Nad 3.','Przewaga nad pierwszym miejscem bez awansu.','Pokazuje, czy zespół wszedł wyżej komfortowo, czy na styku.']);
    CONCEPTS.push(['Atak rank / Obrona rank','Pozycja drużyny w lidze pod względem goli strzelonych i straconych.','Dzięki temu widać, czy awans budował przede wszystkim atak, obrona czy balans obu faz.']);
    CONCEPTS.push(['Ślad po awansie','Pierwszy późniejszy wpis tej drużyny w I lidze znaleziony w bazie.','To skrótowy test, jak awansująca drużyna wyglądała po wejściu poziom wyżej.']);
    const defaultPromoFilters=()=>({surface:'all',rank:'all',buffer:'all',profile:'all'});
    const state={query:'',status:'all',sort:{},promo:defaultPromoFilters()},renderers=[];
    state.video='all';
    state.groups=new Set();
    state.years=new Set();
    state.seasons=new Set();
    const GROUP_OPTIONS=[{id:'current',label:'Bieżący'},{id:'peak',label:'Peak historyczny'},{id:'hala',label:'Wszystkie hale'},{id:'orlik',label:'Wszystkie orliki'}];
    const PROMO_SURFACE_OPTIONS=[{id:'all',label:'Wszystko'},{id:'hala',label:'Tylko hale'},{id:'orlik',label:'Tylko orliki'}];
    const stateMap=new Map(REPORT.state_rows.map(r=>[String(r.sid),r])),closeMap=new Map(REPORT.close_game_rows.map(r=>[String(r.sid),r])),contMap=new Map(REPORT.continuity_rows.map(r=>[String(r.sid),r])),concMap=new Map(REPORT.concentration_rows.map(r=>[String(r.sid),r])),videoMap=new Map(VIDEO.season_rows.map(r=>[String(r.sid),r])),benchmarkMap=new Map(REPORT.benchmark.map(r=>[String(r.season_id),r])),playerCardMap=new Map(REPORT.player_cards.map(r=>[r.player_id,r]));
    const tooltipLayer=document.getElementById('global-tooltip');
    let activeTooltipTerm=null;
    const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const escAttr=s=>esc(s).replaceAll("'","&#39;");
    const norm=s=>String(s??'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
    const num=v=>{if(typeof v==='number')return v;const n=Number(String(v).replace('%','').replace(',','.'));return Number.isNaN(n)?null:n};
    const safeNum=(v,fallback=0)=>{const n=num(v);return n===null?fallback:n};
    const tip=(label,key=label)=>`<span class="term" tabindex="0" data-tip="${escAttr(TERMS[key]||TERMS[label]||'')}">${esc(label)}</span>`;
    const formatDate=value=>{if(!value)return'';const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleDateString('pl-PL')};
    const prettyNum=(value,decimals=2)=>{if(value==null||!Number.isFinite(value))return'-';const rounded=Number(value.toFixed(decimals));return String(rounded).replace(/\\.0$/,'')};
    const extractSeasonYear=label=>{const matches=String(label??'').match(/\\d{4}/g);return matches&&matches.length?matches[matches.length-1]:'0'};
    const seasonMeta=REPORT.season_rows.map(r=>({...r,sid_str:String(r.sid),surface:norm(r.season).includes('hala')?'hala':'orlik',year_key:extractSeasonYear(r.season)}));
    const seasonMetaMap=new Map(seasonMeta.map(r=>[r.sid_str,r]));
    const allSeasonIds=seasonMeta.map(r=>r.sid_str);
    const yearOptions=[...new Set(seasonMeta.map(r=>r.year_key))].sort((a,b)=>Number(a)-Number(b));
    const mobileCharts=()=>window.matchMedia('(max-width: 720px)').matches;
    const cleanProfileName=value=>String(value??'').replace(/\\s*[–-]\\s*Podlaska Liga Piłkarska\\s*$/,'').trim();
    const profileMap=new Map(Object.entries(PROFILE||{}).map(([key,entry])=>[key,{...entry,resolved_name:cleanProfileName(entry?.resolved_name)}]));
    const publicProfileNameMap=new Map([...profileMap.values()].filter(entry=>entry?.public&&entry?.resolved_name).map(entry=>[norm(entry.resolved_name),entry]));
    const teamRefByIdMap=REFERENCE?.teams?.by_id||{};
    const teamRefByNameMap=new Map(Object.entries(REFERENCE?.teams?.by_name||{}));
    const tableRefByIdMap=REFERENCE?.tables?.by_id||{};
    const tableRefBySeasonTitleMap=new Map(Object.entries(REFERENCE?.tables?.by_season_title||{}));
    const wrapLabel=(value,maxChars=14)=>{const words=String(value??'').split(/\\s+/).filter(Boolean);if(!words.length)return[''];const lines=[];let line='';for(const word of words){const candidate=line?`${line} ${word}`:word;if(candidate.length<=maxChars||!line){line=candidate}else{lines.push(line);line=word}}if(line)lines.push(line);return lines.slice(0,3)};
    const svgLabel=(x,y,value,{maxChars=14,lineHeight=12,fontSize=10,fill='#5b6b7d'}={})=>{const lines=wrapLabel(value,maxChars);const startY=y-((lines.length-1)*lineHeight)/2;return `<text x="${x}" y="${startY}" text-anchor="middle" font-size="${fontSize}" fill="${fill}">${lines.map((line,index)=>`<tspan x="${x}" dy="${index===0?0:lineHeight}">${esc(line)}</tspan>`).join('')}</text>`};
    function attachProfile(row){
      if(!row||typeof row!=='object')return row;
      const pid=row.player_id;
      if(pid==null)return row;
      const entry=profileMap.get(String(pid));
      if(!entry)return row;
      if(entry.resolved_name&&(!row.name||String(row.name).includes('Zawodnik #'))) row.name=entry.resolved_name;
      if(entry.profile_url) row.profile_url=entry.profile_url;
      row.profile_public=Boolean(entry.public);
      return row;
    }
    function applyProfileMap(){
      [REPORT.current_players,REPORT.overall_apps,REPORT.overall_points,REPORT.player_cards,REPORT.resolved_hidden_players,PROMO.player_rows].forEach(rows=>rows?.forEach(attachProfile));
      PROMO.promotions.forEach(row=>{
        attachProfile(row.top_scorer);
        attachProfile(row.top_creator);
        attachProfile(row.top_points_player);
        (row.leaders||[]).forEach(attachProfile);
      });
    }
    function playerLink(playerId,name,profileUrl='',className=''){
      const entry=playerId!=null?profileMap.get(String(playerId)):null;
      const display=(entry?.resolved_name&&(String(name??'').includes('Zawodnik #')||!String(name??'').trim()))?entry.resolved_name:String(name??entry?.resolved_name??'');
      const href=profileUrl||entry?.profile_url||'';
      const cls=className?` class="${className}"`:'';
      if(href&&(entry?.public||profileUrl)) return `<a href="${href}" target="_blank" rel="noreferrer"${cls}>${esc(display)}</a>`;
      return `<span${cls}>${esc(display)}</span>`;
    }
    const playerLinkFromRow=(row,className='')=>playerLink(row?.player_id,row?.name,row?.profile_url,className);
    function playerLinkByName(name,className=''){
      const entry=publicProfileNameMap.get(norm(name));
      if(entry?.profile_url) return `<a href="${entry.profile_url}" target="_blank" rel="noreferrer"${className?` class="${className}"`:''}>${esc(name)}</a>`;
      return `<span${className?` class="${className}"`:''}>${esc(name)}</span>`;
    }
    function playerPairLinks(value){
      return String(value??'').split(' / ').map(name=>playerLinkByName(name.trim())).join(' / ');
    }
    function linkOrSpan(href,label,className=''){
      const cls=className?` class="${className}"`:'';
      if(href) return `<a href="${href}" target="_blank" rel="noreferrer"${cls}>${esc(label)}</a>`;
      return `<span${cls}>${esc(label)}</span>`;
    }
    const teamRefById=id=>id!=null?teamRefByIdMap[String(id)]||null:null;
    function teamRefByName(name){
      const id=teamRefByNameMap.get(norm(name));
      return id?teamRefById(id):null;
    }
    const tableRefById=id=>id!=null?tableRefByIdMap[String(id)]||null:null;
    function seasonTableRef(seasonId,tableTitle=''){
      const title=String(tableTitle||seasonMetaMap.get(String(seasonId))?.table_title||'').trim();
      if(!seasonId||!title)return null;
      const tableId=tableRefBySeasonTitleMap.get(`${seasonId}|${norm(title)}`);
      return tableId?tableRefById(tableId):null;
    }
    function teamLink(teamId,name,className=''){
      const ref=teamRefById(teamId)||teamRefByName(name);
      const label=String(name??ref?.name??'').trim();
      return linkOrSpan(ref?.link||'',label,className);
    }
    const teamLinkByName=(name,className='')=>teamLink(null,name,className);
    function tableLinkById(tableId,label,className=''){
      const ref=tableRefById(tableId);
      const text=String(label??ref?.title??'').trim();
      return linkOrSpan(ref?.link||'',text,className);
    }
    function seasonTableLink(seasonId,label,tableTitle='',className=''){
      const ref=seasonTableRef(seasonId,tableTitle||label);
      const text=String(label??tableTitle??ref?.title??'').trim();
      return linkOrSpan(ref?.link||'',text,className);
    }
    function eventLink(url,label='wydarzenie',className=''){
      return linkOrSpan(url||'',label,className);
    }
    function matchLink(row,label='',className=''){
      const text=String(label||row?.match||'').trim();
      return linkOrSpan(row?.event_link||'',text,className);
    }
    applyProfileMap();
    const rowSeason=r=>String(r.sid??r.season_id??'');
    const toggleSetValue=(set,value)=>{set.has(value)?set.delete(value):set.add(value)};
    function selectedSeasonIds(){
      const ids=new Set();
      if(state.groups.has('current')) ids.add(String(REPORT.current_season_id));
      if(state.groups.has('peak')) ids.add(String(REPORT.peak_season_id));
      if(state.groups.has('hala')) seasonMeta.filter(r=>r.surface==='hala').forEach(r=>ids.add(r.sid_str));
      if(state.groups.has('orlik')) seasonMeta.filter(r=>r.surface==='orlik').forEach(r=>ids.add(r.sid_str));
      if(state.years.size) seasonMeta.filter(r=>state.years.has(r.year_key)).forEach(r=>ids.add(r.sid_str));
      if(state.seasons.size) state.seasons.forEach(id=>ids.add(id));
      if(!ids.size) allSeasonIds.forEach(id=>ids.add(id));
      return ids;
    }
    const selectedSeasonRows=()=>seasonMeta.filter(r=>selectedSeasonIds().has(r.sid_str));
    const seasonRow=()=>selectedSeasonRows().length===1?selectedSeasonRows()[0]:null;
    const passSeason=r=>selectedSeasonIds().has(rowSeason(r));
    const activeRangeLabel=()=>{const rows=selectedSeasonRows();if(!state.groups.size&&!state.years.size&&!state.seasons.size)return'Wszystkie sezony';if(rows.length===1)return rows[0].season;if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('hala'))return'Wszystkie hale';if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('orlik'))return'Wszystkie orliki';if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('current'))return REPORT.current_season_name;if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('peak'))return REPORT.peak_season_name;if(!state.groups.size&&state.years.size===1&&!state.seasons.size)return`Rok ${[...state.years][0]}`;return`${rows.length} sezonów`};
    const passQuery=r=>!state.query||norm(JSON.stringify(r)).includes(norm(state.query));
    const passVideo=r=>{if(state.video==='all')return true;const withVideo=Number(r.video_count??r.matches_with_video??r.matched??0)>0;const coverage=norm(r.coverage_type??'');if(state.video==='with')return withVideo;if(state.video==='without'){if(r.matches_with_video!=null)return Number(r.matches_with_video)===0;if(r.video_count!=null)return Number(r.video_count)===0;if(r.matched!=null&&r.unmatched!=null)return Number(r.matched)===0;return !withVideo}if(state.video==='full')return coverage.includes('pełne')||coverage.includes('pelne')||Number(r.full_matches??0)>0;return true};
    const promotionKey=row=>`${row.team_id}|${row.sid}`;
    const passPromotionFilter=row=>{
      if(state.promo.surface!=='all'&&norm(row.surface)!==state.promo.surface)return false;
      if(state.promo.rank!=='all'&&String(row.rank)!==state.promo.rank)return false;
      if(state.promo.buffer==='tight'&&safeNum(row.gap_to_third,0)>2)return false;
      if(state.promo.buffer==='safe'&&safeNum(row.gap_to_third,0)<4)return false;
      if(state.promo.profile==='defense_top2'&&safeNum(row.defense_rank,99)>2)return false;
      if(state.promo.profile==='attack_top2'&&safeNum(row.attack_rank,99)>2)return false;
      if(state.promo.profile==='balanced_top2'&&!(safeNum(row.defense_rank,99)<=2&&safeNum(row.attack_rank,99)<=2))return false;
      if(state.promo.profile==='wide_attack'&&safeNum(row.top3_goal_share,999)>55)return false;
      return true;
    };
    function renderPromotionControls(){
      const surfaceEl=document.getElementById('promotion-surface-chips');
      const rankEl=document.getElementById('promotion-rank-filter');
      const bufferEl=document.getElementById('promotion-buffer-filter');
      const profileEl=document.getElementById('promotion-profile-filter');
      const metaEl=document.getElementById('promotion-filter-meta');
      if(surfaceEl)surfaceEl.innerHTML=PROMO_SURFACE_OPTIONS.map(item=>`<button type="button" class="chip-btn ${state.promo.surface===item.id?'active':''}" data-promo-surface="${item.id}">${esc(item.label)}</button>`).join('');
      if(rankEl)rankEl.value=state.promo.rank;
      if(bufferEl)bufferEl.value=state.promo.buffer;
      if(profileEl)profileEl.value=state.promo.profile;
      if(metaEl){
        const baseRows=PROMO.promotions.filter(passSeason);
        const activeRows=baseRows.filter(passPromotionFilter);
        const parts=[];
        if(state.promo.surface!=='all')parts.push(state.promo.surface==='hala'?'same hale':'same orliki');
        if(state.promo.rank!=='all')parts.push(`tylko ${state.promo.rank}. miejsce`);
        if(state.promo.buffer==='tight')parts.push('bufor do 2 pkt nad 3.');
        if(state.promo.buffer==='safe')parts.push('bufor 4+ pkt nad 3.');
        if(state.promo.profile==='defense_top2')parts.push('obrona top2');
        if(state.promo.profile==='attack_top2')parts.push('atak top2');
        if(state.promo.profile==='balanced_top2')parts.push('balans top2/top2');
        if(state.promo.profile==='wide_attack')parts.push('szeroka produkcja goli');
        metaEl.textContent=baseRows.length?`${activeRows.length} z ${baseRows.length} awansów w aktywnym zakresie${parts.length?` • ${parts.join(' • ')}`:''}`:'Brak awansów dla aktywnego zakresu strony';
      }
    }
    function renderRangeControls(){
      const groupEl=document.getElementById('group-chips'),yearEl=document.getElementById('year-chips'),seasonEl=document.getElementById('season-chips');
      if(groupEl)groupEl.innerHTML=GROUP_OPTIONS.map(item=>`<button type="button" class="chip-btn ${state.groups.has(item.id)?'active':''}" data-kind="group" data-value="${item.id}">${esc(item.label)}</button>`).join('');
      if(yearEl)yearEl.innerHTML=yearOptions.map(year=>`<button type="button" class="chip-btn ${state.years.has(year)?'active':''}" data-kind="year" data-value="${year}">Rok ${esc(year)}</button>`).join('');
      if(seasonEl)seasonEl.innerHTML=seasonMeta.map(row=>`<button type="button" class="chip-btn ${state.seasons.has(row.sid_str)?'active':''}" data-kind="season" data-value="${row.sid_str}">${esc(row.season)}</button>`).join('');
    }
    function bindControls(){
      document.getElementById('query-filter').addEventListener('input',e=>{state.query=e.target.value;refresh()});
      document.getElementById('status-filter').addEventListener('change',e=>{state.status=e.target.value;refresh()});
      document.getElementById('video-filter').addEventListener('change',e=>{state.video=e.target.value;refresh()});
      [['group-chips','group',state.groups],['year-chips','year',state.years],['season-chips','season',state.seasons]].forEach(([id,kind,set])=>{document.getElementById(id)?.addEventListener('click',e=>{const btn=e.target.closest(`button[data-kind="${kind}"]`);if(!btn)return;toggleSetValue(set,btn.dataset.value);sync();refresh()})});
      document.getElementById('range-all')?.addEventListener('click',()=>{state.groups.clear();state.years.clear();state.seasons.clear();sync();refresh()});
      document.getElementById('promotion-surface-chips')?.addEventListener('click',e=>{const btn=e.target.closest('button[data-promo-surface]');if(!btn)return;state.promo.surface=btn.dataset.promoSurface;sync();refresh()});
      document.getElementById('promotion-rank-filter')?.addEventListener('change',e=>{state.promo.rank=e.target.value;sync();refresh()});
      document.getElementById('promotion-buffer-filter')?.addEventListener('change',e=>{state.promo.buffer=e.target.value;sync();refresh()});
      document.getElementById('promotion-profile-filter')?.addEventListener('change',e=>{state.promo.profile=e.target.value;sync();refresh()});
      document.getElementById('promotion-reset')?.addEventListener('click',()=>{state.promo=defaultPromoFilters();sync();refresh()});
      document.getElementById('reset-filters').addEventListener('click',()=>{state.query='';state.status='all';state.video='all';state.groups.clear();state.years.clear();state.seasons.clear();state.promo=defaultPromoFilters();sync();refresh()});
    }
    let toolbarObserver=null;
    const isMobileToolbar=()=>window.matchMedia('(max-width: 900px)').matches;
    function moveToolbarPanel(targetId){
      const panel=document.getElementById('toolbar-panel');
      const target=document.getElementById(targetId);
      if(panel&&target&&panel.parentElement!==target) target.appendChild(panel);
    }
    function updateToolbarSummary(){
      const summary=document.getElementById('toolbar-summary');
      const compactSummary=document.getElementById('toolbar-fly-summary');
      const seasonLabel=activeRangeLabel();
      const statusLabel=({all:'wszyscy',obecny:'obecni',archiwalny:'archiwalni'})[state.status]||state.status;
      const videoLabel=({all:'wideo: wszystko',with:'wideo: tylko z nagraniem',without:'wideo: bez nagrania',full:'wideo: pełne mecze'})[state.video]||state.video;
      const queryPart=state.query?`szukaj: ${state.query.length>18?`${state.query.slice(0,18)}…`:state.query}`:'';
      const text=[seasonLabel,statusLabel,videoLabel,queryPart].filter(Boolean).join(' • ');
      if(summary) summary.textContent=text;
      if(compactSummary) compactSummary.textContent=text;
    }
    function setToolbarOpen(open){
      const toolbar=document.getElementById('toolbar');
      const toggle=document.getElementById('toolbar-toggle');
      if(!toolbar||!toggle) return;
      moveToolbarPanel('toolbar-panel-inline');
      const expanded=isMobileToolbar()&&open;
      toolbar.classList.toggle('open',expanded);
      toggle.setAttribute('aria-expanded',expanded?'true':'false');
      toggle.setAttribute('aria-label',expanded?'Zamknij filtry i nawigację':'Otwórz filtry i nawigację');
      document.body.classList.toggle('toolbar-lock',expanded);
      updateToolbarSummary();
    }
    function updateDesktopToggle(){
      const fly=document.getElementById('toolbar-fly');
      const desktopToggle=document.getElementById('toolbar-desktop-toggle');
      if(!fly||!desktopToggle) return;
      const expanded=fly.classList.contains('open');
      desktopToggle.textContent=expanded?'Zwiń filtry':'Rozwiń filtry';
      desktopToggle.setAttribute('aria-expanded',expanded?'true':'false');
    }
    function setDesktopFlyOpen(open){
      const fly=document.getElementById('toolbar-fly');
      if(!fly||isMobileToolbar()){
        moveToolbarPanel('toolbar-panel-inline');
        updateDesktopToggle();
        return;
      }
      const expanded=Boolean(open)&&fly.classList.contains('active');
      fly.classList.toggle('open',expanded);
      moveToolbarPanel(expanded?'toolbar-fly-panel':'toolbar-panel-inline');
      updateDesktopToggle();
    }
    function syncDesktopFly(active){
      const fly=document.getElementById('toolbar-fly');
      if(!fly||isMobileToolbar()){
        fly?.classList.remove('active','open');
        fly?.setAttribute('aria-hidden','true');
        moveToolbarPanel('toolbar-panel-inline');
        updateDesktopToggle();
        return;
      }
      fly.classList.toggle('active',active);
      fly.setAttribute('aria-hidden',active?'false':'true');
      if(!active) setDesktopFlyOpen(false);
      else updateDesktopToggle();
    }
    function installToolbarObserver(){
      const sentinel=document.getElementById('toolbar-sentinel');
      if(toolbarObserver){
        toolbarObserver.disconnect();
        toolbarObserver=null;
      }
      if(!sentinel||isMobileToolbar()){
        syncDesktopFly(false);
        return;
      }
      toolbarObserver=new IntersectionObserver(entries=>{
        const entry=entries[0];
        syncDesktopFly(!entry.isIntersecting);
      },{threshold:[0],rootMargin:'-10px 0px 0px 0px'});
      toolbarObserver.observe(sentinel);
    }
    function syncToolbarState(){
      setToolbarOpen(false);
      setDesktopFlyOpen(false);
      installToolbarObserver();
    }
    function initToolbar(){
      const toolbar=document.getElementById('toolbar');
      const toggle=document.getElementById('toolbar-toggle');
      const close=document.getElementById('toolbar-close');
      const backdrop=document.getElementById('toolbar-backdrop');
      const desktopToggle=document.getElementById('toolbar-desktop-toggle');
      const fly=document.getElementById('toolbar-fly');
      if(!toolbar||!toggle) return;
      const mq=window.matchMedia('(max-width: 900px)');
      toggle.addEventListener('click',()=>setToolbarOpen(!toolbar.classList.contains('open')));
      close?.addEventListener('click',()=>setToolbarOpen(false));
      backdrop?.addEventListener('click',()=>setToolbarOpen(false));
      desktopToggle?.addEventListener('click',()=>{
        if(isMobileToolbar()) return;
        setDesktopFlyOpen(!fly?.classList.contains('open'));
      });
      mq.addEventListener('change',()=>syncToolbarState());
      window.addEventListener('resize',()=>installToolbarObserver());
      document.addEventListener('keydown',e=>{
        if(e.key==='Escape'&&mq.matches&&toolbar.classList.contains('open')) setToolbarOpen(false);
        if(e.key==='Escape'&&!mq.matches&&fly?.classList.contains('open')) setDesktopFlyOpen(false);
      });
      document.addEventListener('click',e=>{
        if(isMobileToolbar()||!fly?.classList.contains('open')) return;
        if(fly.contains(e.target)) return;
        setDesktopFlyOpen(false);
      });
      document.querySelectorAll('.nav a').forEach(link=>link.addEventListener('click',()=>{
        if(mq.matches) setToolbarOpen(false);
        if(!mq.matches) setDesktopFlyOpen(false);
      }));
      syncToolbarState();
    }
    function initResponsiveCharts(){
      let lastMode=mobileCharts();
      window.addEventListener('resize',()=>{const nextMode=mobileCharts();if(nextMode!==lastMode){lastMode=nextMode;refresh()}});
    }
    function placeTooltip(target){
      if(!target||!tooltipLayer)return;
      const text=target.dataset.tip||'';
      if(!text){hideTooltip();return}
      tooltipLayer.textContent=text;
      tooltipLayer.classList.add('show');
      tooltipLayer.setAttribute('aria-hidden','false');
      tooltipLayer.style.left='12px';
      tooltipLayer.style.top='12px';
      const margin=12;
      const rect=target.getBoundingClientRect();
      const tipRect=tooltipLayer.getBoundingClientRect();
      let left=rect.left+(rect.width/2)-(tipRect.width/2);
      left=Math.max(margin,Math.min(left,window.innerWidth-tipRect.width-margin));
      let top=rect.bottom+12;
      if(top+tipRect.height>window.innerHeight-margin) top=rect.top-tipRect.height-12;
      if(top<margin) top=Math.max(margin,Math.min(window.innerHeight-tipRect.height-margin,rect.bottom+12));
      tooltipLayer.style.left=`${left}px`;
      tooltipLayer.style.top=`${top}px`;
    }
    function showTooltip(target){activeTooltipTerm=target;placeTooltip(target)}
    function hideTooltip(){activeTooltipTerm=null;if(!tooltipLayer)return;tooltipLayer.classList.remove('show');tooltipLayer.setAttribute('aria-hidden','true')}
    function initTooltips(){
      document.addEventListener('mouseover',e=>{const term=e.target.closest?.('.term');if(term&&term.dataset.tip)showTooltip(term)});
      document.addEventListener('mouseout',e=>{if(!activeTooltipTerm)return;const next=e.relatedTarget&&e.relatedTarget.closest?e.relatedTarget.closest('.term'):null;if(next===activeTooltipTerm)return;if(e.target.closest?.('.term')===activeTooltipTerm)hideTooltip()});
      document.addEventListener('focusin',e=>{const term=e.target.closest?.('.term');if(term&&term.dataset.tip)showTooltip(term)});
      document.addEventListener('focusout',e=>{if(e.target.closest?.('.term')===activeTooltipTerm)hideTooltip()});
      window.addEventListener('scroll',()=>{if(activeTooltipTerm)placeTooltip(activeTooltipTerm)},true);
      window.addEventListener('resize',()=>{if(activeTooltipTerm)placeTooltip(activeTooltipTerm)});
    }
    function sync(){document.getElementById('query-filter').value=state.query;document.getElementById('status-filter').value=state.status;document.getElementById('video-filter').value=state.video;renderRangeControls();renderPromotionControls();updateToolbarSummary()}
    const sumBy=(rows,pick)=>rows.reduce((acc,row)=>acc+safeNum(pick(row),0),0);
    const statusFor=(current,target,mode='high')=>{if(current==null||target==null||!Number.isFinite(current)||!Number.isFinite(target))return'luka';if(mode==='low'){if(current<=target)return'mocne';if(current<=target*1.1)return'blisko';return'luka'}if(current>=target)return'mocne';if(current>=target*0.9)return'blisko';return'luka'};
    const selectedMatchRows=()=>VIDEO.match_rows.filter(r=>selectedSeasonIds().has(String(r.sid)));
    const promotionRowsActive=()=>PROMO.promotions.filter(passSeason).filter(passPromotionFilter);
    const promotionRowsVisible=()=>promotionRowsActive().filter(passQuery);
    function promotionSelectionActive(){
      const rows=promotionRowsActive();
      return{rows,keys:new Set(rows.map(promotionKey))};
    }
    function promotionPlayerRowsActive(){
      const selection=promotionSelectionActive();
      return PROMO.player_rows.filter(row=>selection.keys.has(promotionKey(row)));
    }
    function promotionMatchRowsActive(){
      const selection=promotionSelectionActive();
      return PROMO.match_rows.filter(row=>selection.keys.has(promotionKey(row)));
    }
    function promotionHistoryRowsActive(){
      return promotionRowsActive().flatMap(row=>(row.league_history||[]).map(hist=>({...hist,sid:row.sid,promotion_team:row.team_name,promotion_season:row.season,post_flag:row.first_post_top_tier&&hist.season_id===row.first_post_top_tier.season_id&&hist.table_id===row.first_post_top_tier.table_id?'tak':''})));
    }
    function promotionSummaryActive(){
      const rows=promotionRowsVisible();
      if(!rows.length)return null;
      const avg=value=>rows.reduce((acc,row)=>acc+value(row),0)/rows.length;
      return{teams:rows.length,avg_ppg:avg(row=>safeNum(row.ppg,0)),avg_gap_to_third:avg(row=>safeNum(row.gap_to_third,0)),avg_ga_pg:avg(row=>safeNum(row.ga,0)/Math.max(1,safeNum(row.matches,1))),avg_close_ppg:avg(row=>safeNum(row.close_ppg,0)),avg_top3_goal_share:avg(row=>safeNum(row.top3_goal_share,0)),avg_first_goal_share:avg(row=>safeNum(row.first_goal_share,0)),avg_points_dropped:avg(row=>safeNum(row.points_dropped_from_leads,0))};
    }
    function promotionPostText(row){
      const post=row.first_post_top_tier;
      return post?`${tableLinkById(post.table_id,post.table_title)}: ${post.pos}. miejsce, ${post.points} pkt, ${post.gf}:${post.ga}`:'brak późniejszego wpisu I ligi w widocznej bazie';
    }
    function promotionProfileLine(row){
      const attack=row.attack_rank===1?'najmocniejszy atak ligi':row.attack_rank===2?'atak z top2 ligi':`${row.attack_rank}. wynik strzelecki ligi`;
      const defense=row.defense_rank===1?'najszczelniejsza obrona ligi':row.defense_rank===2?'obrona z top2 ligi':`${row.defense_rank}. wynik defensywny ligi`;
      const buffer=row.gap_to_third>=4?'awans z wyraźnym buforem nad 3. miejscem':row.gap_to_third<=1?'awans wygrany praktycznie na styku':'awans z umiarkowanym zapasem nad 3. miejscem';
      const spread=row.top3_goal_share<=52?'szeroko rozłożona produkcja goli':row.top3_goal_share>=65?'mocno skupiona produkcja w top3':'średnio skupiona produkcja';
      return `${attack}, ${defense}, ${buffer}, ${spread}.`;
    }
    const isOrlikSeasonLabel=label=>norm(label).includes('orlik');
    function latestBoschOrlikMatch(teamId,teamName){
      return [...VIDEO.match_rows]
        .filter(row=>isOrlikSeasonLabel(row.season)&&((teamId!=null&&String(row.opponent_id??'')===String(teamId))||norm(row.display_opponent||row.opponent)===norm(teamName)))
        .sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')))[0]||null;
    }
    const orlik2026RowsActive=()=>(ORLIK2026.opponents||[]).map(row=>({...row,bosch_orlik_match:latestBoschOrlikMatch(row.team_id,row.team_name)}));
    const orlik2026RowsVisible=()=>orlik2026RowsActive().filter(passQuery);
    const orlik2026ThreatClass=level=>{const value=norm(level);if(value.includes('wysok')) return 'red';if(value.includes('sred')||value.includes('śred')) return 'orange';return 'teal'};
    function orlik2026Leader(row,index=0,source='hall'){
      const list=source==='orlik'?(row.orlik_2025_top_players||[]):(row.top_players||[]);
      return list[index]||null;
    }
    function orlik2026LeaderInline(player){
      return player?`${playerLinkFromRow(player)} <span class="tag-sep">•</span> <span>${player.points} G+A</span>`:'brak lidera w publicznej bazie';
    }
    function orlik2026LeaderLine(row,source='hall'){
      return orlik2026LeaderInline(orlik2026Leader(row,0,source));
    }
    function orlik2026LeaderList(row,source='hall',limit=3){
      const list=(source==='orlik'?(row.orlik_2025_top_players||[]):(row.top_players||[])).slice(0,limit);
      return list.length?list.map(player=>`<li>${playerLinkFromRow(player)} — ${player.goals} G, ${player.assists} A, ${player.points} G+A</li>`).join(''):'<li>brak publicznych danych indywidualnych</li>';
    }
    function orlik2026DeltaText(diff){
      if(diff==null||!Number.isFinite(diff)) return '';
      if(Math.abs(diff)<0.01) return 'poziom bardzo zbliżony do obecnej hali';
      if(diff>0) return `o ${prettyNum(diff,2)} pkt/mecz lepiej niż na obecnej hali`;
      return `o ${prettyNum(Math.abs(diff),2)} pkt/mecz słabiej niż na obecnej hali`;
    }
    function orlik2026TableCell(row){
      if(!row.orlik_2025) return '<div class="cell-stack"><div class="cell-note">brak wpisu tego zespołu w Orliku 2025</div></div>';
      const diff=safeNum(row.orlik_2025.ppg,0)-safeNum(row.hall.ppg,0);
      const leader=orlik2026Leader(row,0,'orlik');
      return `<div class="cell-stack"><div class="cell-line">${rankTag(row.orlik_2025.pos)}<span class="cell-note">${prettyNum(row.orlik_2025.ppg)} pkt/mecz na Orliku 2025</span></div><div class="cell-note ${diff>=0?'delta-up':'delta-down'}">${orlik2026DeltaText(diff)}</div>${leader?`<div class="cell-note">lider orlika: ${playerLinkFromRow(leader)} — ${leader.points} G+A</div>`:''}</div>`;
    }
    function orlik2026MatchCell(match,label){
      if(!match) return '<div class="cell-stack"><div class="cell-note">brak wcześniejszego meczu Bosch</div></div>';
      return `<div class="cell-stack"><div class="cell-line">${scoreBadgeFor(match.gf,match.ga,`${match.gf}:${match.ga}`)}<span class="cell-note">${formatDate(match.date)}</span></div><div class="cell-note"><a href="${match.event_link||match.link}" target="_blank" rel="noreferrer">${label}</a></div></div>`;
    }
    function orlik2026HallCell(row){
      return orlik2026MatchCell(row.bosch_hall_match,'ostatni mecz hali Bosch');
    }
    function cleanInline(html){
      return String(html).replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim();
    }
    function orlik2026OrlikSummary(row){
      if(!row.orlik_2025) return 'Brak widocznego wpisu tego rywala w Orliku 2025, więc latem trzeba go czytać bardziej przez obecną halę niż przez gotowy wzorzec gry na większej przestrzeni.';
      const diff=safeNum(row.orlik_2025.ppg,0)-safeNum(row.hall.ppg,0);
      const leader=orlik2026Leader(row,0,'orlik');
      const base=row.orlik_2025.pos<=5?`Na Orliku 2025 ${row.team_name} było realnie konkurencyjne: ${row.orlik_2025.pos}. miejsce i ${prettyNum(row.orlik_2025.ppg)} pkt/mecz.`:row.orlik_2025.pos<=10?`Na Orliku 2025 ${row.team_name} siedziało w środku stawki: ${row.orlik_2025.pos}. miejsce i ${prettyNum(row.orlik_2025.ppg)} pkt/mecz.`:`Na Orliku 2025 ${row.team_name} nie weszło wysoko: ${row.orlik_2025.pos}. miejsce i ${prettyNum(row.orlik_2025.ppg)} pkt/mecz.`;
      const trend=`To było ${orlik2026DeltaText(diff)}.`;
      const leaderText=leader?`Głównym liderem tamtego orlika był ${cleanInline(orlik2026LeaderInline(leader))}.`:'';
      return [base,trend,leaderText].filter(Boolean).join(' ');
    }
    function orlik2026ShiftRows(){
      return orlik2026RowsActive()
        .filter(row=>row.orlik_2025&&row.orlik_2025.ppg!=null)
        .map(row=>({
          ...row,
          orlik_ppg:safeNum(row.orlik_2025.ppg,0),
          shift:Number((safeNum(row.orlik_2025.ppg,0)-safeNum(row.hall.ppg,0)).toFixed(2)),
          shift_note:orlik2026DeltaText(safeNum(row.orlik_2025.ppg,0)-safeNum(row.hall.ppg,0)),
          label:`${row.team_name} (${row.orlik_2025.pos}. miejsce Orlik 2025)`,
        }));
    }
    function renderAnalysisList(targetId,rows){
      const el=document.getElementById(targetId);
      if(!el) return;
      el.innerHTML=`<div class="analysis-stack">${rows.map((row,index)=>`<div class="analysis-row"><strong>${esc(row.title||`Punkt ${index+1}`)}</strong><p>${row.detail}</p></div>`).join('')}</div>`;
    }
    function renderOrlik2026Summary(){
      const el=document.getElementById('orlik2026-summary-cards');
      if(!el) return;
      const rows=orlik2026RowsVisible();
      if(!rows.length){el.innerHTML='<div class="empty">Brak rywali Orlika 2026 dla aktywnego wyszukiwania.</div>';return}
      const avgHallPpg=rows.reduce((acc,row)=>acc+safeNum(row.hall.ppg,0),0)/rows.length;
      const topThreat=rows[0];
      const mustWin=rows.filter(row=>safeNum(row.hall.pos,99)>=12).length;
      const bottomTwo=rows.filter(row=>safeNum(row.hall.pos,99)>=15);
      const bestOrlik=[...rows].filter(row=>row.orlik_2025&&row.orlik_2025.ppg!=null).sort((a,b)=>safeNum(b.orlik_2025.ppg,0)-safeNum(a.orlik_2025.ppg,0))[0];
      const cards=[
        ['Rywali w stawce',rows.length,'przewidywana liczba przeciwników Bosch po wyjęciu dwóch ekip awansujących do I ligi'],
        ['Najwyższe zagrożenie',topThreat?teamLink(topThreat.team_id,topThreat.team_name):'-',topThreat?`${prettyNum(topThreat.hall.ppg)} PPG na hali | poziom ${topThreat.threat_level}`:'-'],
        ['Średnie PPG hali',prettyNum(avgHallPpg),'średni poziom punktowy prognozowanej stawki Orlika 2026'],
        ['Mecze obowiązkowe',mustWin,'rywale z końca hali, z którymi Bosch powinien celować w pełną pulę'],
        ['Najmocniejszy ślad z Orlika 2025',bestOrlik?teamLink(bestOrlik.team_id,bestOrlik.team_name):'-',bestOrlik?`${prettyNum(bestOrlik.orlik_2025.ppg)} PPG w ostatnim sezonie orlikowym`:'brak porównania'],
        ['Dolny alarm',bottomTwo.length?bottomTwo.map(row=>teamLink(row.team_id,row.team_name)).join(', '):'brak','dwa ostatnie zespoły hali trzeba potraktować serio, ale bez zostawiania im życia przez chaos']
      ];
      el.innerHTML=cards.map(([k,v,sb])=>`<div class="card"><div class="label">${esc(k)}</div><div class="value">${v}</div><div class="sub">${sb}</div></div>`).join('');
    }
    function renderOrlik2026Lists(){
      renderAnalysisList('orlik2026-assumptions',(ORLIK2026.bosch_scenario?.assumptions||[]).map((detail,index)=>({title:`Założenie ${index+1}`,detail:esc(detail)})));
      renderAnalysisList('orlik2026-tips',(ORLIK2026.bosch_scenario?.global_tips||[]).map((detail,index)=>({title:`Tip ${index+1}`,detail:esc(detail)})));
    }
    function renderOrlik2026Cards(){
      const el=document.getElementById('orlik2026-cards');
      if(!el) return;
      const rows=orlik2026RowsVisible();
      if(!rows.length){el.innerHTML='<div class="empty">Brak profili rywali dla aktywnego wyszukiwania.</div>';return}
      el.innerHTML=rows.map(row=>{
        const hallLine=`hala: ${row.hall.pos}. miejsce | ${row.hall.points} pkt | ${row.hall.gf}:${row.hall.ga} | ${prettyNum(row.hall.ppg)} PPG`;
        const orlikLine=row.orlik_2025?`orlik 2025: ${row.orlik_2025.pos}. miejsce | ${row.orlik_2025.points} pkt | ${prettyNum(row.orlik_2025.ppg)} PPG`:'brak wpisu w Orliku 2025';
        const boschOrlik=row.bosch_orlik_match;
        const extraTags=[
          `<span class="tag ${orlik2026ThreatClass(row.threat_level)}">${tip('Poziom zagrożenia','Poziom zagrożenia')}<span class="tag-value">${esc(row.threat_level)}</span></span>`,
          `<span class="tag blue"><span>Hala</span><span class="tag-value">${row.hall.pos}.</span></span>`,
          `<span class="tag teal"><span>Orlik 2025</span><span class="tag-value">${row.orlik_2025?`${row.orlik_2025.pos}.`:'-'}</span></span>`,
          row.hall.pos>=15?'<span class="tag orange"><span>Dolny alarm</span><span class="tag-value">must win bez chaosu</span></span>':'',
        ].filter(Boolean).join('');
        return `<article class="scout-card"><div class="scout-head"><div><div class="label">${teamLink(row.team_id,row.team_name)}</div><h3>${esc(row.team_name)}</h3><div class="scout-sub">${hallLine}<br>${orlikLine}</div></div><div class="tags">${extraTags}</div></div><div class="tags"><span class="tag blue"><span>Lider hali</span><span class="tag-value">${orlik2026LeaderLine(row,'hall')}</span></span><span class="tag teal"><span>Lider orlika</span><span class="tag-value">${orlik2026LeaderLine(row,'orlik')}</span></span><span class="tag orange"><span>Top3 goli hali</span><span class="tag-value">${prettyNum(row.top3_goal_share,1)}%</span></span></div><p>${row.scouting.summary}</p><p><strong>Ślad z Orlika 2025:</strong> ${orlik2026OrlikSummary(row)}</p><div class="scout-grid"><div class="scout-block"><h4>Mocne strony</h4><ul>${row.scouting.strengths.map(item=>`<li>${item}</li>`).join('')}</ul></div><div class="scout-block"><h4>Gdzie szukać okazji</h4><ul>${row.scouting.opportunities.length?row.scouting.opportunities.map(item=>`<li>${item}</li>`).join(''):'<li>szukać przewagi przez cierpliwe rozciąganie bloku i egzekwowanie jakości w szerokości</li>'}</ul></div><div class="scout-block"><h4>Plan Bosch</h4><ul>${row.scouting.bosch_plan.map(item=>`<li>${item}</li>`).join('')}</ul></div><div class="scout-block"><h4>Na kogo uważać</h4><ul>${row.scouting.watchouts.map(item=>`<li>${item}</li>`).join('')}</ul></div></div><div class="scout-grid"><div class="scout-block"><h4>Słabsze punkty rywala</h4><ul>${row.scouting.weaknesses.length?row.scouting.weaknesses.map(item=>`<li>${item}</li>`).join(''):'<li>brak wyraźnej dziury w danych publicznych</li>'}</ul></div><div class="scout-block"><h4>Liderzy hali 25/26</h4><ul>${orlik2026LeaderList(row,'hall')}</ul></div><div class="scout-block"><h4>Liderzy Orlika 2025</h4><ul>${orlik2026LeaderList(row,'orlik')}</ul></div><div class="scout-block"><h4>Bosch vs ten rywal</h4><ul><li>${cleanInline(orlik2026HallCell(row))}</li><li>${boschOrlik?cleanInline(orlik2026MatchCell(boschOrlik,'ostatni mecz orlika Bosch')):'brak wcześniejszego meczu Bosch z tym rywalem na orliku w widocznej bazie'}</li></ul></div></div></article>`;
      }).join('');
    }
    function renderPromotionSummary(){
      const el=document.getElementById('promotion-summary-cards');
      if(!el)return;
      const summary=promotionSummaryActive();
      if(!summary){el.innerHTML='<div class="empty">Brak danych dla aktywnego zakresu.</div>';return}
      const rows=[['Analizowane awanse',summary.teams,'liczba drużyn z aktywnego zakresu, które naprawdę wywalczyły awans'],['Średnie PPG',prettyNum(summary.avg_ppg),'średni poziom punktowy drużyn awansujących w sezonie awansowym'],['Średni zapas pkt nad 3.',prettyNum(summary.avg_gap_to_third),'średnia przewaga punktowa nad pierwszym miejscem nieawansującym'],['Średnio stracone / mecz',prettyNum(summary.avg_ga_pg),'średnia liczba goli straconych na mecz przez promowane drużyny'],['Pkt/mecz stykowy',prettyNum(summary.avg_close_ppg),'średnia liczba punktów zdobywanych w meczach stykowych, czyli w remisach i spotkaniach rozstrzygniętych jedną bramką'],['Top3 udział goli',`${prettyNum(summary.avg_top3_goal_share,1)}%`,'średni udział trzech najlepszych strzelców w całkowitej liczbie goli']];
      el.innerHTML=rows.map(([k,v,sb])=>`<div class="card"><div class="label">${esc(k)}</div><div class="value">${esc(v)}</div><div class="sub">${esc(sb)}</div></div>`).join('');
    }
    function renderPromotionCards(){
      const el=document.getElementById('promotion-cards');
      if(!el)return;
      const rows=promotionRowsVisible();
      if(!rows.length){el.innerHTML='<div class="empty">Brak profili awansu dla aktywnych filtrów.</div>';return}
      el.innerHTML=rows.map(row=>`<article class="reco-card"><div class="label">${seasonTableLink(row.sid,row.table_title,row.table_title)}</div><h3>${teamLink(row.team_id,row.team_name)}</h3><div class="sub">${row.rank}. miejsce | ${row.points} pkt | ${row.gf}:${row.ga} | PPG ${prettyNum(row.ppg)}</div><div class="tags"><span class="tag blue">${tip('Nad 3.','Nad 3.')}<span class="tag-value">+${row.gap_to_third}</span></span><span class="tag teal">${tip('Pkt/mecz stykowy','Pkt/mecz stykowy')}<span class="tag-value">${prettyNum(row.close_ppg)}</span></span><span class="tag orange"><span>Top3 goli</span><span class="tag-value">${prettyNum(row.top3_goal_share,1)}%</span></span></div><p><strong>Profil awansu:</strong> ${promotionProfileLine(row)}</p><p><strong>Liderzy:</strong> ${row.top_scorer?`${playerLinkFromRow(row.top_scorer)} ${row.top_scorer.goals} G`:'-'}; ${row.top_creator?`${playerLinkFromRow(row.top_creator)} ${row.top_creator.assists} A`:'-'}; ${row.top_points_player?`${playerLinkFromRow(row.top_points_player)} ${row.top_points_player.points} G+A`:'-'}. </p><p><strong>Ślad po awansie:</strong> ${promotionPostText(row)}</p></article>`).join('');
    }
    function activeAggregate(){
      const seasonRows=selectedSeasonRows();
      const ids=new Set(seasonRows.map(r=>r.sid_str));
      const stateRows=REPORT.state_rows.filter(r=>ids.has(String(r.sid)));
      const closeRows=REPORT.close_game_rows.filter(r=>ids.has(String(r.sid)));
      const continuityRows=REPORT.continuity_rows.filter(r=>ids.has(String(r.sid)));
      const concentrationRows=REPORT.concentration_rows.filter(r=>ids.has(String(r.sid)));
      const videoRows=VIDEO.season_rows.filter(r=>ids.has(String(r.sid)));
      const benchmarkRows=REPORT.benchmark.filter(r=>ids.has(String(r.season_id)));
      const team={matches:sumBy(seasonRows,r=>r.matches),points:sumBy(seasonRows,r=>r.points),wins:sumBy(seasonRows,r=>r.wins),draws:sumBy(seasonRows,r=>r.draws),losses:sumBy(seasonRows,r=>r.losses),gf:sumBy(seasonRows,r=>r.gf),ga:sumBy(seasonRows,r=>r.ga),clean_sheets:sumBy(seasonRows,r=>r.clean_sheets),failed_to_score:sumBy(seasonRows,r=>r.failed_to_score)};
      team.gd=team.gf-team.ga;
      team.ppg=team.matches?team.points/team.matches:0;
      team.gfpg=team.matches?team.gf/team.matches:0;
      team.gapg=team.matches?team.ga/team.matches:0;
      const firstFor=sumBy(stateRows,r=>r.first_for),firstAgainst=sumBy(stateRows,r=>r.first_against),leadScoringPoints=stateRows.reduce((acc,row)=>acc+safeNum(row.first_for,0)*safeNum(row.ppg_when_scoring_first,0),0),leadConcedingPoints=stateRows.reduce((acc,row)=>acc+safeNum(row.first_against,0)*safeNum(row.ppg_when_conceding_first,0),0);
      const stateAgg={matches:team.matches,first_for:firstFor,first_against:firstAgainst,first_goal_share:team.matches?(firstFor/team.matches)*100:0,ppg_when_scoring_first:firstFor?leadScoringPoints/firstFor:0,ppg_when_conceding_first:firstAgainst?leadConcedingPoints/firstAgainst:0,points_dropped_from_leads:sumBy(stateRows,r=>r.points_dropped_from_leads)};
      const closeMatches=sumBy(closeRows,r=>r.close_matches),closeWins=sumBy(closeRows,r=>r.close_wins),closeDraws=sumBy(closeRows,r=>r.close_draws),closeLosses=sumBy(closeRows,r=>r.close_losses);
      const closeAgg={close_matches:closeMatches,close_wins:closeWins,close_draws:closeDraws,close_losses:closeLosses,close_ppg:closeMatches?((closeWins*3)+(closeDraws))/closeMatches:0};
      const continuityWeight=sumBy(continuityRows,r=>r.roster);
      const continuityAgg={roster:sumBy(continuityRows,r=>r.roster),returning:sumBy(continuityRows,r=>r.returning),newcomers:sumBy(continuityRows,r=>r.newcomers),departures:sumBy(continuityRows,r=>r.departures),continuity:continuityWeight?continuityRows.reduce((acc,row)=>acc+safeNum(row.continuity,0)*safeNum(row.roster,0),0)/continuityWeight:null};
      const totalGoals=Math.max(1,team.gf),totalMatches=Math.max(1,team.matches),concentrationAgg={scorers:sumBy(concentrationRows,r=>r.scorers),roster:sumBy(concentrationRows,r=>r.roster),top1_goal_share:(seasonRows.reduce((acc,row)=>acc+safeNum(row.gf,0)*(safeNum(concentrationMap(rowSeason(row))?.top1_goal_share,0)/100),0)/totalGoals)*100,top3_goal_share:(seasonRows.reduce((acc,row)=>acc+safeNum(row.gf,0)*(safeNum(concentrationMap(rowSeason(row))?.top3_goal_share,0)/100),0)/totalGoals)*100,top5_point_share:(concentrationRows.reduce((acc,row)=>acc+safeNum(row.top5_point_share,0)*safeNum(stateMap.get(String(row.sid))?.matches??seasonMetaMap.get(String(row.sid))?.matches,0),0)/Math.max(1,concentrationRows.reduce((acc,row)=>acc+safeNum(stateMap.get(String(row.sid))?.matches??seasonMetaMap.get(String(row.sid))?.matches,0),0)))};
      const videoAgg={matches_total:sumBy(videoRows,r=>r.matches_total),matches_with_video:sumBy(videoRows,r=>r.matches_with_video),minutes:sumBy(videoRows,r=>r.minutes),full_matches:sumBy(videoRows,r=>r.full_matches)};
      videoAgg.coverage_pct=videoAgg.matches_total?(videoAgg.matches_with_video/videoAgg.matches_total)*100:0;
      const benchmarkAgg={bosch_points:sumBy(benchmarkRows,r=>r.bosch_points),bosch_matches:sumBy(benchmarkRows,r=>r.bosch_matches),second_points:sumBy(benchmarkRows,r=>r.second_points),second_matches:sumBy(benchmarkRows,r=>r.second_matches)};
      benchmarkAgg.bosch_ppg=benchmarkAgg.bosch_matches?benchmarkAgg.bosch_points/benchmarkAgg.bosch_matches:null;
      benchmarkAgg.second_ppg=benchmarkAgg.second_matches?benchmarkAgg.second_points/benchmarkAgg.second_matches:null;
      benchmarkAgg.gap_ppg=benchmarkAgg.bosch_ppg!=null&&benchmarkAgg.second_ppg!=null?benchmarkAgg.second_ppg-benchmarkAgg.bosch_ppg:null;
      return{seasonRows,team,state:stateAgg,close:closeAgg,continuity:continuityAgg,concentration:concentrationAgg,video:videoAgg,benchmark:benchmarkAgg};
    }
    function concentrationMap(sid){return concMap.get(String(sid))||{}}
    function surfaceRowsActive(){const groups=[['hala','Hala'],['orlik','Orlik']];return groups.map(([surface,label])=>{const rows=selectedSeasonRows().filter(r=>r.surface===surface);if(!rows.length)return null;const matches=sumBy(rows,r=>r.matches),points=sumBy(rows,r=>r.points),gf=sumBy(rows,r=>r.gf),ga=sumBy(rows,r=>r.ga);return{label,seasons:rows.length,matches,points,ppg:matches?Number((points/matches).toFixed(2)):0,gfpg:matches?Number((gf/matches).toFixed(2)):0,gapg:matches?Number((ga/matches).toFixed(2)):0}}).filter(Boolean)}
    function scorecardRowsActive(){const agg=activeAggregate();const targetMap=new Map(REPORT.scorecard_rows.map(row=>[row[0],safeNum(row[2],0)]));const dropPerMatch=agg.team.matches?agg.state.points_dropped_from_leads/agg.team.matches:0;return[['PPG',prettyNum(agg.team.ppg),prettyNum(agg.benchmark.second_ppg??targetMap.get('PPG')),statusFor(agg.team.ppg,agg.benchmark.second_ppg??targetMap.get('PPG'),'high'),'zbiorczy próg 2. miejsca dla aktywnego zakresu'],['Gole stracone / mecz',prettyNum(agg.team.gapg),prettyNum(targetMap.get('Gole stracone / mecz')),statusFor(agg.team.gapg,targetMap.get('Gole stracone / mecz'),'low'),'ile Bosch traci w zaznaczonych sezonach'],['PPG w meczach stykowych',prettyNum(agg.close.close_ppg),prettyNum(targetMap.get('PPG w meczach stykowych')),statusFor(agg.close.close_ppg,targetMap.get('PPG w meczach stykowych'),'high'),'czy Bosch dowozi wyrównane spotkania'],['Pierwszy gol Bosch (%)',prettyNum(agg.state.first_goal_share,1),prettyNum(targetMap.get('Pierwszy gol Bosch (%)'),1),statusFor(agg.state.first_goal_share,targetMap.get('Pierwszy gol Bosch (%)'),'high'),'kontrola wejścia w mecz'],['Ciągłość kadry (%)',prettyNum(agg.continuity.continuity,1),prettyNum(targetMap.get('Ciągłość kadry (%)'),1),statusFor(agg.continuity.continuity,targetMap.get('Ciągłość kadry (%)'),'high'),'stabilność rdzenia w wybranym zakresie'],['Wypuszczone pkt z prowadzeń / mecz',prettyNum(dropPerMatch,2),prettyNum(targetMap.get('Wypuszczone pkt z prowadzeń / mecz'),2),statusFor(dropPerMatch,targetMap.get('Wypuszczone pkt z prowadzeń / mecz'),'low'),'jak często Bosch oddaje przewagę']].map(([metric,current,target,status,note])=>({metric,current,target,status,note}))}
    function peakComparisonRowsActive(){const agg=activeAggregate(),peakSeason=seasonMetaMap.get(String(REPORT.peak_season_id)),peakClose=closeMap.get(String(REPORT.peak_season_id))||{},peakContinuity=contMap.get(String(REPORT.peak_season_id))||{},peakConcentration=concMap.get(String(REPORT.peak_season_id))||{};return[['PPG',prettyNum(agg.team.ppg),prettyNum(peakSeason?.ppg)],['Gole/mecz',prettyNum(agg.team.gfpg),prettyNum(peakSeason?.gf/Math.max(1,peakSeason?.matches??1))],['Stracone/mecz',prettyNum(agg.team.gapg),prettyNum(peakSeason?.ga/Math.max(1,peakSeason?.matches??1))],['PPG w meczach stykowych',prettyNum(agg.close.close_ppg),prettyNum(peakClose.close_ppg)],['Ciągłość kadry',`${prettyNum(agg.continuity.continuity,1)}%`,`${prettyNum(peakContinuity.continuity,1)}%`],['Top3 udział goli',`${prettyNum(agg.concentration.top3_goal_share,1)}%`,`${prettyNum(peakConcentration.top3_goal_share,1)}%`]]}
    function h2hRowsActive(){const groups=new Map();selectedMatchRows().forEach(row=>{const key=`${row.opponent_id||row.opponent}`;if(!groups.has(key))groups.set(key,{opponent_id:row.opponent_id||'',opponent:row.display_opponent||row.opponent,matches:0,wins:0,draws:0,losses:0,gf:0,ga:0,seasons:new Set()});const item=groups.get(key);item.matches+=1;item.gf+=safeNum(row.gf,0);item.ga+=safeNum(row.ga,0);item.seasons.add(row.season);if(row.gf>row.ga)item.wins+=1;else if(row.gf<row.ga)item.losses+=1;else item.draws+=1});return[...groups.values()].map(item=>({...item,gd:item.gf-item.ga,ppg:item.matches?(((item.wins*3)+item.draws)/item.matches):0,seasons_label:[...item.seasons].sort((a,b)=>a.localeCompare(b,'pl',{numeric:true,sensitivity:'base'})).join(', ')}))}
    function resultsRowsActive(direction='best'){return[...selectedMatchRows()].map(row=>({...row,score:`${row.gf}:${row.ga}`,margin:row.gf-row.ga})).sort((a,b)=>direction==='best'?b.margin-a.margin:a.margin-b.margin)}
    function table(target,cols,rowsFn,opts={}){
      const el=document.getElementById(target); if(!el) return;
      const sort=state.sort[target]||{key:opts.defaultSort||cols[0].key,dir:opts.defaultDir||'desc'}; state.sort[target]=sort;
      function render(){
        let rows=rowsFn(); if(opts.season!==false) rows=rows.filter(passSeason); if(opts.query!==false) rows=rows.filter(passQuery); if(opts.video!==false) rows=rows.filter(passVideo); if(opts.filter) rows=rows.filter(opts.filter);
        const col=cols.find(c=>c.key===sort.key)||cols[0];
        rows=[...rows].sort((a,b)=>{const av=col.sort?col.sort(a):a[sort.key], bv=col.sort?col.sort(b):b[sort.key], an=num(av), bn=num(bv); let r=0; if(an!==null&&bn!==null) r=an-bn; else r=String(av??'').localeCompare(String(bv??''),'pl',{numeric:true,sensitivity:'base'}); return sort.dir==='asc'?r:-r});
        if(!rows.length){el.innerHTML='<div class="empty">Brak wyników dla aktywnych filtrów.</div>'; return}
        const useScroller=Boolean(opts.scroller&&rows.length>(opts.scrollerRows??10));
        const head=cols.map(c=>`<th><button type="button" data-key="${c.key}">${c.labelHtml||(TERMS[c.label]?tip(c.label,c.label):esc(c.label))}<span class="sort">${sort.key===c.key?(sort.dir==='asc'?'↑':'↓'):'↕'}</span></button></th>`).join('');
        const body=rows.map(r=>`<tr>${cols.map(c=>`<td data-label="${esc(c.label)}">${c.render?c.render(r):(r[c.key]??'')}</td>`).join('')}</tr>`).join('');
        el.innerHTML=`<div class="table-wrap ${useScroller?'scroller':''}"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
        el.querySelectorAll('th button').forEach(btn=>btn.addEventListener('click',()=>{const key=btn.dataset.key;if(sort.key===key)sort.dir=sort.dir==='asc'?'desc':'asc';else{sort.key=key;sort.dir='desc'};render()}));
      }
      renderers.push(render); render();
    }
    function hero(){const total=REPORT.season_rows.reduce((a,r)=>a+r.matches,0),w=REPORT.season_rows.reduce((a,r)=>a+r.wins,0),d=REPORT.season_rows.reduce((a,r)=>a+r.draws,0),l=REPORT.season_rows.reduce((a,r)=>a+r.losses,0),videoPct=((VIDEO.matched_rows.length/Math.max(1,total))*100).toFixed(0);document.getElementById('hero-stats').innerHTML=[['Mecze ligowe',total],['Bilans',`${w}-${d}-${l}`],['Peak',REPORT.peak_season_name],['Bieżący sezon',REPORT.current_season_name],['Aktywny zakres',activeRangeLabel()],['Pokrycie wideo',`${videoPct}%`]].map(([k,v])=>`<div class="hero-card"><div class="hero-label">${esc(k)}</div><div class="hero-value">${esc(v)}</div></div>`).join('')}
    function summary(){const el=document.getElementById('summary-cards');const s=seasonRow();const agg=activeAggregate();let rows=[]; if(s){const st=stateMap.get(String(s.sid))||{},cl=closeMap.get(String(s.sid))||{},ct=contMap.get(String(s.sid))||{},cn=concMap.get(String(s.sid))||{},vd=videoMap.get(String(s.sid))||{};rows=[['Sezon',s.season,s.table_title],['Pozycja',s.pos,`${s.points} pkt`],['Bilans',`${s.wins}-${s.draws}-${s.losses}`,`${s.gf}:${s.ga}`],['PPG',s.ppg,'punkty na mecz'],['1. gol Bosch',`${st.first_goal_share??0}%`,`${st.first_for??0}/${st.matches??s.matches} meczów`],['Mecze stykowe',cl.close_ppg??'-',`${cl.close_matches??0} meczów`],['Ciągłość',ct.continuity!=null?`${ct.continuity}%`:'-',`${ct.roster??'-'} zawodników`],['Top3 goli',`${cn.top3_goal_share??0}%`,`${cn.scorers??0} strzelców`],['Wideo',`${vd.coverage_pct??0}%`,`${vd.matches_with_video??0}/${vd.matches_total??s.matches} meczów`]]} else {rows=[['Zakres',activeRangeLabel(),`${agg.seasonRows.length} sezonów w podsumowaniu zbiorczym`],['Bilans zbiorczy',`${agg.team.wins}-${agg.team.draws}-${agg.team.losses}`,`${agg.team.gf}:${agg.team.ga}`],['Punkty łącznie',agg.team.points,`${agg.team.matches} meczów`],['PPG zbiorcze',prettyNum(agg.team.ppg),`target: ${prettyNum(agg.benchmark.second_ppg??safeNum(REPORT.scorecard_rows[0][2],0))}`],['1. gol Bosch',`${prettyNum(agg.state.first_goal_share,1)}%`,`${agg.state.first_for}/${agg.team.matches} meczów`],['Mecze stykowe',prettyNum(agg.close.close_ppg),`${agg.close.close_matches} meczów`],['Ciągłość',agg.continuity.continuity!=null?`${prettyNum(agg.continuity.continuity,1)}%`:'-',`${agg.continuity.roster} wpisów kadrowych`],['Top3 goli',`${prettyNum(agg.concentration.top3_goal_share,1)}%`,`${agg.concentration.scorers} wpisów strzeleckich`],['Wideo',`${prettyNum(agg.video.coverage_pct,1)}%`,`${agg.video.matches_with_video}/${agg.video.matches_total} meczów`]]} el.innerHTML=rows.map(([k,v,sb])=>`<div class="card"><div class="label">${esc(k)}</div><div class="value">${esc(v)}</div><div class="sub">${esc(sb)}</div></div>`).join('')}
    function seasonCards(){const el=document.getElementById('season-cards');const activeIds=selectedSeasonIds();el.innerHTML=REPORT.season_rows.filter(passQuery).map(r=>{const st=stateMap.get(String(r.sid))||{},vd=videoMap.get(String(r.sid))||{};return `<article class="season-card ${activeIds.has(String(r.sid))?'active':''}" data-season="${r.sid}"><div class="label">${esc(r.table_title)}</div><div class="value">${esc(r.season)}</div><div class="sub">Pozycja ${r.pos} | ${r.points} pkt | ${r.gf}:${r.ga}</div><div class="tags"><span class="tag blue">PPG ${r.ppg}</span><span class="tag teal">1. gol ${st.first_goal_share??0}%</span><span class="tag orange">Wideo ${vd.coverage_pct??0}%</span></div></article>`}).join('')||'<div class="empty">Brak sezonów dla aktywnego wyszukiwania.</div>';el.querySelectorAll('.season-card').forEach(card=>card.addEventListener('click',()=>{toggleSetValue(state.seasons,String(card.dataset.season));sync();refresh();window.scrollTo({top:0,behavior:'smooth'})}))}
    function bars(id,rows,labelKey,valKey,color,suffix=''){const el=document.getElementById(id), data=rows.filter(passSeason).filter(passQuery); if(!data.length){el.innerHTML='<div class="empty">Brak danych.</div>';return} const mobile=mobileCharts(),w=560,h=mobile?280:240,left=18,right=18,bottom=mobile?102:70,top=14,gap=mobile?10:12,bw=(w-left-right-gap*(data.length-1))/data.length,max=Math.max(...data.map(r=>safeNum(r[valKey],0)),1); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${data.map((r,i)=>{const v=safeNum(r[valKey],0),bh=(v/max)*(h-top-bottom),x=left+i*(bw+gap),y=h-bottom-bh; return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${color}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="11" fill="#425466">${v}${suffix}</text>${svgLabel(x+bw/2,h-(mobile?46:44),r[labelKey],{maxChars:mobile?10:14,lineHeight:mobile?11:12,fontSize:mobile?10:11})}`}).join('')}</svg>`}
    function barList(id,rows,labelKey,valKey,color,opts={}){const el=document.getElementById(id),data=rows.filter(r=>opts.season===false||passSeason(r)).filter(r=>opts.query===false||passQuery(r));if(!el)return;if(!data.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const max=Math.max(...data.map(r=>safeNum(r[valKey],0)),1),decimals=opts.decimals??2,suffix=opts.suffix??'',subKey=opts.subLabelKey;el.innerHTML=`<div class="metric-bars">${data.map(r=>{const value=safeNum(r[valKey],0),width=Math.max(4,(value/max)*100),sub=subKey&&r[subKey]?`<span class="metric-bar-sub">${esc(r[subKey])}</span>`:'';return `<div class="metric-bar"><div class="metric-bar-label">${esc(r[labelKey])}${sub}</div><div class="metric-bar-main"><div class="metric-bar-track"><div class="metric-bar-fill" style="width:${width}%;background:${color}"></div></div><div class="metric-bar-value">${esc(`${prettyNum(value,decimals)}${suffix}`)}</div></div></div>`}).join('')}</div>`}
    function currentPlayers(){const el=document.getElementById('current-player-cards'); el.innerHTML=REPORT.current_players.filter(passQuery).slice(0,6).map(r=>`<article class="player-card"><div class="label">Bieżący sezon</div><div class="value">${playerLinkFromRow(r)}</div><div class="tags"><span class="tag blue">${r.apps} meczów</span><span class="tag teal">${r.points} G+A</span><span class="tag orange">${r.motm} MVP</span></div><div class="sub">Gole ${r.goals} | Asysty ${r.assists} | ŻK ${r.yellow} | CZK ${r.red}</div></article>`).join('')}
    function outcomeClass(forGoals,againstGoals){const gf=num(forGoals),ga=num(againstGoals);if(gf===null||ga===null)return'draw';return gf>ga?'win':gf<ga?'loss':'draw'}
    function scoreBadgeFor(forGoals,againstGoals,label){const gf=num(forGoals),ga=num(againstGoals);if(gf===null||ga===null)return esc(label??`${forGoals}:${againstGoals}`);return `<span class="status ${outcomeClass(gf,ga)}">${esc(label??`${gf}:${ga}`)}</span>`}
    function halftimeBadge(value){if(value==null||value==='')return'-';const match=String(value).match(/(-?\\d+)\\s*:\\s*(-?\\d+)/);if(!match)return esc(value);return scoreBadgeFor(match[1],match[2],`${match[1]}:${match[2]}`)}
    function halftimeScoreBadge(forGoals,againstGoals){if(forGoals==null||againstGoals==null)return'-';return scoreBadgeFor(forGoals,againstGoals,`${forGoals}:${againstGoals}`)}
    function stateBadge(label){const key=norm(label);const cls=key.includes('prowad')?'win':key.includes('strata')||key.includes('przegry')?'loss':'draw';return `<span class="status ${cls}">${esc(label)}</span>`}
    function rankTag(value){const n=num(value);if(n===null)return'-';const cls=n===1?'teal':n===2?'blue':'orange';return `<span class="tag ${cls}"><span class="tag-value">${esc(String(value))}</span></span>`}
    function resultBadge(r){const cls=r.gf>r.ga?'win':r.gf<r.ga?'loss':'draw';const text=r.gf>r.ga?'wygrana':r.gf<r.ga?'porażka':'remis';return `<span class="status ${cls}">${text}</span>`}
    function distribution(id,payload,color){const el=document.getElementById(id);if(!el)return;if(!payload||!payload.labels||!payload.labels.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),data=payload.labels.map((label,index)=>({label,value:payload.values[index]}));const w=560,h=mobile?286:250,left=18,right=18,bottom=mobile?108:74,top=16,gap=16,bw=(w-left-right-gap*(data.length-1))/data.length,max=Math.max(...data.map(r=>safeNum(r.value,0)),1),totals=payload.totals||{};el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${data.map((r,i)=>{const v=safeNum(r.value,0),bh=(v/max)*(h-top-bottom),x=left+i*(bw+gap),y=h-bottom-bh;return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${color}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="11" fill="#425466">${v}</text>${svgLabel(x+bw/2,h-(mobile?54:44),r.label,{maxChars:mobile?10:14,lineHeight:mobile?11:12,fontSize:mobile?10:11})}`}).join('')}<text x="${left}" y="${h-14}" font-size="10" fill="#5b6b7d">Gole: ${totals.goals??0} · Strzelcy: ${totals.unique_scorers??0} · Dublety: ${totals.braces??0} · Hat-tricki: ${totals.hat_tricks??0}</text></svg>`}
    function comparisonChart(){const el=document.getElementById('peak-chart');if(!el)return;const rows=peakComparisonRowsActive().filter(r=>num(r[1])!==null&&num(r[2])!==null).slice(0,6);if(!rows.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),w=560,h=mobile?326:270,left=24,right=18,bottom=mobile?132:82,top=16,gap=mobile?18:24,bw=28,group=(w-left-right-gap*(rows.length-1))/rows.length,max=Math.max(...rows.flatMap(r=>[safeNum(r[1],0),safeNum(r[2],0)]),1);el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${rows.map((r,i)=>{const cur=safeNum(r[1],0),peak=safeNum(r[2],0),base=left+i*(group+gap),h1=(cur/max)*(h-top-bottom),h2=(peak/max)*(h-top-bottom);return `<rect x="${base}" y="${h-bottom-h1}" width="${bw}" height="${h1}" rx="8" fill="#ea580c"></rect><rect x="${base+bw+6}" y="${h-bottom-h2}" width="${bw}" height="${h2}" rx="8" fill="#1d4ed8"></rect><text x="${base+bw/2}" y="${h-bottom-h1-6}" text-anchor="middle" font-size="10" fill="#425466">${cur}</text><text x="${base+bw+6+bw/2}" y="${h-bottom-h2-6}" text-anchor="middle" font-size="10" fill="#425466">${peak}</text>${svgLabel(base+bw,h-(mobile?72:46),r[0],{maxChars:mobile?12:16,lineHeight:mobile?11:12,fontSize:mobile?10:10})}`}).join('')}<text x="${left}" y="${h-16}" font-size="10" fill="#5b6b7d">pomarańczowy: aktywny zakres · niebieski: peak</text></svg>`}
    function surfaceChart(){const el=document.getElementById('surface-chart');if(!el)return;const rows=surfaceRowsActive();if(!rows.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),w=560,h=mobile?286:250,left=24,right=18,bottom=mobile?98:70,top=16,gap=48,bw=26,max=Math.max(...rows.flatMap(r=>[safeNum(r.ppg,0),safeNum(r.gfpg,0),safeNum(r.gapg,0)]),1);el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${rows.map((r,i)=>{const base=left+i*(bw*3+gap),vals=[[safeNum(r.ppg,0),'#1d4ed8','PPG'],[safeNum(r.gfpg,0),'#0f766e','GF/m'],[safeNum(r.gapg,0),'#ea580c','GA/m']];return vals.map((v,j)=>{const bh=(v[0]/max)*(h-top-bottom),x=base+j*(bw+8),y=h-bottom-bh;return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${v[1]}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="10" fill="#425466">${v[0]}</text>${svgLabel(x+bw/2,h-(mobile?56:42),v[2],{maxChars:mobile?8:10,lineHeight:mobile?11:10,fontSize:mobile?9:9})}`}).join('')+`${svgLabel(base+bw+16,h-(mobile?20:18),r.label,{maxChars:mobile?10:12,lineHeight:11,fontSize:10,fill:'#425466'})}`}).join('')}</svg>`}
    function recommendationRows(){const currentBenchmark=benchmarkMap.get(String(REPORT.current_season_id));const currentState=stateMap.get(String(REPORT.current_season_id))||REPORT.current_state||{};const currentClose=closeMap.get(String(REPORT.current_season_id))||{};const currentConcentration=concMap.get(String(REPORT.current_season_id))||{};const currentTier=REPORT.tier_split_current||[];const topHalf=currentTier.find(r=>norm(r.label).includes('top'));const bottomHalf=currentTier.find(r=>norm(r.label).includes('bottom'));const currentPlayer=REPORT.current_players[0];const gapPpg=currentBenchmark?((currentBenchmark.second_points/Math.max(1,currentBenchmark.second_matches))-(currentBenchmark.bosch_points/Math.max(1,currentBenchmark.bosch_matches))).toFixed(2):null;return[{priority:'Priorytet 1',title:'Domknąć prowadzenia i końcówki',impact:'najszybszy wzrost punktów bez rewolucji kadrowej',detail:`Bosch oddał już ${currentState.points_dropped_from_leads??0} ${tip('wypuszczone pkt','Wypuszczone pkt')}, a w ${currentClose.close_matches??0} ${tip('meczach stykowych','Mecze stykowe')} robi ${currentClose.close_ppg??'-'} ${tip('PPG','PPG')}.`,target:'zmniejszyć liczbę oddanych punktów po prowadzeniu i podnieść PPG w meczach stykowych do poziomu zespołu z top2'},{priority:'Priorytet 2',title:'Podnieść jakość przeciw mocnym rywalom',impact:'bez tego Bosch zostanie solidnym środkiem II ligi',detail:topHalf&&bottomHalf?`W ${tip('splicie konkurencyjności','Split konkurencyjności')} Bosch punktuje wyraźnie lepiej z bottom half (${bottomHalf.ppg} PPG) niż z top half (${topHalf.ppg} PPG).`:'Największy zapas jakości nadal leży w meczach z górą tabeli.',target:'zbliżyć PPG z top half do poziomu pozwalającego regularnie bić się o podium'},{priority:'Priorytet 3',title:'Uszczelnić fazę bez piłki',impact:'awans zwykle buduje się obroną, nie samym wolumenem goli',detail:currentBenchmark?`Do progu awansu brakuje dziś około ${gapPpg} ${tip('PPG','PPG')} na mecz, a najprostsza droga do odzyskania tego dystansu prowadzi przez niższą liczbę bramek traconych.`:'W bieżącej próbce nadal łatwiej poprawić obronę niż wyciągnąć jeszcze wyższy sufit ofensywny.',target:'zejść z liczbą bramek traconych i częściej utrzymywać kontrolę po objęciu prowadzenia'},{priority:'Priorytet 4',title:'Zachować szerokość ataku, ale odciążyć lidera',impact:'lepsza odporność kadry na słabszy dzień jednego zawodnika',detail:currentPlayer?`${currentPlayer.name} jest dziś liderem produkcji, ale obecnie top3 odpowiada za ${currentConcentration.top3_goal_share??0}% goli Bosch.`:`Potrzebne jest utrzymanie wieloźródłowej ofensywy, bo peak Bosch nigdy nie opierał się na jednym nazwisku.`,target:'utrzymać szeroką produkcję i dołożyć stabilne drugie-trzecie źródło liczb'},{priority:'Priorytet 5',title:'Rozbudować świeżą bibliotekę wideo',impact:'bez tego trudniej o pracę korekcyjną i monitoring postępu',detail:`Publiczne pokrycie bieżącego sezonu wynosi ${videoMap.get(String(REPORT.current_season_id))?.coverage_pct??0}%.`,target:'budować własne archiwum bieżących meczów, żeby liczby od razu podpinać pod konkretne klipy'}]}
    function renderRecommendations(){const el=document.getElementById('recommendation-cards');if(!el)return;const rows=recommendationRows().filter(passQuery);el.innerHTML=rows.map(r=>`<article class="reco-card"><div class="label">${esc(r.priority)}</div><h3>${esc(r.title)}</h3><div class="tags"><span class="tag blue">${esc(r.impact)}</span></div><p>${r.detail}</p><p><strong>Cel:</strong> ${esc(r.target)}</p></article>`).join('')||'<div class="empty">Brak rekomendacji dla aktywnego wyszukiwania.</div>'}
    function renderNotes(){
      const agg=activeAggregate();
      const peakPlayer=REPORT.overall_points[0];
      const currentPlayer=REPORT.current_players[0];
      const h2h=h2hRowsActive().filter(r=>r.matches>=2);
      const bestH2H=[...h2h].sort((a,b)=>b.ppg-a.ppg)[0];
      const worstH2H=[...h2h].sort((a,b)=>a.ppg-b.ppg)[0];
      const promo=promotionSummaryActive();
      const promoRows=promotionRowsVisible();
      const promoDefenseTop2=promoRows.filter(r=>safeNum(r.defense_rank,99)<=2).length;
      const promoAttackTop2=promoRows.filter(r=>safeNum(r.attack_rank,99)<=2).length;
      const promoTightMargins=promoRows.filter(r=>safeNum(r.gap_to_third,0)<=2).length;
      const promoSafeMargins=promoRows.filter(r=>safeNum(r.gap_to_third,0)>=4).length;
      const promoBestPpg=[...promoRows].sort((a,b)=>safeNum(b.ppg,0)-safeNum(a.ppg,0))[0];
      const futureRows=orlik2026RowsVisible();
      const futureHigh=futureRows.filter(row=>row.threat_level==='wysokie');
      const futureMustWin=futureRows.filter(row=>safeNum(row.hall.pos,99)>=12);
      const futureRise=orlik2026ShiftRows().filter(row=>row.shift>0.15).sort((a,b)=>b.shift-a.shift).slice(0,3);
      const futureBestOrlik=[...futureRows].filter(row=>row.orlik_2025&&row.orlik_2025.ppg!=null).sort((a,b)=>safeNum(b.orlik_2025.ppg,0)-safeNum(a.orlik_2025.ppg,0))[0];
      const note=lines=>`<strong>Wniosek Rozdziału</strong>${lines.map(line=>`<p>${line}</p>`).join('')}`;
      const set=(id,html)=>{const el=document.getElementById(id);if(el)el.innerHTML=html};
      set('overview-note',note([`Aktywny zakres obejmuje ${agg.team.matches} meczów ligowych Bosch w układzie: ${activeRangeLabel()}.`,`W tym zakresie po własnym otwarciu Bosch robi ${prettyNum(agg.state.ppg_when_scoring_first)} ${tip('PPG','PPG')}, a po stracie pierwszej bramki ${prettyNum(agg.state.ppg_when_conceding_first)}.`]));
      set('seasons-note',note([`Zakres ${activeRangeLabel()} daje zbiorcze ${prettyNum(agg.team.ppg)} ${tip('PPG','PPG')}.`,agg.benchmark.second_ppg!=null?`Do progu awansu dla tych sezonów brakuje około ${prettyNum(agg.benchmark.gap_ppg)} ${tip('PPG','PPG')} na mecz.`:`Dla części zaznaczonych sezonów nie ma pełnego benchmarku 2. miejsca, więc próg awansu jest tylko częściowo porównywalny.`]));
      set('splits-note',note([`W wybranym zakresie można porówniać hale z orlikiem albo sklejać pełne lata, np. rok 2025 jako Hala 2024/2025 plus Orlik 2025.`,`To właśnie tutaj najlepiej widać, czy Bosch jest mocniejszy na konkretnej powierzchni i jak bardzo zmienia profil gry między przekrojami.`]));
      set('control-note',note([`W aktywnym zakresie Bosch oddał ${agg.state.points_dropped_from_leads} ${tip('wypuszczone pkt','Wypuszczone pkt')} po objęciu prowadzenia.`,`W ${agg.close.close_matches} ${tip('meczach stykowych','Mecze stykowe')} Bosch zdobywa średnio ${prettyNum(agg.close.close_ppg)} ${tip('Pkt/mecz stykowy','Pkt/mecz stykowy')}, więc końcówki nadal pozostają jednym z głównych obszarów poprawy.`]));
      set('players-note',note([currentPlayer&&peakPlayer?`${currentPlayer.name} pozostaje dziś najproduktywniejszy w bieżącej kadrze, a historycznie najwyższy pułap liczb daje ${peakPlayer.name}.`:`Sekcja zawodników pokazuje pełne tło indywidualne Bosch.`,`W warstwie zbiorczej aktywny zakres daje ${prettyNum(agg.concentration.top3_goal_share,1)}% udziału top3 strzelców, więc łatwo porównać, czy atak jest szeroki czy skupiony.`]));
      set('matches-note',note([`Tabela meczowa działa teraz także jako filtr zakresów: możesz łączyć kilka sezonów i od razu zobaczyć wspólną próbkę spotkań.`,`To najlepsze miejsce do sprawdzania całych bloków typu same hale, same orliki albo pełny rok rozgrywkowy.`]));
      set('opponents-note',note([bestH2H?`W aktywnym zakresie najlepiej punktowany regularny rywal to ${teamLink(bestH2H.opponent_id,bestH2H.opponent)} (${prettyNum(bestH2H.ppg)} ${tip('PPG','PPG')}).`:'W aktywnym zakresie próba H2H jest zbyt mała, by pewnie wskazać najwygodniejszego rywala.',worstH2H?`Najtrudniej punktować przeciw ${teamLink(worstH2H.opponent_id,worstH2H.opponent)} (${prettyNum(worstH2H.ppg)} ${tip('PPG','PPG')}).`:'W aktywnym zakresie próba H2H jest zbyt mała, by pewnie wskazać najtrudniejszego rywala.']));
      set('promotions-note',note([
        promo?`W aktywnym zakresie jest ${promo.teams} realnych awansów do I ligi. Średni profil takiej drużyny to ${prettyNum(promo.avg_ppg)} ${tip('PPG','PPG')}, ${prettyNum(promo.avg_gap_to_third)} pkt przewagi nad 3. miejscem i ${prettyNum(promo.avg_ga_pg)} straconego gola na mecz.`:'Dla aktywnego zakresu nie ma obecnie danych o promowanych drużynach.',
        `Tabela "Ścieżka ligowa ekip, które awansowały" nie opisuje Bosch. Każdy wiersz pokazuje jedną historyczną tabelę dla konkretnej promowanej drużyny, a kolumna "Poz. w tej tabeli" oznacza miejsce właśnie tej ekipy w tamtym sezonie lub lidze.`,
        promo?`${promoTightMargins} z ${promoRows.length} awansów zostało dowiezionych z zapasem najwyżej 2 pkt nad 3. miejscem, a tylko ${promoSafeMargins} miały bufor co najmniej 4 pkt. To ważny wniosek: sam awans nie zawsze wymaga dominacji tabeli, ale zwykle wymaga stabilnego domykania wyścigu z drużyną z 3. miejsca.`:'',
        promo?`${promoDefenseTop2} z ${promoRows.length} promowanych ekip miało obronę w top2 swojej ligi, a ${promoAttackTop2} z ${promoRows.length} atak w top2. Wzorzec awansu częściej budował więc balans albo szczelność, a nie sam wysoki wolumen goli.`:'',
        promo?`Ofensywnie promowane drużyny też rzadko były skrajnie jednowymiarowe: top3 strzelców dawało średnio ${prettyNum(promo.avg_top3_goal_share,1)}% wszystkich goli. To bliżej modelu szerokiej produkcji niż wejścia opartego wyłącznie na jednym liderze.`:'',
        promo?`Na tle tego benchmarku Bosch w aktywnym zakresie jest ${agg.team.ppg>=promo.avg_ppg?`o ${prettyNum(agg.team.ppg-promo.avg_ppg)} ${tip('PPG','PPG')} powyżej`: `o ${prettyNum(promo.avg_ppg-agg.team.ppg)} ${tip('PPG','PPG')} poniżej`} średniej awansu, ${agg.team.gapg<=promo.avg_ga_pg?`traci o ${prettyNum(promo.avg_ga_pg-agg.team.gapg)} gola mniej na mecz`: `traci o ${prettyNum(agg.team.gapg-promo.avg_ga_pg)} gola więcej na mecz`} i ${agg.close.close_ppg>=promo.avg_close_ppg?`zdobywa średnio o ${prettyNum(agg.close.close_ppg-promo.avg_close_ppg)} ${tip('Pkt/mecz stykowy','Pkt/mecz stykowy')} więcej`: `zdobywa średnio o ${prettyNum(promo.avg_close_ppg-agg.close.close_ppg)} ${tip('Pkt/mecz stykowy','Pkt/mecz stykowy')} mniej`} w meczach stykowych.`:'',
        promoBestPpg?`Najwyższy punktowy sufit w tej próbce dał ${teamLink(promoBestPpg.team_id,promoBestPpg.team_name)} (${seasonTableLink(promoBestPpg.sid,promoBestPpg.season,promoBestPpg.table_title)}) z ${prettyNum(promoBestPpg.ppg)} ${tip('PPG','PPG')}, ale równie ważne jest to, że nawet słabsze awanse zwykle miały czytelny punkt odniesienia: nie można tracić zbyt dużo i trzeba utrzymywać kontakt z top2 przez cały sezon.`:''
      ].filter(Boolean)));
      set('orlik2026-note',note([
        `Prognoza Orlika 2026 zostawia Bosch z ${futureRows.length} rywalami po wyjęciu ${ORLIK2026.excluded_promoted.map(row=>teamLink(row.team_id,row.name)).join(' i ')}. To daje szeroką stawkę, ale z czytelnym podziałem na mecze obowiązkowe, pułapki środka i kilka spotkań naprawdę topowych.`,
        futureHigh.length?`Najmocniejszy blok tworzą dziś ${futureHigh.map(row=>teamLink(row.team_id,row.team_name)).join(', ')}. To rywale, przeciw którym Bosch nie powinien iść w otwarty mecz bez asekuracji, tylko kontrolować tempo, pilnować rest defense i lepiej zarządzać stratą po własnym ataku.`:'W danych nie ma dziś szerokiego bloku rywali z najwyższym poziomem zagrożenia.',
        futureRise.length?`Największe ryzyko letniego niedoszacowania mają ${futureRise.map(row=>`${teamLink(row.team_id,row.team_name)} (${row.shift_note})`).join(', ')}, bo ostatni ślad z Orlika 2025 był u nich lepszy niż obecna hala. To ważne: sama tabela hali nie mówi jeszcze całej prawdy o tym, jak ci rywale mogą wyglądać na większej przestrzeni.`:'Ślad z Orlika 2025 nie pokazuje dziś dużej grupy rywali, którzy wyraźnie rosną po wyjściu na otwarte boisko.',
        futureMustWin.length?`Blok meczów obowiązkowych tworzą przede wszystkim ${futureMustWin.map(row=>teamLink(row.team_id,row.team_name)).join(', ')}. Tu Bosch powinien iść po pełną pulę, ale pod warunkiem szybkiego objęcia kontroli: nie przedłużać remisów, nie dawać przeciwnikowi rosnąć w chaosie i zamykać wynik szybciej niż na hali.`:'Nie widać tu dużego bloku rywali z końca stawki, których można potraktować jako łatwe mecze.',
        `Przy założeniu powrotu Mateusza Jurkowicza po wakacjach i wejścia trzech nowych jakościowych zawodników Bosch powinien być lepiej przygotowany do dwóch trybów gry: wysokiego, agresywnego pressingu na dół tabeli oraz bardziej cierpliwego, kontrolnego meczu na zespoły z topu. Największy zysk nie musi wcale przyjść z samego wzrostu jakości piłkarskiej, tylko z lepszego dopasowania planu do klasy rywala.`,
        futureBestOrlik?`Jeśli Bosch ma realnie myśleć o mocnym Orliku 2026, punkt odniesienia jest prosty: trzeba wejść co najmniej na poziom rywali takich jak ${teamLink(futureBestOrlik.team_id,futureBestOrlik.team_name)}, którzy już na ostatnim orliku dawali ${prettyNum(futureBestOrlik.orlik_2025.ppg)} ${tip('PPG','PPG')}. To nie oznacza, że każdy mecz ma wyglądać widowiskowo; ważniejsze jest to, by dolny blok brać seryjnie, a z górnym regularnie zbierać punkty zamiast pojedynczych zrywów.`:''
      ].filter(Boolean)));
      set('video-note',note([`Dla zakresu ${activeRangeLabel()} pokrycie wideo wynosi ${prettyNum(agg.video.coverage_pct,1)}% i obejmuje ${agg.video.matches_with_video} z ${agg.video.matches_total} meczów.`,`To pozwala porównywać nie tylko jeden sezon, ale też całe pakiety typu same hale albo pełny rok.`]));
      set('recommendations-note',note([`Rekomendacje na dole nadal są planem działania pod awans, ale filtry pozwalają teraz sprawdzić, które problemy wracają w różnych blokach sezonów.`,`Dzięki temu można oddzielić problem strukturalny od jednorazowego gorszego sezonu.`]));
    }
    function statusHtml(status){return norm(status).includes('obecny')?'<span class="status obecny">obecny</span>':'<span class="status arch">archiwalny</span>'}
    function register(){
      table('legend-table',[{key:'short',label:'Skrót',render:r=>tip(r.short,r.short)},{key:'meaning',label:'Znaczenie'}],()=>LEGEND.map(([short,meaning])=>({short,meaning})),{season:false,defaultSort:'short',defaultDir:'asc'});
      table('concept-table',[{key:'term',label:'Pojęcie',render:r=>tip(r.term,r.term)},{key:'definition',label:'Co to znaczy'},{key:'why',label:'Jak to czytać'}],()=>CONCEPTS.map(([term,definition,why])=>({term,definition,why})),{season:false,video:false,defaultSort:'term',defaultDir:'asc'});
      table('hidden-table',[{key:'player_id',label:'ID'},{key:'name',label:'Zawodnik',render:r=>`<div class="identity-badges">${playerLinkFromRow(r)}<span class="tag gold">profil niepubliczny</span></div>`},{key:'event_date',label:'Mecz źródłowy',render:r=>formatDate(r.event_date),sort:r=>r.event_date},{key:'event_title',label:'Spotkanie'},{key:'event_link',label:'Link',render:r=>`<a href="${r.event_link}" target="_blank" rel="noreferrer">wydarzenie</a>`}],()=>REPORT.resolved_hidden_players,{season:false,video:false,defaultSort:'event_date',defaultDir:'desc',scroller:true});
      table('season-table',[{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,r.table_title)},{key:'pos',label:'Poz.',render:r=>rankTag(r.pos)},{key:'points',label:'Pkt'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'gd',label:'RB'},{key:'ppg',label:'PPG'}],()=>REPORT.season_rows,{season:false,defaultSort:'sid',defaultDir:'asc'});
      table('scorecard-table',[{key:'metric',label:'KPI'},{key:'current',label:'Bosch teraz'},{key:'target',label:'Target'},{key:'status',label:'Status',render:r=>`<span class="tag ${r.status==='mocne'?'teal':r.status==='blisko'?'orange':'red'}">${esc(r.status)}</span>`},{key:'note',label:'Komentarz'}],()=>scorecardRowsActive(),{season:false,defaultSort:'current'});
      table('peak-table',[{key:'metric',label:'Metryka'},{key:'current',label:'Aktywny zakres'},{key:'peak',label:'Peak sezon'},{key:'gap',label:'Luka'}],()=>peakComparisonRowsActive().map(([metric,current,peak])=>({metric,current,peak,gap:num(current)!==null&&num(peak)!==null?(num(peak)-num(current)).toFixed(2):`${current} → ${peak}`})),{season:false,video:false,defaultSort:'metric',defaultDir:'asc'});
      table('state-table',[{key:'season',label:'Sezon'},{key:'matches',label:'M'},{key:'first_for',label:'1. gol Bosch'},{key:'first_against',label:'1. gol rywal'},{key:'first_goal_share',label:'1. gol %'},{key:'ppg_when_scoring_first',label:'PPG po 1:0'},{key:'ppg_when_conceding_first',label:'PPG po 0:1'},{key:'points_dropped_from_leads',label:'Wypuszczone pkt'}],()=>REPORT.state_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('close-table',[{key:'season',label:'Sezon'},{key:'close_matches',label:'Mecze stykowe',labelHtml:tip('Mecze stykowe','Mecze stykowe')},{key:'close_wins',label:'W'},{key:'close_draws',label:'R'},{key:'close_losses',label:'P'},{key:'close_ppg',label:'PPG'},{key:'scored_4plus',label:'4+ strzelone'},{key:'conceded_3plus',label:'3+ stracone'}],()=>REPORT.close_game_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('continuity-table',[{key:'season',label:'Sezon'},{key:'roster',label:'Kadra'},{key:'returning',label:'Powracający'},{key:'newcomers',label:'Nowi'},{key:'departures',label:'Ubytki'},{key:'continuity',label:'Ciągłość',labelHtml:tip('Ciągłość','Ciągłość'),render:r=>r.continuity==null?'-':`${r.continuity}%`}],()=>REPORT.continuity_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('concentration-table',[{key:'season',label:'Sezon'},{key:'scorers',label:'Strzelcy'},{key:'roster',label:'Kadra'},{key:'top1_goal_share',label:'Top1 goli',render:r=>`${r.top1_goal_share}%`},{key:'top3_goal_share',label:'Top3 goli',render:r=>`${r.top3_goal_share}%`},{key:'top5_point_share',label:'Top5 G+A',render:r=>`${r.top5_point_share}%`}],()=>REPORT.concentration_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('surface-table',[{key:'label',label:'Powierzchnia'},{key:'seasons',label:'Sezony'},{key:'matches',label:'M'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>surfaceRowsActive(),{season:false,video:false,defaultSort:'ppg'});
      table('slot-all-table',[{key:'label',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.slot_split_all,{season:false,video:false,defaultSort:'label',defaultDir:'asc'});
      table('slot-current-table',[{key:'label',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.slot_split_current,{season:false,video:false,defaultSort:'label',defaultDir:'asc'});
      table('halftime-all-table',[{key:'state',label:'Stan',render:r=>stateBadge(r.state)},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.halftime_all,{season:false,video:false,defaultSort:'ppg'});
      table('halftime-current-table',[{key:'state',label:'Stan',render:r=>stateBadge(r.state)},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.halftime_current,{season:false,video:false,defaultSort:'ppg'});
      table('tier-current-table',[{key:'label',label:'Grupa'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.tier_split_current,{season:false,video:false,defaultSort:'ppg'});
      table('tier-peak-table',[{key:'label',label:'Grupa'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.tier_split_peak,{season:false,video:false,defaultSort:'ppg'});
      table('peak-compare-table',[{key:'metric',label:'Metryka'},{key:'current',label:'Zakres'},{key:'peak',label:'Peak'},{key:'reading',label:'Interpretacja'}],()=>peakComparisonRowsActive().map(([metric,current,peak])=>({metric,current,peak,reading:num(current)!==null&&num(peak)!==null?(num(peak)-num(current)>0?`Dołożenia: ${(num(peak)-num(current)).toFixed(2)}`:'poziom utrzymany'):'miara jakościowa'})),{season:false,video:false,defaultSort:'metric',defaultDir:'asc'});
      table('apps-table',[{key:'name',label:'Zawodnik',render:r=>playerLinkFromRow(r)},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'motm',label:'MVP'}],()=>REPORT.overall_apps,{season:false,defaultSort:'apps'});
      table('points-table',[{key:'name',label:'Zawodnik',render:r=>playerLinkFromRow(r)},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'motm',label:'MVP'}],()=>REPORT.overall_points,{season:false,defaultSort:'points'});
      table('player-cards-table',[{key:'name',label:'Zawodnik',render:r=>playerLinkFromRow(r)},{key:'status',label:'Status',render:r=>statusHtml(r.status)},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'points_per_match',label:'G+A/M'},{key:'peak',label:'Peak'}],()=>REPORT.player_cards,{season:false,defaultSort:'points',filter:r=>state.status==='all'||norm(r.status).includes(norm(state.status))});
      table('partnership-table',[{key:'pair',label:'Duet',render:r=>playerPairLinks(r.pair)},{key:'matches',label:'M'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.partnership_rows,{season:false,video:false,defaultSort:'ppg',scroller:true});
      table('h2h-table',[{key:'opponent',label:'Rywal',render:r=>teamLink(r.opponent_id,r.opponent)},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'gd',label:'RB'},{key:'ppg',label:'PPG',render:r=>prettyNum(r.ppg,2)},{key:'seasons_label',label:'Sezony'}],()=>h2hRowsActive(),{season:false,defaultSort:'matches'});
      table('best-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,seasonMetaMap.get(String(r.sid))?.table_title||r.season)},{key:'match',label:'Mecz',render:r=>matchLink(r)},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'margin',label:'RB'}],()=>resultsRowsActive('best'),{season:false,defaultSort:'margin'});
      table('worst-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,seasonMetaMap.get(String(r.sid))?.table_title||r.season)},{key:'match',label:'Mecz',render:r=>matchLink(r)},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'margin',label:'RB'}],()=>resultsRowsActive('worst'),{season:false,defaultSort:'margin',defaultDir:'asc'});
      table('benchmark-table',[{key:'season_name',label:'Sezon',render:r=>seasonTableLink(r.season_id,r.season_name,seasonMetaMap.get(String(r.season_id))?.table_title||r.season_name)},{key:'bosch_ppg',label:'Bosch PPG',render:r=>(r.bosch_points/Math.max(1,r.bosch_matches)).toFixed(2),sort:r=>r.bosch_points/Math.max(1,r.bosch_matches)},{key:'second_ppg',label:'2. miejsce PPG',render:r=>(r.second_points/Math.max(1,r.second_matches)).toFixed(2),sort:r=>r.second_points/Math.max(1,r.second_matches)},{key:'gap',label:'Luka pkt',render:r=>r.second_points-r.bosch_points,sort:r=>r.second_points-r.bosch_points},{key:'second_name',label:'Drużyna progowa',render:r=>teamLinkByName(r.second_name)}],()=>REPORT.benchmark,{defaultSort:'season_id',defaultDir:'asc'});
      table('promotion-benchmark-table',[{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,r.table_title)},{key:'team_name',label:'Drużyna',render:r=>teamLink(r.team_id,r.team_name)},{key:'rank',label:'Miejsce awansu',labelHtml:tip('Miejsce awansu','Miejsce awansu'),render:r=>rankTag(r.rank)},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG',render:r=>prettyNum(r.ppg)},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'gap_to_third',label:'Nad 3.',labelHtml:tip('Nad 3.','Nad 3.')},{key:'attack_rank',label:'Atak rank',labelHtml:tip('Atak rank','Atak rank'),render:r=>rankTag(r.attack_rank)},{key:'defense_rank',label:'Obrona rank',labelHtml:tip('Obrona rank','Obrona rank'),render:r=>rankTag(r.defense_rank)},{key:'close_ppg',label:'Pkt/mecz stykowy',labelHtml:tip('Pkt/mecz stykowy','Pkt/mecz stykowy'),render:r=>prettyNum(r.close_ppg)},{key:'first_post',label:'Ślad po awansie',labelHtml:tip('Ślad po awansie','Ślad po awansie'),render:r=>promotionPostText(r)}],()=>promotionRowsActive(),{defaultSort:'sid',defaultDir:'asc',scroller:true});
      table('promotion-player-table',[{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,(PROMO.promotions.find(x=>x.sid===r.sid&&x.team_id===r.team_id)?.table_title)||r.season)},{key:'team_name',label:'Drużyna',render:r=>teamLink(r.team_id,r.team_name)},{key:'name',label:'Zawodnik',render:r=>playerLinkFromRow(r)},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'points_per_match',label:'G+A/M',render:r=>prettyNum(r.points_per_match)},{key:'motm',label:'MVP'}],()=>promotionPlayerRowsActive(),{defaultSort:'points',scroller:true});
      table('promotion-history-table',[{key:'promotion_team',label:'Drużyna awansująca',render:r=>teamLink(r.team_id,r.promotion_team)},{key:'promotion_season',label:'Sezon awansu',render:r=>seasonTableLink(r.sid,r.promotion_season,(PROMO.promotions.find(x=>x.sid===r.sid&&x.team_id===r.team_id)?.table_title)||r.promotion_season)},{key:'table_title',label:'Tabela historyczna',render:r=>tableLinkById(r.table_id,r.table_title)},{key:'pos',label:'Poz. w tej tabeli',labelHtml:tip('Poz. w tej tabeli','Poz. w tej tabeli'),render:r=>rankTag(r.pos)},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG',render:r=>prettyNum(r.ppg)},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'post_flag',label:'Ślad po awansie',labelHtml:tip('Ślad po awansie','Ślad po awansie'),render:r=>r.post_flag?'<span class="tag teal">pierwszy ślad</span>':'-'}],()=>promotionHistoryRowsActive(),{season:false,defaultSort:'season_id',defaultDir:'asc',scroller:true});
      table('promotion-match-table',[{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,(PROMO.promotions.find(x=>x.sid===r.sid&&x.team_id===r.team_id)?.table_title)||r.season)},{key:'team_name',label:'Drużyna',render:r=>teamLink(r.team_id,r.team_name)},{key:'date',label:'Data',render:r=>formatDate(r.date),sort:r=>r.date},{key:'match',label:'Mecz',render:r=>matchLink(r)},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'result',label:'Rezultat',render:r=>resultBadge(r),sort:r=>r.margin},{key:'halftime',label:'HT',render:r=>halftimeScoreBadge(r.ht_for,r.ht_against)},{key:'event_link',label:'Link',render:r=>eventLink(r.event_link)}],()=>promotionMatchRowsActive(),{defaultSort:'date',defaultDir:'desc',scroller:true});
      table('orlik2026-table',[{key:'team_name',label:'Drużyna',render:r=>teamLink(r.team_id,r.team_name)},{key:'hall_pos',label:'Hala 25/26',render:r=>rankTag(r.hall.pos),sort:r=>r.hall.pos},{key:'hall_ppg',label:'PPG hala',render:r=>prettyNum(r.hall.ppg),sort:r=>r.hall.ppg},{key:'orlik_2025',label:'Orlik 2025',render:r=>orlik2026TableCell(r),sort:r=>r.orlik_2025?r.orlik_2025.ppg:-1},{key:'bosch_hall_match',label:'Bosch na hali',render:r=>orlik2026HallCell(r),sort:r=>r.bosch_hall_match?r.bosch_hall_match.margin:-99},{key:'bosch_orlik_match',label:'Bosch na orliku',render:r=>orlik2026MatchCell(r.bosch_orlik_match,'ostatni mecz orlika Bosch'),sort:r=>r.bosch_orlik_match?(r.bosch_orlik_match.gf-r.bosch_orlik_match.ga):-99},{key:'leader',label:'Lider hali',render:r=>orlik2026LeaderLine(r,'hall'),sort:r=>orlik2026Leader(r,0,'hall')?.points??-1},{key:'close_ppg',label:'Pkt/mecz stykowy',labelHtml:tip('Pkt/mecz stykowy','Pkt/mecz stykowy'),render:r=>prettyNum(r.hall.close_ppg),sort:r=>r.hall.close_ppg},{key:'threat_level',label:'Poziom zagrożenia',labelHtml:tip('Poziom zagrożenia','Poziom zagrożenia'),render:r=>`<span class="tag ${orlik2026ThreatClass(r.threat_level)}">${esc(r.threat_level)}</span>`,sort:r=>r.threat_score},{key:'plan',label:'Najkrótszy plan',render:r=>esc((r.scouting.bosch_plan||[])[0]||r.scouting.summary)}],()=>orlik2026RowsActive(),{season:false,video:false,defaultSort:'threat_level',scroller:true});
      table('video-season-table',[{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,seasonMetaMap.get(String(r.sid))?.table_title||r.season)},{key:'matches_total',label:'Mecze'},{key:'matches_with_video',label:'Z materiałem'},{key:'coverage_pct',label:'Pokrycie %'},{key:'minutes',label:'Minuty'},{key:'full_matches',label:'Pełne 2 połowy'}],()=>VIDEO.season_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('recommended-table',[{key:'reason',label:'Powód'},{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,seasonMetaMap.get(String(r.sid))?.table_title||r.season)},{key:'date',label:'Data'},{key:'display_opponent',label:'Rywal',render:r=>teamLink(r.opponent_id,r.display_opponent||r.opponent)},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'watch',label:'Linki',render:r=>[eventLink(r.event_link),...(r.links||[]).map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)}</a>`)].join('<br>')}],()=>VIDEO.recommended_rows.map(x=>({...x.match,reason:x.reason})),{defaultSort:'date'});
      table('matched-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon',render:r=>seasonTableLink(r.sid,r.season,seasonMetaMap.get(String(r.sid))?.table_title||r.season)},{key:'display_opponent',label:'Rywal',render:r=>teamLink(r.opponent_id,r.display_opponent||r.opponent)},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'coverage_type',label:'Pokrycie'},{key:'duration_minutes',label:'Minuty'},{key:'watch',label:'Linki',render:r=>[eventLink(r.event_link),...(r.links||[]).map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)} | ${esc(l.channel_handle)}</a>`)].join('<br>')}],()=>VIDEO.matched_rows,{defaultSort:'date'});
      table('match-log-table',[{key:'date',label:'Data',render:r=>formatDate(r.date),sort:r=>r.date},{key:'season',label:'Sezon'},{key:'match',label:'Mecz'},{key:'score',label:'Wynik',render:r=>scoreBadgeFor(r.gf,r.ga,`${r.gf}:${r.ga}`)},{key:'result',label:'Rezultat',render:r=>resultBadge(r),sort:r=>r.gf-r.ga},{key:'halftime',label:'HT',render:r=>halftimeBadge(r.halftime)},{key:'slot',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'coverage_type',label:'Wideo',render:r=>r.video_count?`<span class="tag ${norm(r.coverage_type).includes('pełne')||norm(r.coverage_type).includes('pelne')?'teal':'orange'}">${esc(r.coverage_type)}</span>`:'<span class="tag red">brak</span>'},{key:'video_count',label:'Segmenty'},{key:'event_link',label:'Linki',render:r=>{const event=`<a href="${r.event_link}" target="_blank" rel="noreferrer">mecz</a>`;const watch=r.links?.length?r.links.map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)}</a>`).join('<br>'):'';return [event,watch].filter(Boolean).join('<br>')}}],()=>VIDEO.match_rows,{defaultSort:'date',defaultDir:'desc',scroller:true});
      table('channel-table',[{key:'channel_name',label:'Kanał'},{key:'channel_handle',label:'Handle'},{key:'videos',label:'Wideo'},{key:'matched',label:'Dopasowane'},{key:'unmatched',label:'Niedopasowane'},{key:'minutes',label:'Minuty'},{key:'first_date',label:'Pierwszy upload',render:r=>formatDate(r.first_date),sort:r=>r.first_date},{key:'last_date',label:'Ostatni upload',render:r=>formatDate(r.last_date),sort:r=>r.last_date}],()=>VIDEO.channel_summary_rows,{season:false,defaultSort:'matched',scroller:true});
      table('unmatched-table',[{key:'channel_name',label:'Kanał'},{key:'title',label:'Tytuł'},{key:'publish_date',label:'Data',render:r=>formatDate(r.publish_date),sort:r=>r.publish_date},{key:'duration_text',label:'Długość'},{key:'view_count',label:'Wyświetlenia'},{key:'url',label:'Link',render:r=>`<a href="${r.url}" target="_blank" rel="noreferrer">otwórz</a>`}],()=>VIDEO.unmatched_rows,{season:false,defaultSort:'publish_date',defaultDir:'desc',scroller:true});
    }
    function meta(){document.getElementById('season-meta').textContent=`Aktywny zakres: ${activeRangeLabel()}`}
    function refresh(){summary();seasonCards();currentPlayers();renderRecommendations();renderPromotionSummary();renderPromotionCards();renderOrlik2026Summary();renderOrlik2026Lists();renderOrlik2026Cards();hero();bars('points-chart',REPORT.season_rows,'season','points','#1d4ed8');bars('ppg-chart',REPORT.season_rows,'season','ppg','#0f766e');bars('first-goal-chart',REPORT.state_rows,'season','first_goal_share','#0f766e','%');bars('video-chart',VIDEO.season_rows,'season','coverage_pct','#ea580c','%');barList('promotion-ppg-chart',promotionRowsActive(),'team_name','ppg','#1d4ed8',{subLabelKey:'season',decimals:2});barList('promotion-gap-chart',promotionRowsActive(),'team_name','gap_to_third','#0f766e',{subLabelKey:'season',decimals:0});barList('promotion-defense-chart',promotionRowsActive().map(r=>({...r,ga_pg:Number((r.ga/Math.max(1,r.matches)).toFixed(2))})),'team_name','ga_pg','#ea580c',{subLabelKey:'season',decimals:2});barList('promotion-close-chart',promotionRowsActive(),'team_name','close_ppg','#0f766e',{subLabelKey:'season',decimals:2});barList('orlik2026-threat-chart',orlik2026RowsVisible().map(r=>({...r,threat_sub:`hala ${r.hall.pos}. | ${prettyNum(r.hall.ppg)} PPG`})),'team_name','threat_score','#1d4ed8',{season:false,subLabelKey:'threat_sub',decimals:2});barList('orlik2026-shift-chart',orlik2026ShiftRows().sort((a,b)=>safeNum(b.orlik_ppg,0)-safeNum(a.orlik_ppg,0)),'team_name','orlik_ppg','#0f766e',{season:false,subLabelKey:'shift_note',decimals:2});distribution('timing-all-chart',REPORT.goal_timing_all,'#1d4ed8');distribution('timing-current-chart',REPORT.goal_timing_current,'#0f766e');comparisonChart();surfaceChart();renderNotes();meta();renderers.forEach(fn=>fn())}
    hero();bindControls();initTooltips();initToolbar();initResponsiveCharts();register();sync();refresh();
  </script>
</body>
</html>
"""


def build_site() -> Path:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    video = json.loads(VIDEO_PATH.read_text(encoding="utf-8"))
    promo = json.loads(PROMO_PATH.read_text(encoding="utf-8"))
    orlik2026 = json.loads(ORLIK2026_PATH.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    reference = build_reference_map(report, video, promo, orlik2026)
    REFERENCE_PATH.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")
    html = TEMPLATE.replace("__REPORT_JSON__", json.dumps(report, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__VIDEO_JSON__", json.dumps(video, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__PROMO_JSON__", json.dumps(promo, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__ORLIK2026_JSON__", json.dumps(orlik2026, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__PROFILE_JSON__", json.dumps(profiles, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__REFERENCE_JSON__", json.dumps(reference, ensure_ascii=False).replace("</", "<\\/"))
    OUT_PATH.write_text(html, encoding="utf-8")
    return OUT_PATH


if __name__ == "__main__":
    print(build_site())
