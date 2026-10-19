#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/assets/data.json"
OUTPUT = ROOT / "reports/player-data-coverage.md"
FIELDS = ("apps", "goals", "assists", "motm", "yellow", "red")
LABELS = {
    "apps": "Występy",
    "goals": "Bramki",
    "assists": "Asysty",
    "motm": "MVP",
    "yellow": "Żółte kartki",
    "red": "Czerwone kartki",
}


def build_report(database: dict) -> str:
    players = database["players"]
    manifest = database.get("media") or {}
    photo_counts = {
        str(subject["id"]): len(subject.get("photos") or [])
        for subject in manifest.get("subjects") or []
        if subject.get("kind") == "players"
    }
    missing_photos = []
    unknown_totals = []
    unassigned_stats = []
    unknown_seasons = []
    missing_careers = []
    missing_sources = []
    counts = Counter()

    for player in sorted(players, key=lambda item: item["name"].casefold()):
        identifier = str(player["id"])
        name = player["name"]
        profile = f"{name} (PLP ID {identifier})"
        source = player.get("profile_url") or ""
        history = player.get("season_history") or []

        if not photo_counts.get(identifier):
            missing_photos.append(profile)

        if not player.get("career_totals"):
            missing_careers.append(profile)

        if not source:
            missing_sources.append(profile)

        for field in FIELDS:
            if player.get(field) is None:
                counts["unknown_total_" + field] += 1
                unknown_totals.append((profile, LABELS[field]))

            remainder = (player.get("season_coverage") or {}).get("unassigned", {}).get(field)

            if isinstance(remainder, int) and not isinstance(remainder, bool) and remainder > 0:
                counts["unassigned_" + field] += 1
                unassigned_stats.append((profile, LABELS[field], str(remainder)))

            for entry in history:
                if entry.get(field) is None:
                    counts["missing_season_" + field] += 1
                    unknown_seasons.append((profile, str(entry.get("name") or entry.get("sid")), LABELS[field]))

    audit = database.get("analysis", {}).get("match_protocol_audit", {})
    goals = database.get("analysis", {}).get("player_goal_coverage", [])
    total_goals = sum(item["team_goals"] for item in goals)
    unresolved_goals = sum(item["unattributed_goals"] for item in goals)
    report = [
        "# Audyt kompletności kompendium Bosch Service Tech-Car",
        "",
        "Raport generowany z aktualnego JSON portalu. Brak oznacza brak potwierdzonych danych, nie wartość zero.",
        "",
        "## Podsumowanie",
        "",
        f"- Zawodnicy: **{len(players)}**",
        f"- Sezony: **{len(database['seasons'])}**",
        f"- Mecze: **{len(database['matches'])}**",
        f"- Oficjalne protokoły bramkowe: **{sum(bool(match.get('goal_protocol', {}).get('verified')) for match in database['matches'])}**",
        f"- Bramki drużyny: **{total_goals}**, nierozliczone: **{unresolved_goals}**",
        f"- Samobóje Boscha: **{audit.get('total_own_goals_conceded', 'brak danych')}**",
        f"- Zawodnicy ze zdjęciem: **{len(players) - len(missing_photos)}**, bez zdjęcia: **{len(missing_photos)}**",
        f"- Zawodnicy bez pełnego archiwum kariery PLP: **{len(missing_careers)}**",
        f"- Zawodnicy bez linku do publicznego profilu PLP: **{len(missing_sources)}**",
        "",
        "## Zakresy brakujących statystyk",
        "",
        "| Statystyka | Nieznana suma zawodnika | Znany bilans nieprzypisany do sezonów | Puste dane sezonowe |",
        "|---|---:|---:|---:|",
    ]

    for field in FIELDS:
        report.append(
            f"| {LABELS[field]} | {counts['unknown_total_' + field]} | "
            f"{counts['unassigned_' + field]} | {counts['missing_season_' + field]} |"
        )

    sections = [
        ("Bez potwierdzonego zdjęcia indywidualnego", missing_photos),
        ("Bez pełnej historii kariery PLP", missing_careers),
        ("Bez publicznego linku profilu PLP", missing_sources),
    ]

    for heading, values in sections:
        report.extend(["", "## " + heading, ""])
        report.extend(f"- {value}" for value in values)
        if not values:
            report.append("Brak.")

    report.extend(["", "## Bilans znany, ale nieprzypisany do sezonów", ""])
    report.extend(f"- {name}: {field} — {amount}" for name, field, amount in unassigned_stats)
    if not unassigned_stats:
        report.append("Brak.")

    report.extend(["", "## Nieznane dane sezonowe", ""])
    report.extend(f"- {name} — {season}: {field}" for name, season, field in unknown_seasons)
    if not unknown_seasons:
        report.append("Brak.")

    report.extend(["", "## Nieznane sumy zawodników", ""])
    report.extend(f"- {name}: {field}" for name, field in unknown_totals)
    if not unknown_totals:
        report.append("Brak.")

    report.extend([
        "",
        "## Zasady źródłowe",
        "",
        "- Bramki i minuty: indywidualne protokoły PLP i opisane korekty administracyjne.",
        "- Występy, asysty, MVP i kartki: wyłącznie zweryfikowane dane sezonowe PLP lub zachowane archiwa.",
        "- Rozbicie na sezony bez potwierdzenia jest zabronione.",
        "- Zdjęcia: wyłącznie oficjalne załączniki lub jednoznaczne dopasowanie do nazwiska; zdjęcia drużynowe nie potwierdzają tożsamości osoby.",
        "- PLP może blokować niektóre archiwalne profile (HTTP 401); zachowujemy wtedy wcześniejsze wartości i pokazujemy luki.",
        "",
    ])
    recovered = [p for p in players if p.get("public_protocol_review")]
    if recovered:
        report.extend(["", "## Minima kariery odtworzone z publicznych protokołów", "",
                       "Pełne kariery pozostają niepotwierdzone. Przegląd całego publicznego API nie obejmuje usuniętych/prywatnych wydarzeń ani nieznanych innych identyfikatorów.", "",
                       "| Zawodnik | M | G | A | MVP | ŻK | CK bezp. | Publiczne wydarzenia sprawdzone |",
                       "|---|---:|---:|---:|---:|---:|---:|---:|"])
        for p in recovered:
            r = p["public_protocol_review"]
            report.append("| " + p["name"] + " | " + " | ".join("≥" + str(r["totals"][f]) for f in FIELDS) + " | " + str(r["archive_events_reviewed"]) + " |")
        report.extend(["", "## Źródłowe protokoły bez oznaczenia sezonu", "",
                       "Znane wartości przypisano do odrębnych protokołów. Nie nadano im fikcyjnego identyfikatora sezonu; nie rozszerzają 113 meczów ligowych.", ""])
        for p in recovered:
            for row in p["public_protocol_review"]["matches"]:
                if not row["season_ids"]:
                    report.append(f"- {p['name']}: {row['date']}, {row['title']} — [protokół {row['event_id']}]({row['source_url']}).")
    return "\n".join(report)


def main() -> None:
    database = json.loads(INPUT.read_text(encoding="utf-8"))
    report = build_report(database)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report, encoding="utf-8")
    print(f"Player data coverage report: {OUTPUT}")


if __name__ == "__main__":
    main()
