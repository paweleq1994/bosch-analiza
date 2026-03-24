from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import json
import re
import time
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "bosch_service_tech_car_data_v3.json"
OUT_PATH = ROOT / "data" / "promoted_teams_analysis.json"
RAW_ROOT = ROOT / "data" / "promotion_cache"
TABLE_RAW_DIR = ROOT / "data" / "promotion_tables_raw"

PROMOTION_SEASON_IDS = [120, 125, 139, 141, 144, 146]
EXCLUDED_TEAM_IDS: set[int] = set()
USER_AGENT = "Mozilla/5.0"
BASE = "https://podlaskaliga.pl/wp-json/sportspress/v2"

TAG_RE = re.compile(r"<[^>]+>")
GOAL_MINUTE_RE = re.compile(r"(\d+)(?:\+(\d+))?'")


def request_json(url: str, cache_path: Path | None = None) -> object:
    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.load(response)
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(0.12)
            return data
        except Exception as exc:  # pragma: no cover - network retries
            last_error = exc
            time.sleep(1.0 + attempt * 0.8)
    raise RuntimeError(f"Failed to fetch {url}") from last_error


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = unescape(str(value))
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def int_value(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else default


def float_value(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return default


def stat_count(value: object) -> int:
    return int_value(value, 0)


def extract_goal_minutes(value: object) -> list[int]:
    if not value:
        return []
    minutes: list[int] = []
    for base, extra in GOAL_MINUTE_RE.findall(str(value)):
        minutes.append(int(base) + int(extra or "0"))
    return minutes


def season_tables(season_id: int) -> list[dict]:
    preferred = TABLE_RAW_DIR / f"{season_id}.json"
    cache_path = RAW_ROOT / "tables" / f"{season_id}.json"
    if preferred.exists():
        return json.loads(preferred.read_text(encoding="utf-8"))
    url = f"{BASE}/tables?seasons={season_id}&per_page=100"
    return request_json(url, cache_path)  # type: ignore[return-value]


def team_payload(team_id: int) -> dict:
    url = f"{BASE}/teams/{team_id}"
    return request_json(url, RAW_ROOT / "teams" / f"{team_id}.json")  # type: ignore[return-value]


def event_pages(team_id: int, season_id: int) -> list[dict]:
    page = 1
    rows: list[dict] = []
    while True:
        query = urllib.parse.urlencode(
            {
                "teams": team_id,
                "seasons": season_id,
                "per_page": 100,
                "page": page,
                "orderby": "date",
                "order": "asc",
            }
        )
        url = f"{BASE}/events?{query}"
        page_rows = request_json(url, RAW_ROOT / "events" / f"{season_id}_{team_id}_{page}.json")
        if not isinstance(page_rows, list):
            raise TypeError(f"Unexpected event payload for team {team_id} season {season_id}")
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < 100:
            break
        page += 1
    unique: dict[int, dict] = {}
    for row in rows:
        unique[int(row["id"])] = row
    return [unique[key] for key in sorted(unique)]


def player_payloads(player_ids: list[int]) -> dict[int, dict]:
    mapping: dict[int, dict] = {}
    batch_size = 60
    for idx in range(0, len(player_ids), batch_size):
        batch = player_ids[idx : idx + batch_size]
        include = ",".join(str(pid) for pid in batch)
        url = f"{BASE}/players?include={include}&per_page=100"
        cache_path = RAW_ROOT / "player_batches" / f"{idx // batch_size:02d}_{len(batch)}.json"
        data = request_json(url, cache_path)
        if not isinstance(data, list):
            raise TypeError("Unexpected player batch payload")
        for item in data:
            mapping[int(item["id"])] = item
    return mapping


def title_text(obj: dict) -> str:
    return clean_text((obj.get("title") or {}).get("rendered", ""))


def normalized(value: str) -> str:
    text = unescape(value or "").lower()
    return re.sub(r"\s+", " ", text).strip()


def is_general_table(obj: dict) -> bool:
    slug = normalized(str(obj.get("slug") or ""))
    title = normalized(title_text(obj))
    return "fair play" in title or "generalka" in title or "fair-play" in slug or "generalka" in slug


def is_second_tier_table(obj: dict) -> bool:
    slug = normalized(str(obj.get("slug") or ""))
    title = normalized(title_text(obj))
    if is_general_table(obj):
        return False
    return slug.startswith("ii-liga") or slug.startswith("2-liga") or "ii liga" in title


def is_league_table(obj: dict) -> bool:
    slug = normalized(str(obj.get("slug") or ""))
    title = normalized(title_text(obj))
    if is_general_table(obj):
        return False
    return "liga" in slug or "liga" in title


def league_tier(obj: dict) -> str | None:
    slug = normalized(str(obj.get("slug") or ""))
    title = normalized(title_text(obj))
    if slug.startswith("ii-liga") or slug.startswith("2-liga") or "ii liga" in title:
        return "II"
    if slug.startswith("i-liga") or (" i liga" in f" {title}" and "ii liga" not in title):
        return "I"
    return None


def parse_table_rows(obj: dict, season_id: int) -> list[dict]:
    rows = obj.get("data") or {}
    if not isinstance(rows, dict):
        return []
    title = title_text(obj)
    tier = league_tier(obj)
    parsed: list[dict] = []
    for team_id, raw in rows.items():
        item = {
            "team_id": int_value(team_id),
            "team_name": clean_text(raw.get("name")),
            "pos": int_value(raw.get("pos")),
            "points": int_value(raw.get("pkt")),
            "matches": int_value(raw.get("m")),
            "wins": int_value(raw.get("w")),
            "draws": int_value(raw.get("r")),
            "losses": int_value(raw.get("p")),
            "gf": int_value(raw.get("g")),
            "ga": int_value(raw.get("s")),
            "gd": int_value(raw.get("rb")),
            "ppg": round(int_value(raw.get("pkt")) / max(1, int_value(raw.get("m"))), 2),
            "form_html": raw.get("last") or "",
            "season_id": season_id,
            "table_id": int(obj.get("id", 0)),
            "table_title": title,
            "tier": tier,
        }
        if item["team_id"] <= 0 or item["pos"] <= 0 or not item["team_name"] or item["team_name"].lower() == "drużyna":
            continue
        parsed.append(item)
    return sorted(parsed, key=lambda row: (row["pos"], row["team_name"]))


def infer_opponent_name(event: dict, team_id: int, team_name: str) -> str:
    title = title_text(event)
    parts = [part.strip() for part in title.split(" vs ") if part.strip()]
    teams = [int(tid) for tid in event.get("teams", []) if isinstance(tid, int)]
    if len(parts) == 2 and len(teams) >= 2:
        return parts[1] if teams[0] == team_id else parts[0]
    return f"Rywal #{next((tid for tid in teams if tid != team_id), 0)}"


def infer_first_goal_side(team_perf: dict, opp_perf: dict) -> str | None:
    timed: list[tuple[int, str]] = []
    for side, performance in (("for", team_perf), ("against", opp_perf)):
        if not isinstance(performance, dict):
            continue
        for player_id, entry in performance.items():
            if str(player_id) == "0" or not isinstance(entry, dict):
                continue
            for field in ("goals", "samobje"):
                for minute in extract_goal_minutes(entry.get(field)):
                    timed.append((minute, side))
    if not timed:
        return None
    timed.sort(key=lambda item: item[0])
    if len(timed) > 1 and timed[0][0] == timed[1][0] and timed[0][1] != timed[1][1]:
        return None
    return timed[0][1]


def rank_lookup(rows: list[dict], key: str, reverse: bool) -> dict[int, int]:
    ordered = sorted(rows, key=lambda row: (-row[key], row["team_name"]) if reverse else (row[key], row["team_name"]))
    lookup: dict[int, int] = {}
    for index, row in enumerate(ordered, start=1):
        lookup[row["team_id"]] = index
    return lookup


def summarize_player_entry(player_id: int, season_row: dict, player_lookup: dict[int, dict]) -> dict:
    payload = player_lookup.get(player_id, {})
    name = clean_text(((payload.get("title") or {}).get("rendered"))) if payload else f"Zawodnik #{player_id}"
    apps = season_row["apps"]
    goals = season_row["goals"]
    assists = season_row["assists"]
    points = goals + assists
    gk_ratings = season_row["gk_ratings"]
    gk_avg = round(sum(gk_ratings) / len(gk_ratings), 2) if gk_ratings else None
    return {
        "player_id": player_id,
        "name": name,
        "apps": apps,
        "goals": goals,
        "assists": assists,
        "points": points,
        "points_per_match": round(points / max(1, apps), 2),
        "motm": season_row["motm"],
        "top": season_row["top"],
        "yellow": season_row["yellow"],
        "red": season_row["red"],
        "gk_avg": gk_avg,
    }


def build_dataset() -> dict:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    season_meta = {int(row["sid"]): row["season"] for row in report["season_rows"]}
    promotion_rows: list[dict] = []
    team_ids: set[int] = set()

    for season_id in PROMOTION_SEASON_IDS:
        tables = season_tables(season_id)
        second_table = next((obj for obj in tables if is_second_tier_table(obj)), None)
        if not second_table:
            raise RuntimeError(f"Missing second-tier table for season {season_id}")
        rows = parse_table_rows(second_table, season_id)
        if len(rows) < 2:
            raise RuntimeError(f"Not enough rows in second-tier table for season {season_id}")
        third_points = rows[2]["points"] if len(rows) > 2 else rows[1]["points"]
        leader_points = rows[0]["points"]
        attack_ranks = rank_lookup(rows, "gf", reverse=True)
        defense_ranks = rank_lookup(rows, "ga", reverse=False)
        gd_ranks = rank_lookup(rows, "gd", reverse=True)
        season_label = season_meta.get(season_id) or title_text(second_table)
        for row in rows[:2]:
            if row["team_id"] in EXCLUDED_TEAM_IDS:
                continue
            team_ids.add(row["team_id"])
            promotion_rows.append(
                {
                    "sid": season_id,
                    "season": season_label,
                    "table_title": title_text(second_table),
                    "team_id": row["team_id"],
                    "team_name": row["team_name"],
                    "rank": row["pos"],
                    "points": row["points"],
                    "matches": row["matches"],
                    "wins": row["wins"],
                    "draws": row["draws"],
                    "losses": row["losses"],
                    "gf": row["gf"],
                    "ga": row["ga"],
                    "gd": row["gd"],
                    "ppg": row["ppg"],
                    "leader_gap": leader_points - row["points"],
                    "gap_to_third": row["points"] - third_points,
                    "attack_rank": attack_ranks[row["team_id"]],
                    "defense_rank": defense_ranks[row["team_id"]],
                    "gd_rank": gd_ranks[row["team_id"]],
                    "teams_in_table": len(rows),
                    "surface": "hala" if "hala" in normalized(season_label) else "orlik",
                }
            )

    team_lookup = {team_id: team_payload(team_id) for team_id in sorted(team_ids)}
    history_season_ids: set[int] = set()
    for payload in team_lookup.values():
        for season_id in payload.get("seasons", []):
            if isinstance(season_id, int):
                history_season_ids.add(season_id)

    history_tables = {season_id: season_tables(season_id) for season_id in sorted(history_season_ids)}
    history_by_team: dict[int, list[dict]] = defaultdict(list)
    for season_id, tables in history_tables.items():
        for obj in tables:
            if not is_league_table(obj):
                continue
            tier = league_tier(obj)
            if not tier:
                continue
            for row in parse_table_rows(obj, season_id):
                if row["team_id"] not in team_ids:
                    continue
                history_by_team[row["team_id"]].append(row)

    for team_id in history_by_team:
        history_by_team[team_id].sort(key=lambda row: (row["season_id"], row["pos"], row["table_title"]))

    all_player_ids: set[int] = set()
    player_accumulators: dict[tuple[int, int], dict[int, dict]] = {}
    match_rows: list[dict] = []

    for row in promotion_rows:
        team_id = row["team_id"]
        season_id = row["sid"]
        team_name = row["team_name"]
        events = event_pages(team_id, season_id)
        player_totals: dict[int, dict] = defaultdict(
            lambda: {
                "apps": 0,
                "goals": 0,
                "assists": 0,
                "motm": 0,
                "top": 0,
                "yellow": 0,
                "red": 0,
                "gk_ratings": [],
            }
        )

        first_goal_for = 0
        first_goal_against = 0
        first_goal_known = 0
        points_dropped_from_leads = 0
        close_matches = close_wins = close_draws = close_losses = 0
        clean_sheets = failed_to_score = 0
        firsthalf_gf = firsthalf_ga = secondhalf_gf = secondhalf_ga = 0
        win_streak = unbeaten_streak = current_win_streak = current_unbeaten_streak = 0
        biggest_win: dict | None = None
        biggest_loss: dict | None = None
        form_letters: list[str] = []

        for event in events:
            teams = [int(tid) for tid in event.get("teams", []) if isinstance(tid, int)]
            if team_id not in teams:
                continue
            opponent_id = next((tid for tid in teams if tid != team_id), 0)
            team_result = (event.get("results") or {}).get(str(team_id), {})
            opp_result = (event.get("results") or {}).get(str(opponent_id), {})
            gf = int_value(team_result.get("goals"))
            ga = int_value(opp_result.get("goals"))
            ht_for = int_value(team_result.get("firsthalf"))
            ht_against = int_value(opp_result.get("firsthalf"))
            sh_for = int_value(team_result.get("secondhalf"))
            sh_against = int_value(opp_result.get("secondhalf"))
            margin = gf - ga
            result = "W" if margin > 0 else "P" if margin < 0 else "R"
            points = 3 if result == "W" else 1 if result == "R" else 0

            firsthalf_gf += ht_for
            firsthalf_ga += ht_against
            secondhalf_gf += sh_for
            secondhalf_ga += sh_against
            clean_sheets += int(ga == 0)
            failed_to_score += int(gf == 0)
            form_letters.append(result)

            if result == "W":
                current_win_streak += 1
                current_unbeaten_streak += 1
            elif result == "R":
                current_win_streak = 0
                current_unbeaten_streak += 1
            else:
                current_win_streak = 0
                current_unbeaten_streak = 0
            win_streak = max(win_streak, current_win_streak)
            unbeaten_streak = max(unbeaten_streak, current_unbeaten_streak)

            if abs(margin) <= 1:
                close_matches += 1
                if result == "W":
                    close_wins += 1
                elif result == "R":
                    close_draws += 1
                else:
                    close_losses += 1

            first_goal_side = infer_first_goal_side(
                (event.get("performance") or {}).get(str(team_id), {}),
                (event.get("performance") or {}).get(str(opponent_id), {}),
            )
            if first_goal_side:
                first_goal_known += 1
                if first_goal_side == "for":
                    first_goal_for += 1
                    if result != "W":
                        points_dropped_from_leads += 3 - points
                else:
                    first_goal_against += 1

            match_row = {
                "sid": season_id,
                "season": row["season"],
                "team_id": team_id,
                "team_name": team_name,
                "event_id": int(event["id"]),
                "date": str(event.get("date") or "")[:10],
                "match": title_text(event),
                "opponent_id": opponent_id,
                "opponent": infer_opponent_name(event, team_id, team_name),
                "gf": gf,
                "ga": ga,
                "margin": margin,
                "result": result,
                "points": points,
                "ht_for": ht_for,
                "ht_against": ht_against,
                "sh_for": sh_for,
                "sh_against": sh_against,
                "event_link": event.get("link") or "",
            }
            match_rows.append(match_row)

            if biggest_win is None or margin > biggest_win["margin"] or (margin == biggest_win["margin"] and match_row["date"] < biggest_win["date"]):
                biggest_win = match_row
            if biggest_loss is None or margin < biggest_loss["margin"] or (margin == biggest_loss["margin"] and match_row["date"] < biggest_loss["date"]):
                biggest_loss = match_row

            performance = (event.get("performance") or {}).get(str(team_id), {})
            if not isinstance(performance, dict):
                continue
            for player_id, entry in performance.items():
                if str(player_id) == "0" or not isinstance(entry, dict):
                    continue
                pid = int(player_id)
                appearance = bool(
                    str(entry.get("status") or "").strip()
                    or str(entry.get("goals") or "").strip()
                    or str(entry.get("assists") or "").strip()
                    or str(entry.get("pikarzmeczu") or "").strip()
                    or str(entry.get("top") or "").strip()
                    or str(entry.get("yellowcards") or "").strip()
                    or str(entry.get("redcards") or "").strip()
                    or str(entry.get("samobje") or "").strip()
                    or str(entry.get("ocenabramkarza") or "").strip()
                )
                if not appearance:
                    continue
                all_player_ids.add(pid)
                player = player_totals[pid]
                player["apps"] += 1
                player["goals"] += stat_count(entry.get("goals"))
                player["assists"] += stat_count(entry.get("assists"))
                player["motm"] += stat_count(entry.get("pikarzmeczu"))
                player["top"] += stat_count(entry.get("top"))
                player["yellow"] += stat_count(entry.get("yellowcards"))
                player["red"] += stat_count(entry.get("redcards"))
                rating = float_value(entry.get("ocenabramkarza"), 0.0)
                if rating > 0:
                    player["gk_ratings"].append(rating)

        close_ppg = round(((close_wins * 3) + close_draws) / max(1, close_matches), 2) if close_matches else 0.0
        row["close_matches"] = close_matches
        row["close_wins"] = close_wins
        row["close_draws"] = close_draws
        row["close_losses"] = close_losses
        row["close_ppg"] = close_ppg
        row["clean_sheets"] = clean_sheets
        row["failed_to_score"] = failed_to_score
        row["firsthalf_gf"] = firsthalf_gf
        row["firsthalf_ga"] = firsthalf_ga
        row["secondhalf_gf"] = secondhalf_gf
        row["secondhalf_ga"] = secondhalf_ga
        row["first_goal_for"] = first_goal_for
        row["first_goal_against"] = first_goal_against
        row["first_goal_known"] = first_goal_known
        row["first_goal_share"] = round((first_goal_for / max(1, first_goal_known)) * 100, 1) if first_goal_known else None
        row["points_dropped_from_leads"] = points_dropped_from_leads
        row["win_streak"] = win_streak
        row["unbeaten_streak"] = unbeaten_streak
        row["last5_form"] = "".join(form_letters[-5:])
        row["biggest_win"] = biggest_win
        row["biggest_loss"] = biggest_loss
        player_accumulators[(season_id, team_id)] = player_totals

    player_lookup = player_payloads(sorted(all_player_ids))
    promotion_player_rows: list[dict] = []
    detailed_rows: list[dict] = []

    for row in promotion_rows:
        team_id = row["team_id"]
        season_id = row["sid"]
        team_payload_data = team_lookup[team_id]
        team_title = clean_text((team_payload_data.get("title") or {}).get("rendered"))
        history = history_by_team.get(team_id, [])
        history_summary = {
            "league_seasons": len(history),
            "top_tier_seasons": sum(1 for item in history if item["tier"] == "I"),
            "second_tier_seasons": sum(1 for item in history if item["tier"] == "II"),
            "best_top_tier_finish": min((item["pos"] for item in history if item["tier"] == "I"), default=None),
            "best_second_tier_finish": min((item["pos"] for item in history if item["tier"] == "II"), default=None),
            "latest_league_row": max(history, key=lambda item: item["season_id"], default=None),
        }
        post_top = sorted(
            [item for item in history if item["tier"] == "I" and item["season_id"] > season_id],
            key=lambda item: item["season_id"],
        )
        row["team_link"] = team_payload_data.get("link") or ""
        row["team_title"] = team_title
        row["history_summary"] = history_summary
        row["first_post_top_tier"] = post_top[0] if post_top else None

        players = [
            summarize_player_entry(player_id, season_row, player_lookup)
            for player_id, season_row in player_accumulators[(season_id, team_id)].items()
        ]
        players.sort(key=lambda item: (-item["points"], -item["goals"], -item["assists"], item["name"]))
        goals_total = sum(item["goals"] for item in players)
        top1_goal_share = round((players[0]["goals"] / goals_total) * 100, 1) if players and goals_total else 0.0
        top3_goal_share = round((sum(item["goals"] for item in players[:3]) / goals_total) * 100, 1) if goals_total else 0.0
        row["players_used"] = len(players)
        row["scorers_count"] = sum(1 for item in players if item["goals"] > 0)
        row["top1_goal_share"] = top1_goal_share
        row["top3_goal_share"] = top3_goal_share
        row["top_scorer"] = max(players, key=lambda item: (item["goals"], item["points"], item["assists"], -item["player_id"]), default=None)
        row["top_creator"] = max(players, key=lambda item: (item["assists"], item["points"], item["goals"], -item["player_id"]), default=None)
        row["top_points_player"] = max(players, key=lambda item: (item["points"], item["goals"], item["assists"], -item["player_id"]), default=None)
        row["top_mvp_player"] = max(players, key=lambda item: (item["motm"], item["points"], item["goals"], -item["player_id"]), default=None)
        row["leaders"] = players[:8]
        row["league_history"] = history
        row["history_counts"] = {
            "seasons_total": history_summary["league_seasons"],
            "first_league": history_summary["top_tier_seasons"],
            "second_league": history_summary["second_tier_seasons"],
        }

        for player in players:
            promotion_player_rows.append(
                {
                    "sid": season_id,
                    "season": row["season"],
                    "team_id": team_id,
                    "team_name": row["team_name"],
                    **player,
                }
            )

        detailed_rows.append(row)

    detailed_rows.sort(key=lambda item: (item["sid"], item["rank"], item["team_name"]))
    promotion_player_rows.sort(key=lambda item: (item["sid"], item["team_name"], -item["points"], -item["goals"], item["name"]))
    match_rows.sort(key=lambda item: (item["sid"], item["team_name"], item["date"], item["event_id"]))

    summary = {
        "teams": len(detailed_rows),
        "unique_clubs": len({row["team_id"] for row in detailed_rows}),
        "avg_ppg": round(sum(row["ppg"] for row in detailed_rows) / max(1, len(detailed_rows)), 2),
        "avg_gap_to_third": round(sum(row["gap_to_third"] for row in detailed_rows) / max(1, len(detailed_rows)), 2),
        "avg_goals_for_pg": round(sum(row["gf"] / max(1, row["matches"]) for row in detailed_rows) / max(1, len(detailed_rows)), 2),
        "avg_goals_against_pg": round(sum(row["ga"] / max(1, row["matches"]) for row in detailed_rows) / max(1, len(detailed_rows)), 2),
        "avg_close_ppg": round(sum(row["close_ppg"] for row in detailed_rows) / max(1, len(detailed_rows)), 2),
        "avg_top3_goal_share": round(sum(row["top3_goal_share"] for row in detailed_rows) / max(1, len(detailed_rows)), 1),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "promotion_season_ids": PROMOTION_SEASON_IDS,
        "excluded_team_ids": sorted(EXCLUDED_TEAM_IDS),
        "summary": summary,
        "promotions": detailed_rows,
        "player_rows": promotion_player_rows,
        "match_rows": match_rows,
    }


def main() -> Path:
    dataset = build_dataset()
    OUT_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUT_PATH


if __name__ == "__main__":
    print(main())
