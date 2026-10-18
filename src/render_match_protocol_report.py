from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "match_protocol_audit_index.json"
FINDINGS_PATH = ROOT / "data" / "match_protocol_audit_findings.json"
OUTPUT_PATH = ROOT / "reports" / "bosch-113-match-protocols.md"

EVIDENCE = [
    ("Hala 2022", 2, "Damian Markowski (1 gol) i samobój rywala (1)", ["7851", "7788"]),
    ("Orlik 2023", 1, "Samobój rywala (1)", ["8366"]),
    ("Orlik 2024", 2, "Tomasz Sołowiej (2 gole)", ["10157", "10254"]),
    ("Orlik 2025", 1, "Kamil Kakareko (1 gol)", ["12165"]),
    ("Hala 2025/26", 1, "Samobój rywala (1)", ["12617"]),
]


def scorer_details(match: dict) -> str:
    if not match["scorers"]:
        return "—"

    parts = []

    for scorer in match["scorers"]:
        minute_label = ", ".join(str(minute) + "′" for minute in scorer.get("goal_minutes") or [])
        details = " (" + minute_label + ")" if minute_label else " (" + str(scorer["goals"]) + " gol)"

        if scorer.get("profile_url"):
            name = "[" + scorer["name"] + "](" + scorer["profile_url"] + ")"
        else:
            name = scorer["name"]

        parts.append(name + details)

    return "; ".join(parts)


def render(source: dict, findings: dict) -> str:
    games = source["matches"]
    by_id = {str(game["id"]): game for game in games}
    by_season = defaultdict(list)

    for game in games:
        by_season[str(game["sid"])].append(game)

    lines = [
        "# Bosch Service Tech-Car — audyt wszystkich 113 protokołów",
        "",
        "**Zakres:** wszystkie 113 spotkań od 20 listopada 2022 do 17 października 2026.",
        "**Metoda:** otwarcie każdej oryginalnej strony meczu PLP i odczyt podpisanych goli z ikoną „Gol” oraz minutą,",
        "oddzielnie statystyki samobójów przeciwników i zweryfikowanych wyników administracyjnych.",
        "",
        "## Wyjaśnienie siedmiu wcześniej nieprzypisanych bramek",
        "",
        "| Sezon | Różnica | Ustalenie | Protokoły PLP |",
        "|---|---:|---|---|",
    ]

    for season, gap, explanation, match_ids in EVIDENCE:
        links = ", ".join(
            "[mecz " + match_id + "](" + by_id[match_id]["event_url"] + ")"
            for match_id in match_ids
        )
        lines.append(f"| {season} | {gap} | {explanation} | {links} |")

    lines.extend([
        "| **Razem** | **7** | **4 gole zawodników i 3 samobóje rywali** | |",
        "",
        "## Kontrola jakości danych",
        "",
        f"- Otworzone strony: **{sum(game['page_status'] == 'ok' for game in games)}/{len(games)}**.",
        f"- Mecze z golami Boscha: **{findings['total_matches_with_scorers']}**; reszta ma 0 goli zdobytych przez zawodników Boscha.",
        "- Każdy mecz ma źródło prowadzące bezpośrednio do protokołu PLP.",
        "- Jeden dodatkowy przypadek poza siedmioma różnicami: [Bosch–VESTA 18.02.2024](" +
        "https://podlaskaliga.pl/wydarzenie/bosch-service-tech-car-vs-vesta-3/" +
        ") — w protokole jest oznaczenie gola bez czytelnej minuty, wymagające ostrożnej weryfikacji.",
        "- Samobóje i bramki administracyjne nie są przypisywane napastnikom Boscha.",
        "",
        "## Cała historia — protokół po protokole",
        "",
    ])

    for season in findings["season_summaries"]:
        sid = str(season["sid"])
        matches = sorted(by_season[sid], key=lambda item: (item["date"], item["id"]))
        lines.extend([
            "### " + season["name"] + f" ({len(matches)} meczów)",
            "",
            "| Data | Przeciwnik | Wynik Boscha | Strzelcy i minuty | Samobóje rywali | Korekty administracyjne | Kontrola | PLP |",
            "|---|---|---:|---|---:|---:|---|---|",
        ])

        for game in matches:
            player_goals = game.get("protocol_player_goals")
            opponent_own_goals = game.get("opponent_own_goals") or 0
            administrative_goals = game.get("administrative_goals") or 0
            compared = player_goals is not None and (
                player_goals + opponent_own_goals + administrative_goals == game["official_team_goals"]
            )
            note = "OK" if compared and game["unreadable_goal_markers"] == 0 else "Do weryfikacji"
            row = [
                game["date"],
                game["opponent"].replace("|", " / "),
                game["score"],
                scorer_details(game).replace("|", " / "),
                str(opponent_own_goals),
                str(administrative_goals),
                note,
                "[Protokół](" + game["event_url"] + ")",
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    findings = json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))
    matches = source["matches"]

    if len(matches) != 113 or not findings["all_pages_fetched"]:
        raise ValueError("Full original PLP match coverage is required")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render(source, findings), encoding="utf-8")
    print("Generated complete Polish markdown audit:", OUTPUT_PATH, "with", len(matches), "matches")


if __name__ == "__main__":
    main()
