#!/usr/bin/env python3
"""Source-level numeric audit of every Bosch player and public PLP career record.

Career totals for ALL clubs are not interchangeable with Bosch-only totals.
Different official source values are retained as separate, attributed facts.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re

from sync_plp import norm, season_key

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PORTAL = ROOT / "docs/assets/data.json"
OUTPUT = DATA / "source_reconciliation.json"
REPORT = ROOT / "reports/source-reconciliation.md"
FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
LABEL = {
    "apps": "Mecze", "goals": "Gole", "assists": "Asysty",
    "motm": "MVP", "yellow": "ŻK", "red": "CK",
}


def one(row, field):
    value = (row or {}).get(field)
    return value if type(value) is int and value >= 0 else None


def career_season_key(label):
    text = re.sub(r"(?<=[a-z])(?=\d)", " ", norm(label))
    return season_key(text) or tuple(sorted(text.split()))


def career_season_differences(player, rest, html):
    """Locate arithmetic differences without inferring which club owns a goal."""
    grouped = defaultdict(lambda: {"html": [], "rest": []})
    for source, rows in (("html", html.get("season_rows") or []), ("rest", rest.get("season_rows") or [])):
        for row in rows:
            grouped[career_season_key(row.get("name"))][source].append(row)
    output = []
    for groups in grouped.values():
        label = (groups["html"] or groups["rest"])[0].get("name") or "Nieznany sezon"
        for field in FIELDS:
            values = {
                source: sum(row[field] for row in rows)
                if all(one(row, field) is not None for row in rows) else None
                for source, rows in groups.items()
            }
            if None in values.values() or values["html"] == values["rest"]:
                continue
            output.append({
                "id": str(player["id"]), "name": player["name"], "season": label,
                "season_ids": sorted({str(r["sid"]) for r in groups["rest"] if r.get("sid")}),
                "rest_teams": sorted({str(r.get("team") or "") for r in groups["rest"]}),
                "field": field, **values, "difference": values["html"] - values["rest"],
                "html_row_present": bool(groups["html"]), "rest_row_present": bool(groups["rest"]),
                "html_url": html.get("source_url") or "",
                "rest_url": f"https://podlaskaliga.pl/wp-json/sportspress/v2/players/{player['id']}",
                "reason": "supercup_source_scope" if "superpuchar" in norm(label) else "same_season_source_variance",
                "resolution": "Retain official HTML whole-career value; do not add this difference to Bosch",
            })
    return output


def official_source_urls(player, snapshot, match_sources):
    urls = []
    career = snapshot or {}
    if career.get("source_url"):
        urls.append(career["source_url"])
    if player.get("profile_url"):
        urls.append(player["profile_url"])
    for record in match_sources:
        if record.get("source_url") and record["source_url"] not in urls:
            urls.append(record["source_url"])
    for url in ((player.get("verified_identity_source") or {}).get("evidence_urls") or []):
        if url not in urls:
            urls.append(url)
    return urls


def audit(database, rest_snapshots, html_snapshot, evidence):
    stats_by_player_season = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    match_source_by_player = defaultdict(list)

    for match in evidence.get("matches") or []:
        season = str(match["season_id"])
        for row in match.get("players") or []:
            pid = str(row["player_id"])
            for field, source in (
                ("apps", "appearance"),
                ("goals", "goals"),
                ("assists", "assists"),
                ("motm", "motm"),
                ("yellow", "yellow"),
                ("red", "red"),
            ):
                value = one(row, source)
                if value is not None:
                    stats_by_player_season[pid][season][field] += value
            match_source_by_player[pid].append({
                "match_id": match["match_id"],
                "source_url": match["source_url"],
                "season_id": season,
            })

    differences = []
    season_checks = []
    missing = []
    career_seasons = []
    for player in database["players"]:
        pid = str(player["id"])
        rest = rest_snapshots.get(pid) or {}
        html = html_snapshot.get("players", {}).get(pid) or {}
        browser_career = html.get("totals") or {}
        season_deltas = career_season_differences(player, rest, html) if html else []
        for delta in season_deltas:
            # Whole-career rows may describe other clubs. Compare Bosch match
            # evidence only when the REST season explicitly belongs to Bosch.
            if delta["reason"] != "same_season_source_variance" or delta["rest_teams"] != ["Bosch Service Tech-Car"]:
                continue
            confirmed = sum(stats_by_player_season[pid][sid].get(delta["field"], 0) for sid in delta["season_ids"])
            if confirmed == delta["html"] and confirmed > delta["rest"]:
                delta["reason"] = "rest_below_official_match_minimum"
                delta["match_minimum"] = confirmed
                delta["match_source_urls"] = [r["source_url"] for r in match_source_by_player[pid] if r["season_id"] in delta["season_ids"]]
        career_seasons.extend(season_deltas)
        for field in FIELDS:
            official = one(browser_career, field)
            rest_value = one(rest, field)
            displayed = one(player.get("career_totals"), field)
            if official is not None and rest_value is not None and official != rest_value:
                differences.append({
                    "id": pid,
                    "name": player["name"],
                    "field": field,
                    "html": official,
                    "rest": rest_value,
                    "difference": official - rest_value,
                    "url": html.get("source_url") or player.get("profile_url") or "",
                    "type": "official_html_versus_sportspress_api",
                    "note": "Compare source competitions including Supercup before reconciling",
                })
                details = [r for r in season_deltas if r["field"] == field]
                accounted = sum(r["difference"] for r in details) == official - rest_value
                differences[-1].update({
                    "season_breakdown": details,
                    "status": "explained_supercup_scope" if accounted and details and all(r["reason"] == "supercup_source_scope" for r in details) else "source_variance_requires_review",
                    "note": "Difference located in official season rows; the cause of non-Supercup source variance remains unconfirmed",
                })
                if accounted and details and all(r["reason"] in {"supercup_source_scope", "rest_below_official_match_minimum"} for r in details) and any(r["reason"] == "rest_below_official_match_minimum" for r in details):
                    differences[-1]["status"] = "explained_source_rows_and_match_evidence"
            if official is not None and displayed is not None and official != displayed:
                differences.append({
                    "id": pid,
                    "name": player["name"],
                    "field": field,
                    "html": official,
                    "rest": displayed,
                    "difference": official - displayed,
                    "url": html.get("source_url") or player.get("profile_url") or "",
                    "type": "displayed_career_disagrees_with_html",
                    "note": "This source difference requires investigation",
                })
                contributors = [
                    {"id": str(alias), "value": one(rest_snapshots[str(alias)], field),
                     "url": f"https://podlaskaliga.pl/wp-json/sportspress/v2/players/{alias}"}
                    for alias in player.get("aliases") or []
                    if player.get("merged_source_profiles") and str(alias).isdigit()
                    and str(alias) in rest_snapshots and one(rest_snapshots[str(alias)], field) is not None
                ]
                explained = bool(contributors) and official + sum(r["value"] for r in contributors) == displayed
                differences[-1].update({
                    "status": "explained_verified_identity_merge" if explained else "display_variance_requires_review",
                    "identity_contributions": contributors,
                    "note": "Canonical career includes the separately documented duplicate profile" if explained else "This source difference requires investigation",
                })

        for season, fields in stats_by_player_season.get(pid, {}).items():
            public = (player.get("season_stats") or {}).get(season) or {}
            for field in FIELDS:
                confirmed_minimum = fields.get(field, 0)
                shown = one(public, field)
                if shown is not None and confirmed_minimum > shown:
                    season_checks.append({
                        "id": pid,
                        "name": player["name"],
                        "sid": season,
                        "field": field,
                        "displayed": shown,
                        "source_minimum": confirmed_minimum,
                        "source_urls": sorted({
                            value["source_url"] for value in match_source_by_player[pid]
                            if value["season_id"] == season
                        }),
                        "type": "source_match_minimum_exceeds_season",
                    })

        sources = official_source_urls(
            player, html, match_source_by_player.get(pid) or []
        )
        if not player.get("career_totals"):
            missing.append({
                "id": pid, "name": player["name"],
                "reason": "No public fully enumerated PLP career table",
                "source_urls": sources[:15],
            })

    return {
        "all_players": len(database["players"]),
        "players_with_public_career": len(database["players"]) - len(missing),
        "career_source_differences": differences,
        "career_season_differences": career_seasons,
        "career_difference_status_counts": {
            status: sum(row["status"] == status for row in differences)
            for status in sorted({row["status"] for row in differences})
        },
        "season_source_conflicts": season_checks,
        "missing_full_careers": missing,
        "verified_goal_matches": sum(
            bool((match.get("goal_protocol") or {}).get("verified"))
            for match in database["matches"]
        ),
        "unattributed_team_goals": sum(
            row["unattributed_goals"]
            for row in database["analysis"]["player_goal_coverage"]
        ),
    }


def markdown(audit_data: dict) -> str:
    report = [
        "# Weryfikacja źródeł kariery i meczów — Bosch",
        "",
        "Dane karier HTML oraz SportsPress REST nie są nadpisywane wzajemnie.",
        "Różnica źródłowa oznacza potrzebę sprawdzenia zakresu rozgrywek,",
        "nie automatyczny błąd w statystykach Boscha.",
        "",
        f"- Zawodnicy: **{audit_data['all_players']}**",
        f"- Pełne publiczne kariery PLP: **{audit_data['players_with_public_career']}**",
        f"- Różnice HTML vs API / widok: **{len(audit_data['career_source_differences'])}**",
        f"- Sprzeczne sezonowe minimum z protokołów: **{len(audit_data['season_source_conflicts'])}**",
        f"- Zweryfikowane protokoły goli: **{audit_data['verified_goal_matches']}**",
        f"- Nierozliczone gole drużyny: **{audit_data['unattributed_team_goals']}**",
        "",
        "## Różnice między źródłami kariery PLP",
        "",
        "| Zawodnik | Statystyka | HTML (cała kariera) | API / kompendium | Różnica | Rodzaj porównania | Wyjaśnienie / status | Oficjalne źródło |",
        "|---|---|---:|---:|---:|---|---|---|",
    ]

    for item in audit_data["career_source_differences"]:
        report.append(
            f"| {item['name']} (ID {item['id']}) | {LABEL[item['field']]} | "
            f"{item['html']} | {item['rest']} | {item['difference']:+d} | "
            f"{item['type']} | {item['status']} | [profil PLP]({item['url']}) |"
        )

    if not audit_data["career_source_differences"]:
        report.append("| Brak rozbieżności | — | — | — | — | — | — | — |")

    report += ["", "## Rozliczenie różnic według sezonów i źródeł", "",
               "Brak wiersza oznacza brak składnika w agregacie API, nie potwierdzone zero zawodnika.",
               "Superpuchary wyjaśniają różnicę zakresu. Różnice w pozostałych sezonach pozostają niepewnością źródłową; nie zmieniają automatycznie bilansu Boscha.", "",
               "| Zawodnik | Sezon / ID API | Pole | HTML | REST | Różnica | Przyczyna / niepewność | Źródła |",
               "|---|---|---|---:|---:|---:|---|---|"]
    for row in audit_data["career_season_differences"]:
        rest_value = str(row["rest"]) if row["rest_row_present"] else "brak wiersza"
        match_links = "".join(f" · [protokół]({url})" for url in row.get("match_source_urls") or [])
        report.append(
            f"| {row['name']} (ID {row['id']}) | {row['season']} / {', '.join(row['season_ids']) or 'brak ID w API'} | "
            f"{LABEL[row['field']]} | {row['html']} | {rest_value} | {row['difference']:+d} | {row['reason']} | "
            f"[HTML]({row['html_url']}) · [REST]({row['rest_url']}){match_links} |"
        )
    report += ["", "## Bilans po scaleniu potwierdzonych tożsamości", ""]
    for row in audit_data["career_source_differences"]:
        if row["status"] == "explained_verified_identity_merge":
            additions = ", ".join(f"ID {r['id']}: {r['value']} ([REST]({r['url']}))" for r in row["identity_contributions"])
            report.append(f"- {row['name']} (ID {row['id']}), {LABEL[row['field']]}: HTML {row['html']} + {additions} = kanoniczne {row['rest']}. Bez ponownego dodawania sezonu.")

    report += [
        "",
        "## Protokoły meczowe przekraczające zapisany wynik sezonu",
        "",
        "| Zawodnik | Sezon ID | Statystyka | Widok | Potwierdzone minimum | Źródło |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in audit_data["season_source_conflicts"]:
        url = (row.get("source_urls") or ["https://podlaskaliga.pl/"])[0]
        report.append(
            f"| {row['name']} (ID {row['id']}) | {row['sid']} | "
            f"{LABEL[row['field']]} | {row['displayed']} | "
            f"{row['source_minimum']} | [protokół PLP]({url}) |"
        )

    if not audit_data["season_source_conflicts"]:
        report.append("| Brak | — | — | — | — | — |")

    report += ["", "## Brak publicznej tabeli pełnej kariery", ""]
    for entry in audit_data["missing_full_careers"]:
        sources = ", ".join(
            f"[PLP {index + 1}]({url})"
            for index, url in enumerate(entry["source_urls"][:3])
        )
        report.append(
            f"- **{entry['name']} (ID {entry['id']})** — "
            f"{entry['reason']}; źródła z meczów: {sources or 'brak'}"
        )
    report += [
        "",
        "## Zasady",
        "",
        "- Cała kariera PLP obejmuje również kluby inne niż Bosch i Superpuchary.",
        "- Potwierdzony występ w protokole jest dolnym ograniczeniem, nie dowodem całej kariery.",
        "- Rozbieżność między oficjalnymi źródłami nie jest automatycznie sumowana.",
        "- Nieznana wartość nigdy nie jest zamieniana w zero bez kompletnego źródła.",
        "",
    ]
    return "\n".join(report)


def main():
    portal = json.loads(PORTAL.read_text(encoding="utf-8"))
    careers = json.loads((DATA / "player_career_updates.json").read_text(encoding="utf-8"))
    html = json.loads((DATA / "player_html_career_snapshot.json").read_text(encoding="utf-8"))
    matches = json.loads((DATA / "match_player_evidence.json").read_text(encoding="utf-8"))
    summary = audit(portal, careers, html, matches)

    for location, content in (
        (OUTPUT, json.dumps(summary, ensure_ascii=False, indent=2) + "\n"),
        (REPORT, markdown(summary)),
    ):
        location.parent.mkdir(parents=True, exist_ok=True)
        if not location.exists() or location.read_text(encoding="utf-8") != content:
            location.write_text(content, encoding="utf-8")

    print(
        f"Source reconciliation: {summary['all_players']} players; "
        f"{len(summary['career_source_differences'])} source differences; "
        f"{len(summary['season_source_conflicts'])} contradictory season minima.",
        flush=True,
    )


if __name__ == "__main__":
    main()
