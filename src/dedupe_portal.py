"""Conservative deduplication and cross-reference audit for the published portal."""
import unicodedata,re
def norm(s):
    s=unicodedata.normalize("NFD",str(s or "").lower().replace("ł","l"))
    return re.sub(r"[^a-z0-9]+"," ","".join(c for c in s if unicodedata.category(c)!="Mn")).strip()
def dedupe(data):
    issues=[];sids=set();seasons=[]
    for s in data["seasons"]:
        key=(norm(s["name"]),s.get("matches"),s.get("points"),s.get("gf"),s.get("ga"))
        if key in sids:
            issues.append("Repeated season: "+s["name"]);continue
        sids.add(key);seasons.append(s)
    data["seasons"]=seasons
    identity={};matches=[]
    for m in data["matches"]:
        key=(str(m["sid"]),m["date"],norm(m["opponent"]))
        old=identity.get(key)
        if old is None:
            identity[key]=m;matches.append(m);continue
        if (old["gf"],old["ga"])!=(m["gf"],m["ga"]):
            raise ValueError("Conflicting fixture results: "+str(key))
        for v in m.get("videos") or []:
            if v.get("video_id") not in {x.get("video_id") for x in old.get("videos") or []}:
                old.setdefault("videos",[]).append(v)
        if "podlaskaliga.pl/wydarzenie/" in str(m.get("event_link")):old["event_link"]=m["event_link"]
        issues.append("Repeated fixture: "+str(key))
    data["matches"]=matches
    ids=set();videos=[]
    for v in data["videos"]:
        if v["id"] in ids:
            issues.append("Repeated video "+str(v["id"]));continue
        ids.add(v["id"]);videos.append(v)
    data["videos"]=videos
    real_by_name={}
    for p in data["players"]:
        if str(p["id"]).isdigit():
            real_by_name.setdefault(norm(p["name"]),[]).append(p)
    retained=[]
    for p in data["players"]:
        if not str(p["id"]).startswith("new-"):retained.append(p);continue
        real=real_by_name.get(norm(p["name"]),[])
        if len(real)!=1:retained.append(p);continue
        winner=real[0]
        if p.get("orlik2026") and not winner.get("orlik2026"):winner["orlik2026"]=p["orlik2026"]
        if p.get("season_history"):
            existing={x["sid"]:x for x in winner.get("season_history",[])}
            for x in p["season_history"]:existing.setdefault(x["sid"],x)
            winner["season_history"]=list(existing.values())
        issues.append("Merged synthetic player "+str(p["id"])+" into "+str(winner["id"]))
    data["players"]=retained
    opponents={}
    distinct=[]
    for p in data.get("analysis",{}).get("scouting",[]):
        key=str(p.get("team_id") or "") or norm(p.get("name"))
        if key in opponents:
            issues.append("Repeated rival "+str(key));continue
        opponents[key]=p;distinct.append(p)
    data["analysis"]["scouting"]=distinct
    data["meta"]["seasons_count"]=len(seasons)
    return data,issues
