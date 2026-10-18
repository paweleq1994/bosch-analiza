import json,subprocess,re
urls=["https://www.youtube.com/@martawnuszynska9993/videos","https://www.youtube.com/@martawnuszynska9993/streams","https://www.youtube.com/@piotrgoabeski3337/videos"]
for url in urls:
 print("PROBE",url,flush=True)
 try:
  p=subprocess.run(["yt-dlp","--flat-playlist","--playlist-end","250","--dump-single-json","--no-warnings","--socket-timeout","10",url],capture_output=True,text=True,timeout=90)
  print("RESULT",p.returncode,"STDERR",p.stderr[-1500:],flush=True)
  if p.returncode==0:
   d=json.loads(p.stdout); es=d.get("entries") or [];print("COUNT",len(es),flush=True)
   for v in es[:8]:print("EXAMPLE",v.get("id"),v.get("title"),flush=True)
   for v in es:
    if re.search("bosch|tech.car|orlik",str(v.get("title","")),re.I):print("MATCH",v.get("id"),v.get("title"),flush=True)
 except Exception as e:print("ERROR",str(e),flush=True)
