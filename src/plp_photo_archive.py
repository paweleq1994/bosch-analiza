#!/usr/bin/env python3
"""Archive only public PLP media attached to players and Bosch's team page."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode,urlparse
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[1]
API="https://podlaskaliga.pl/wp-json/"
HEADERS={"User-Agent":"Bosch-Analiza/1.0","Accept":"application/json"}
OUT=ROOT/"data/media_manifest.json"

def get(path,params=None):
    url=API+path+("?" + urlencode(params) if params else "")
    with urlopen(Request(url,headers=HEADERS),timeout=18) as response:return json.load(response)

def valid(url):
    u=urlparse(str(url or ""))
    return u.scheme=="https" and u.hostname in ("podlaskaliga.pl","www.podlaskaliga.pl")

def identify(kind,ident,fetch=get):
    try:object=fetch(f"sportspress/v2/{kind}/{ident}")
    except Exception:return []
    candidate=[]
    featured=object.get("featured_media")
    if featured:
        try:candidate.append(fetch(f"wp/v2/media/{featured}"))
        except Exception:pass
    try:
        for page in range(1,5):
            rows=fetch("wp/v2/media",{"parent":ident,"page":page,"per_page":100})
            if not isinstance(rows,list):break
            candidate.extend(rows)
            if len(rows)<100:break
    except Exception:pass
    photos={}
    for m in candidate:
        if not isinstance(m,dict):continue
        url=m.get("source_url")
        if not valid(url) or not str(m.get("mime_type","")).startswith("image/"):continue
        media_id=str(m.get("id") or "")
        if not media_id:continue
        photos[media_id]={"id":media_id,"url":url,"alt":m.get("alt_text") or "","published":m.get("date") or "", "featured":str(featured)==media_id}
    return list(photos.values())

def download(photo,folder):
    with urlopen(Request(photo["url"],headers=HEADERS),timeout=18) as response:
        content_type=response.headers.get("Content-Type","").split(";")[0]
        if content_type not in {"image/jpeg","image/png","image/webp","image/avif"}:raise ValueError("Unsupported image type")
        payload=response.read(6000001)
    if len(payload)>6000000:raise ValueError("File too large")
    suffix={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/avif":".avif"}[content_type]
    folder.mkdir(parents=True,exist_ok=True)
    filename=hashlib.sha256(payload).hexdigest()[:24]+suffix
    target=folder/filename
    if not target.exists():target.write_bytes(payload)
    photo["local"]="media/"+filename

def sync(previous, player_ids,fetch=get, downloader=download, discovered=None):
    subjects={ (s["kind"],str(s["id"])):s for s in previous.get("subjects",[]) }
    errors=[]
    for kind,ident in [("teams","6951")]+[("players",str(p)) for p in player_ids if str(p).isdigit()]:
        key=(kind,ident)
        try:
            new=identify(kind,ident,fetch)
            old={p["id"]:p for p in subjects.get(key,{}).get("photos",[])}
            for photo in new:
                if photo["id"] in old and old[photo["id"]].get("local"):photo["local"]=old[photo["id"]]["local"]
                if not photo.get("local"):
                    try:downloader(photo,ROOT/"docs/media")
                    except Exception as exc:errors.append(f"{kind}/{ident}/{photo['id']}: {exc}")
                old[photo["id"]]=photo
            subjects[key]={"kind":kind,"id":ident,"photos":list(old.values())}
        except Exception as exc:
            errors.append(f"{kind}/{ident}: {type(exc).__name__}: {exc}")
    eligible_ids = {str(player_id) for player_id in player_ids if str(player_id).isdigit()}
    for entry in (discovered or {}).get("matches", []):
        player_id = str(entry.get("player_id") or "")
        photo = dict(entry.get("photo") or {})
        media_id = str(photo.get("id") or "")

        if player_id not in eligible_ids or not media_id.isdigit() or not valid(photo.get("url")):
            continue

        subject = subjects.setdefault(
            ("players", player_id),
            {"kind": "players", "id": player_id, "photos": []},
        )

        if any(str(existing.get("id")) == media_id for existing in subject["photos"]):
            continue

        photo["origin"] = "public_archive_exact_metadata"
        photo["evidence"] = str(entry.get("evidence") or "")

        try:
            downloader(photo, ROOT / "docs/media")
            subject["photos"].append(photo)
        except Exception as error:
            errors.append(f"Detached media {player_id}/{media_id}: {type(error).__name__}: {error}")

    return {"subjects":list(subjects.values()),"notes":"Public PLP media attached to team/player profiles and uniquely matched detached WordPress media. Caption-only mentions are not treated as confirmed portraits."},errors

def main():
    previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"subjects":[]}
    portal=json.loads((ROOT/"docs/assets/data.json").read_text(encoding="utf-8"))
    players=[p["id"] for p in portal["players"] if str(p["id"]).isdigit()]
    discovery_path=ROOT/"data/media_discovery.json"
    discovered=json.loads(discovery_path.read_text(encoding="utf-8")) if discovery_path.exists() else {}
    result,errors=sync(previous,players,discovered=discovered)
    if errors:
        print("PLP photo warnings:",len(errors),file=sys.stderr)
        for err in errors[:8]:print(err,file=sys.stderr)
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=output:
        OUT.write_text(output,encoding="utf-8")
    print("PLP public photos:",sum(len(row["photos"]) for row in result["subjects"]),"in",len(result["subjects"]),"profiles")
if __name__=="__main__":main()
