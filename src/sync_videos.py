#!/usr/bin/env python3
"""Collect full public YouTube channel archives and link Bosch match videos.

Uses yt-dlp's metadata-only flat playlist, no video downloads or paid API.
Keeps prior verified links when YouTube fails.
"""
from __future__ import annotations
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
import json
import re
import subprocess
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/"data/video_channels.json"
OVERRIDES=ROOT/"data/video_updates.json"
SITE=ROOT/"docs/assets/data.json"
VIDEO_ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
SCORE=re.compile(r"(?<!\d)(\d{1,2})\s*[:-]\s*(\d{1,2})(?!\d)")

def iso_date(value):
    text=str(value or "").replace("-", "")
    if not re.fullmatch(r"20\d{6}", text):return ""
    try:return date.fromisoformat(f"{text[:4]}-{text[4:6]}-{text[6:]}").isoformat()
    except ValueError:return ""

def video_metadata(video):
    """Use the existing Actions dependency for exact dates missing in flat lists."""
    if not VIDEO_ID.fullmatch(video["id"]):raise ValueError("Invalid video ID")
    command=["yt-dlp", "--skip-download", "--no-playlist", "--dump-single-json",
             "--ignore-no-formats-error", "--no-warnings", "--socket-timeout", "8",
             "https://www.youtube.com/watch?v="+video["id"]]
    run=subprocess.run(command,capture_output=True,text=True,timeout=35)
    if run.returncode:raise RuntimeError(run.stderr.strip()[-200:])
    raw=json.loads(run.stdout)
    if raw.get("id") != video["id"]:raise ValueError("Wrong video metadata")
    stamp=iso_date(raw.get("upload_date"))
    if not stamp:raise ValueError("No exact YouTube publication date")
    result={"date":stamp,"date_source":"youtube_upload_date"}
    if type(raw.get("duration")) in (int,float) and raw["duration"]>0:
        result["length_seconds"]=int(raw["duration"])
    return result

def refresh_metadata(snapshot, site, fetch=video_metadata):
    existing={v["id"]:dict(v) for v in site.get("videos",[])}
    for video in snapshot.get("videos",[]):
        existing[video["id"]]={**existing.get(video["id"],{}),**video}
    targets=[v for v in existing.values() if not iso_date(v.get("date")) and v.get("status")!="rejected"]
    targets=targets[:60]  # Retry remaining entries on the next hourly run.
    warnings=[]
    def inspect(video):
        try:return video["id"], fetch(video), None
        except Exception as error:return video["id"], None, f"{video['id']}: {type(error).__name__}: {error}"
    changed={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for pid, metadata, error in pool.map(inspect,targets):
            if error:warnings.append(error)
            elif metadata and iso_date(metadata.get("date")):
                changed[pid]={**existing[pid],**metadata,"date":iso_date(metadata["date"])}
    by_id={v["id"]:dict(v) for v in snapshot.get("videos",[])}
    by_id.update(changed)
    return {**snapshot,"videos":sorted(by_id.values(),key=lambda v:(v.get("date") or "",v["id"]))},warnings

def norm(value):
    txt=unicodedata.normalize("NFD",unescape(str(value or "")).lower())
    return re.sub(r"[^a-z0-9]+"," ","".join(c for c in txt if unicodedata.category(c)!="Mn")).strip()

def score_in(title,match):
    pairs={(int(a),int(b)) for a,b in SCORE.findall(title)}
    return (match["gf"],match["ga"]) in pairs or (match["ga"],match["gf"]) in pairs

def opponent_in(title, opponent):
    t=norm(title);o=norm(opponent)
    # Ignore corporate/legal suffixes and generic locale terms for name variants.
    variants={o}
    variants.add(re.sub(r"\b(bialystok|s a|sp z o o)\b","",o).strip())
    if o=="biuro serwis kopiarki":variants.add("biuro serwis kopiarki")
    if o=="unibep s a":variants.add("unibep")
    return any(len(v)>=4 and re.search(r"(?<!\w)"+re.escape(v)+r"(?!\w)",t) for v in variants)

def match_video(video,matches):
    """Match uniquely using Bosch, result, opponent and official team aliases."""
    title = video["title"]
    if "bosch" not in norm(title):
        return None

    aliases = {}
    for match in matches:
        team_id = str(match.get("opponent_id") or "")
        if team_id:
            aliases.setdefault(team_id, set()).add(match["opponent"])

    candidates = [
        match for match in matches
        if score_in(title, match) and any(
            opponent_in(title, name)
            for name in aliases.get(str(match.get("opponent_id") or ""), {match["opponent"]})
        )
    ]
    # A unique score/name is insufficient when the upload contradicts its
    # season. Delayed archival uploads remain available for manual review.
    raw_date = str(video.get("date") or "").replace("-", "")
    if len(raw_date) == 8 and raw_date.isdigit() and raw_date.startswith("20"):
        try:
            upload_date = date.fromisoformat(
                raw_date[:4] + "-" + raw_date[4:6] + "-" + raw_date[6:]
            )
            nearby = [
                match for match in candidates
                if not match.get("date") or -1 <= (upload_date - date.fromisoformat(match["date"])).days <= 21
            ]
            if len(nearby) == 1:
                return str(nearby[0]["id"])
            return None
        except ValueError:
            pass

    if len(candidates) == 1:
        return str(candidates[0]["id"])

    return None

def list_channel(source):
    channel_id=source.get("channel_id")
    tab=source.get("tab", "videos")
    if tab not in ("videos", "streams"):raise ValueError("invalid channel tab")
    if channel_id:
        if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}",channel_id):raise ValueError("invalid channel ID")
        url=f"https://www.youtube.com/channel/{channel_id}/{tab}"
    else:
        handle=source["handle"].lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",handle):raise ValueError("invalid handle")
        url=f"https://www.youtube.com/@{handle}/{tab}"
    command=["yt-dlp","--flat-playlist","--dump-single-json",
             "--no-warnings","--socket-timeout","12",url]
    run=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if run.returncode:raise RuntimeError(run.stderr.strip()[-500:] or "yt-dlp unavailable")
    entries=json.loads(run.stdout).get("entries") or []
    return [{"id":str(v.get("id") or ""),"title":v.get("title") or "",
             "url":"https://www.youtube.com/watch?v="+str(v.get("id") or ""),
             "date":iso_date(v.get("upload_date")),"channel":source["name"],"segment":("II połowa" if re.search(r"\b(ii|2)\s+po",norm(v.get("title"))) else "I połowa" if re.search(r"\b(i|1)\s+po",norm(v.get("title"))) else ""),
             "match_id":None,"status":"needs_review"} for v in entries
            if VIDEO_ID.fullmatch(str(v.get("id") or ""))
            and (not source.get("title_contains") or norm(source["title_contains"]) in norm(v.get("title")))]

def sync(sources,previous,site,archives):
    existing={v["id"]:dict(v) for v in previous.get("videos",[]) if v.get("id")}
    archived={v["id"] for v in site.get("videos",[]) if v.get("id")}
    matches=site.get("matches") or []
    # Reconcile all archived years, not just the latest Orlik season.
    total_new=0; warnings=[]
    for source in sources:
        try:videos=archives(source)
        except Exception as exc:
            warnings.append(f"{source['name']}: {type(exc).__name__}: {exc}")
            continue
        for index,v in enumerate(videos):
            if v["id"] in existing or v["id"] in archived:
                old=existing.get(v["id"]) or next(row for row in site["videos"] if row["id"]==v["id"])
                # Preserve reviewed bindings while filling missing metadata.
                if iso_date(v.get("date")):
                    existing[v["id"]]={**old,"date":iso_date(v["date"])}
                continue
            target=match_video(v,matches)
            if target:
                v["match_id"]=target;v["status"]="matched_auto"
            existing[v["id"]]=v
            total_new+=1
    # Re-evaluate unassigned videos against every known official season safely.
    for v in existing.values():
        if v["id"] in previous.get("manual_bindings", {}):
            continue
        if v.get("status")=="needs_review":
            candidate=match_video(v,matches)
            if candidate:
                v["match_id"]=candidate;v["status"]="matched_auto"
    return {"videos":sorted(existing.values(),key=lambda v:(v.get("date") or "",v["id"])),
            "manual_bindings":previous.get("manual_bindings",{})},total_new,warnings

def main():
    sources=json.loads(SOURCES.read_text(encoding="utf-8")).get("channels",[])
    previous=json.loads(OVERRIDES.read_text(encoding="utf-8")) if OVERRIDES.exists() else {"videos":[]}
    site=json.loads(SITE.read_text(encoding="utf-8"))
    updated,count,warnings=sync(sources,previous,site,list_channel)
    updated,metadata_warnings=refresh_metadata(updated,site)
    warnings.extend(metadata_warnings)
    for warning in warnings:print("Video source warning:",warning,file=sys.stderr)
    out=json.dumps(updated,ensure_ascii=False,indent=2)+"\n"
    if not OVERRIDES.exists() or out!=OVERRIDES.read_text(encoding="utf-8"):OVERRIDES.write_text(out,encoding="utf-8")
    matches={v["match_id"] for v in updated["videos"] if v.get("status")=="matched_auto" and v.get("match_id","").startswith("orlik26-")}
    print(f"Video scan: {count} discovered, {len(matches)}/15 Orlik 2026 games matched, {len(warnings)} warnings")

if __name__=="__main__":main()
