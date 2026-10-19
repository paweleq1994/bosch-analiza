#!/usr/bin/env python3
"""Source-level numeric audit of every Bosch player and public PLP career record.

Career totals for ALL clubs are not interchangeable with Bosch-only totals.
Different official source values are retained as separate, attributed facts.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

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
    for player in database["players"]:
        pid = str(player["id"])
        rest = rest_snapshots.get(pid) or {}
        html = html_snapshot.get("players", {}).get(pid) or {}
        browser_career = html.get("totals") or {}
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
        "| Zawodnik | Statystyka | HTML (cała kariera) | API / kompendium | Różnica | Rodzaj porównania | Oficjalne źródło |",
        "|---|---|---:|---:|---:|---|---|",
    ]

    for item in audit_data["career_source_differences"]:
        report.append(
            f"| {item['name']} (ID {item['id']}) | {LABEL[item['field']]} | "
            f"{item['html']} | {item['rest']} | {item['difference']:+d} | "
            f"{item['type']} | [profil PLP]({item['url']}) |"
        )

    if not audit_data["career_source_differences"]:
        report.append("| Brak rozbieżności | — | — | — | — | — | — |")

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
