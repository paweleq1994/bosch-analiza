#!/usr/bin/env python3
"""Audit Bosch player totals against independent official PLP source evidence."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/assets/data.json"
OUTPUT = ROOT / "reports/player-source-reconciliation.md"
FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")


def audit(database: dict) -> dict:
    players = {str(player["id"]): player for player in database["players"]}
    known_match_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    match_sources = defaultdict(set)

    for match in database["matches"]:
        sid = str(match["sid"])
        source = str(match.get("player_performance_source") or match.get("event_link") or "")
        for entry in match.get("player_performance") or []:
            player_id = str(entry["player_id"])
            for field, source_key in (
                ("apps", "appearance"), ("assists", "assists"),
                ("motm", "motm"), ("yellow", "yellow"), ("red", "red")
            ):
                value = entry.get(source_key)
                if type(value) is int and value >= 0:
                    known_match_stats[player_id][sid][field] += value
            if source.startswith("https://podlaskaliga.pl/"):
                match_sources[(player_id, sid)].add(source)

        if (match.get("goal_protocol") or {}).get("verified"):
            for entry in match["goal_protocol"].get("scorers") or []:
                player_id = str(entry["player_id"])
                known_match_stats[player_id][sid]["goals"] += entry["goals"]
                match_sources[(player_id, sid)].add(
                    match["goal_protocol"].get("source_url") or match["event_link"]
                )

    contradictions = []
    gaps = []
    coverage = []

    for player in sorted(players.values(), key=lambda row: row["name"].casefold()):
        player_id = str(player["id"])
        career = player.get("career_totals") or {}
        public_seasons = career.get("public_season_rows") or []

        for field in FIELDS:
            official_career = career.get(field)
            if public_seasons and type(official_career) is int:
                public_sum = sum(row.get(field, 0) for row in public_seasons)
                # A proven merge of two PLP profile IDs can increase the
                # combined total beyond a single official source profile.
                if official_career < public_sum:
                    contradictions.append({
                        "name": player["name"], "id": player_id,
                        "season": "Cała kariera", "stat": field,
                        "recorded": official_career, "minimum": public_sum,
                        "reason": "Career total below own public season source rows",
                        "urls": [career.get("source_url") or player.get("profile_url") or ""],
                    })

        for sid, observed in known_match_stats.get(player_id, {}).items():
            season_data = (player.get("season_stats") or {}).get(sid) or {}
            for field in FIELDS:
                observed_value = observed.get(field)
                stored = season_data.get(field)
                if type(observed_value) is not int or observed_value <= 0:
                    continue

                urls = sorted(match_sources[(player_id, sid)])
                if type(stored) is int and stored < observed_value:
                    contradictions.append({
                        "name": player["name"], "id": player_id,
                        "season": sid, "stat": field,
                        "recorded": stored, "minimum": observed_value,
                        "reason": "Season total lower than independently documented match events",
                        "urls": urls,
                    })
                elif stored is None:
                    gaps.append({
                        "name": player["name"], "id": player_id,
                        "season": sid, "stat": field, "minimum": observed_value,
                        "urls": urls,
                    })

        coverage.append({
            "id": player_id, "name": player["name"],
            "has_career": bool(career),
            "career_source": career.get("source_url") or player.get("profile_url") or "",
            "incomplete_bosch": bool(player.get("stats_minimum")),
            "unassigned": {
                key: value for key, value in (
                    (player.get("season_coverage") or {}).get("unassigned") or {}
                ).items() if type(value) is int and value > 0
            },
        })

    return {
        "total_players": len(players),
        "total_matches": len(database["matches"]),
        "contradictions": contradictions,
        "known_minimums_without_season_field": gaps,
        "coverage": coverage,
    }


def render(report: dict) -> str:
    text = [
        "# Audyt pochodzenia statystyk Bosch Service Tech-Car",
        "",
        "Porównania bazują na oficjalnych protokołach meczów i osobnych tabelach",
        "kariery PLP. Nie utożsamiamy całej kariery zawodnika z grą w Boschu.",
        "Nieznana liczba i potwierdzone zero nie są tym samym.",
        "",
        f"- Zawodnicy: **{report['total_players']}**",
        f"- Mecze: **{report['total_matches']}**",
        f"- Niespójności wymagające wyjaśnienia: **{len(report['contradictions'])}**",
        f"- Wartości minimalne bez pola sezonowego: **{len(report['known_minimums_without_season_field'])}**",
        f"- Bez pełnego potwierdzonego bilansu kariery PLP: **{sum(not r['has_career'] for r in report['coverage'])}**",
        "",
        "## Sprzeczności z oficjalnymi protokołami",
        "",
        "| Zawodnik | Sezon ID | Pole | W kompendium | Minimum z PLP | Źródło |",
        "|---|---|---|---:|---:|---|",
    ]

    if not report["contradictions"]:
        text.append("| Brak wykrytych sprzeczności | — | — | — | — | — |")

    for row in report["contradictions"]:
        url = next((url for url in row["urls"] if url.startswith("https://")), "")
        source = f"[protokół]({url})" if url else "Brak publicznego URL"
        text.append(
            f"| {row['name']} (ID {row['id']}) | {row['season']} | {row['stat']} | "
            f"{row['recorded']} | ≥ {row['minimum']} | {source} |"
        )

    text += [
        "", "## Potwierdzone minimum, ale brak wpisanej wartości sezonowej",
        "",
        "| Zawodnik | Sezon ID | Pole | Minimum | Źródło |",
        "|---|---|---|---:|---|",
    ]

    if not report["known_minimums_without_season_field"]:
        text.append("| Brak | — | — | — | — |")

    for row in report["known_minimums_without_season_field"]:
        url = row["urls"][0] if row["urls"] else ""
        source = f"[protokół]({url})" if url else "Brak publicznego URL"
        text.append(
            f"| {row['name']} (ID {row['id']}) | {row['season']} | "
            f"{row['stat']} | ≥ {row['minimum']} | {source} |"
        )

    text += [
        "", "## Nieprzypisane do sezonu, choć znane z bilansu zawodnika",
        "",
        "| Zawodnik | Pole | Liczba |",
        "|---|---|---:|",
    ]
    unresolved = [
        (person, field, count)
        for person in report["coverage"]
        for field, count in person["unassigned"].items()
    ]

    if not unresolved:
        text.append("| Brak | — | — |")

    for person, field, count in unresolved:
        text.append(f"| {person['name']} (ID {person['id']}) | {field} | {count} |")

    text += [
        "", "## Zasady weryfikacji",
        "",
        "- Meczowy występ, gol, asysta lub kartka dają dolną granicę z konkretnego protokołu.",
        "- Agregat sezonowy nie może być mniejszy niż suma niezależnie potwierdzonych zdarzeń.",
        "- Statystyki innych klubów i Superpucharów nie są automatycznie zaliczane do Boscha.",
        "- Złączenie dwóch tożsamości PLP wymaga ręcznie udokumentowanej identyczności osoby.",
        "- Pustego wyniku nie uzupełniamy zerem bez kompletu potwierdzonych meczów.",
        "",
    ]
    return "\n".join(text)


def main() -> None:
    database = json.loads(INPUT.read_text(encoding="utf-8"))
    report = audit(database)
    content = render(report)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
        OUTPUT.write_text(content, encoding="utf-8")
    print(
        f"Player provenance audit: {len(report['contradictions'])} lower-than-source totals, "
        f"{len(report['known_minimums_without_season_field'])} unassigned season minimums",
        flush=True,
    )


if __name__ == "__main__":
    main()
