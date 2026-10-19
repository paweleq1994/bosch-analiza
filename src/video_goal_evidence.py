"""Require evidence before creating minute-perfect YouTube links for PLP goals."""
from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data/video_goal_evidence.json"
REPORT = ROOT / "reports/video-goal-review-queue.md"
VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate(database: dict, source: dict) -> list[dict]:
    matches = {str(item["id"]): item for item in database["matches"]}
    videos = {str(item["id"]): item for item in database["videos"]}
    verified = []
    keys = set()

    for row in source.get("entries") or []:
        match_id = str(row.get("match_id") or "")
        player_id = str(row.get("player_id") or "")
        minute = str(row.get("minute") or "")
        video_id = str(row.get("video_id") or "")
        timestamp = row.get("timestamp_seconds")
        review_method = row.get("verification_source")
        verified_by = str(row.get("verified_by") or "").strip()
        reviewed_at = str(row.get("verified_at") or "")

        if not VID.fullmatch(video_id) or type(timestamp) is not int or timestamp < 0:
            raise ValueError("Invalid video ID or playback timestamp")
        if review_method not in {"observed_video_frame", "official_youtube_chapter"}:
            raise ValueError("Goal timestamp has no verifiable review method")
        if len(verified_by) < 2 or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", reviewed_at):
            raise ValueError("Goal timestamp requires an identified reviewer and date")

        match = matches.get(match_id)
        video = videos.get(video_id)
        if not match or not video or str(video.get("match_id")) != match_id:
            raise ValueError("Unlinked goal video and official fixture")
        protocol = match.get("goal_protocol") or {}
        if not protocol.get("verified"):
            raise ValueError("Cannot timestamp an unverified goal protocol")

        scorer = next((
            entry for entry in protocol.get("scorers") or []
            if str(entry["player_id"]) == player_id
            and minute in [str(value) for value in entry.get("minutes") or []]
        ), None)
        if scorer is None:
            raise ValueError("Goal timestamp does not match proven PLP scorer and minute")

        duration = next((
            item["length_seconds"]
            for item in match.get("videos") or []
            if str(item.get("video_id")) == video_id
            and type(item.get("length_seconds")) is int
        ), None)
        if duration is not None and timestamp >= duration:
            raise ValueError("Playback timestamp exceeds video duration")

        key = (match_id, player_id, minute, video_id)
        if key in keys:
            raise ValueError("Duplicate goal timestamp")
        keys.add(key)
        verified.append({
            "match_id": match_id, "player_id": player_id,
            "minute": minute, "video_id": video_id,
            "timestamp_seconds": timestamp,
            "verification_source": review_method,
            "verified_by": verified_by,
            "verified_at": reviewed_at,
            "source_url": protocol["source_url"],
            "url": f"https://www.youtube.com/watch?v={video_id}&t={timestamp}s",
            "review_notes": str(row.get("review_notes") or ""),
            "review_frame": str(row.get("review_frame") or ""),
        })

    return verified


def report(database: dict, verified: list[dict]) -> str:
    proven = {(r["match_id"], r["player_id"], r["minute"]) for r in verified}
    pending = []
    for match in database["matches"]:
        if not (match.get("goal_protocol") or {}).get("verified") or not match.get("videos"):
            continue
        clips = [
            video for video in match["videos"]
            if VID.fullmatch(str(video.get("video_id") or ""))
        ]
        for scorer in match["goal_protocol"].get("scorers") or []:
            for minute in scorer.get("minutes") or []:
                if (str(match["id"]), str(scorer["player_id"]), str(minute)) in proven:
                    continue
                links = " · ".join(
                    f"[{v.get('segment') or 'Nagranie'}](https://www.youtube.com/watch?v={v['video_id']})"
                    for v in clips[:4]
                )
                pending.append(
                    f"| [PLP {match['id']}]({match['goal_protocol']['source_url']}) | "
                    f"{scorer['name']} | {minute}′ | {links} |"
                )

    lines = [
        "# Bosch — kolejka potwierdzania momentów bramek w filmach YouTube",
        "",
        "Minuta meczu i czas nagrania nie są równoważne. Montaż, opóźniony",
        "start nagrania, dogrywka i różne połowy wymagają obejrzenia materiału.",
        f"Potwierdzone linki: **{len(proven)}**.",
        f"Niepotwierdzone gole w meczach z filmem: **{len(pending)}**.",
        "",
        "## Obejrzane i potwierdzone akcje",
        "",
        "Znacznik wskazuje obejrzaną sekundę akcji bramkowej. To czas odtwarzacza, nie przeliczenie minuty meczu.",
        "",
        "| Mecz / zawodnik / minuta PLP | Sekunda filmu | Dowód przeglądu |",
        "|---|---:|---|",
        *[
            f"| [PLP {r['match_id']}]({r['source_url']}) / ID {r['player_id']} / {r['minute']}′ | "
            f"[YouTube {r['timestamp_seconds']} s]({r['url']}) | "
            f"{r.get('review_notes', '').replace('|', '¦')} |"
            for r in verified
        ],
        "",
        "## Gole oczekujące na weryfikację",
        "",
        "| Mecz | Strzelec | Minuta PLP | Nagrania do weryfikacji |",
        "|---|---|---|---|",
        *pending,
        "",
        "Aby dodać bezpośredni link, zapisz w pliku data/video_goal_evidence.json",
        "identyfikatory meczu, zawodnika, filmu, minutę PLP, prawdziwy czas wideo",
        "w sekundach, metodę weryfikacji, osobę sprawdzającą i datę.",
        "Dopuszczalne dowody: obejrzana klatka z golem lub jednoznaczny oficjalny",
        "rozdział filmu YouTube. Samodzielne przeliczenie minut jest zabronione.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
    payload = json.loads(FILE.read_text(encoding="utf-8"))
    verified = validate(database, payload)
    text = report(database, verified)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != text:
        REPORT.write_text(text, encoding="utf-8")
    print(f"Verified goal timestamps: {len(verified)}")


if __name__ == "__main__":
    main()
