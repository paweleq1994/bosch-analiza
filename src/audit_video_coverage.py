#!/usr/bin/env python3
"""Report every unlinked match and public video without guessing matches."""
from __future__ import annotations

import json
from pathlib import Path

from sync_videos import match_video

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs/assets/data.json"
REPORT = ROOT / "reports/video-coverage.md"


def build_report(database: dict) -> str:
    matches = database["matches"]
    videos = database["videos"]
    mapped_matches = {
        str(match["id"])
        for match in matches
        if match.get("videos")
    }
    gaps = [match for match in matches if str(match["id"]) not in mapped_matches]
    unmatched = [video for video in videos if not video.get("match_id")]
    rejected = [video for video in unmatched if video.get("status") == "rejected"]
    pending = [video for video in unmatched if video.get("status") != "rejected"]

    report = [
        "# Bosch — źródłowy audyt nagrań YouTube",
        "",
        "Kompendium nie zakłada, że brak filmu oznacza brak rozegranego meczu. ",
        "Automatyczne powiązanie wymaga jednoznacznego rywala i wyniku;",
        "gdy wiele meczów pasuje, materiał pozostaje nieprzypisany.",
        "",
        "## Podsumowanie",
        "",
        f"- Mecze z materiałem wideo: **{len(mapped_matches)} / {len(matches)}**",
        f"- Mecze bez materiału wideo: **{len(gaps)}**",
        f"- Znane filmy: **{len(videos)}**",
        f"- Filmy bez powiązanego meczu: **{len(unmatched)}**",
        f"- Materiały oczekujące na identyfikację: **{len(pending)}**; odrzucone powiązania / materiały spoza meczów: **{len(rejected)}**",
        "",
        "## Pokrycie według sezonów",
        "",
        "| Sezon | Mecze | Z nagraniem | Bez nagrania |",
        "|---|---:|---:|---:|",
    ]
    for season in database["seasons"]:
        season_matches = [match for match in matches if match["sid"] == season["id"]]
        mapped = sum(str(match["id"]) in mapped_matches for match in season_matches)
        report.append(
            f"| {season['name']} | {len(season_matches)} | {mapped} | "
            f"{len(season_matches) - mapped} |"
        )

    report += [
        "",
        "## Nieprzypisane materiały",
        "",
        "| Film YouTube | Kanał | Kandydat z potwierdzonym wynikiem |",
        "|---|---|---|",
    ]

    for video in pending:
        candidate_id = match_video(video, matches)
        candidate = next(
            (match for match in matches if str(match["id"]) == candidate_id),
            None,
        )
        candidate_label = (
            f"[{candidate['date']} — {candidate['opponent']}]({candidate['event_link']})"
            if candidate is not None else "Brak jednoznacznego dopasowania"
        )
        title = str(video["title"]).replace("|", "¦")
        channel = str(video.get("channel") or "").replace("|", "¦")
        report.append(
            f"| [{title}]({video['url']}) | {channel} | {candidate_label} |"
        )

    report += ["", "## Zweryfikowane odrzucenia powiązań", "",
               "| Film | Powód / dowód | Data przeglądu |", "|---|---|---|"]
    for video in rejected:
        reason = str(video.get("review_reason") or "Ręczna korekta źródła").replace("|", "¦")
        report.append(f"| [{video['title'].replace('|', '¦')}]({video['url']}) | {reason} | {video.get('reviewed_at') or '—'} |")
    report += [
        "",
        "## Mecze bez powiązanego nagrania",
        "",
        "| Data | Sezon | Przeciwnik | Wynik | Źródło PLP |",
        "|---|---|---|---|---|",
    ]

    for match in sorted(gaps, key=lambda entry: (entry["date"], str(entry["id"]))):
        report.append(
            f"| {match['date']} | {match['season']} | "
            f"{match['opponent'].replace('|', '¦')} | {match['gf']}:{match['ga']} | "
            f"[protokół]({match.get('event_link') or 'https://podlaskaliga.pl/'}) |"
        )

    report += [
        "",
        "## Zasada dokładności",
        "",
        "Nie generujemy bezpośrednich odnośników YouTube do bramek "
        "bez potwierdzonego przesunięcia między czasem meczu a filmem. "
        "Pierwsza lub druga połowa w tytule nie dowodzi dokładnej sekundy rozpoczęcia gry.",
        "",
    ]

    return "\n".join(report)


def main() -> None:
    database = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    content = build_report(database)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != content:
        REPORT.write_text(content, encoding="utf-8")
    matched = sum(bool(match.get("videos")) for match in database["matches"])
    print(
        f"Video coverage verified: {matched}/{len(database['matches'])} matches; "
        f"{len(database['videos'])} public video records.",
        flush=True,
    )


if __name__ == "__main__":
    main()
