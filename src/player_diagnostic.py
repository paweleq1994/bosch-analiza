from urllib.request import Request,urlopen
import json
for path in ("sportspress/v2/players/1960","wp/v2/players/1960"):
 try:
  with urlopen(Request("https://podlaskaliga.pl/wp-json/"+path,headers={"User-Agent":"Bosch-Scout/1.0"}),timeout=25) as r:
   data=json.load(r)
  print("ENDPOINT",path)
  print("KEYS",list(data.keys()))
  print("FEATURED",data.get("featured_media"))
  for key in ("statistics","performance","leagues","seasons","teams"):
   obj=data.get(key)
   if obj is not None:
    print("FIELD",key,"TYPE",type(obj).__name__,"EXCERPT",json.dumps(obj,ensure_ascii=False)[:5000])
 except Exception as e:print("ERROR",path,str(e))
