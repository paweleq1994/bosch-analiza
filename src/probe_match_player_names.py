from urllib.request import Request,urlopen
import re

urls = {
"10321":"https://podlaskaliga.pl/wydarzenie/vesta-vs-bosch-service-tech-car/",
"10603":"https://podlaskaliga.pl/wydarzenie/bosch-service-tech-car-vs-zps-biaform-sa/",
"11895":"https://podlaskaliga.pl/wydarzenie/zubry-bema-vs-bosch-service-tech-car/",
"1594":"https://podlaskaliga.pl/wydarzenie/bosch-service-tech-car-vs-paka/",
"12285":"https://podlaskaliga.pl/wydarzenie/juan-pablo-bialystok-vs-bosch-service-tech-car/",
}
for player_id,url in urls.items():
    try:
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as f: html=f.read().decode("utf8","replace")
        print("PAGE",player_id,len(html),flush=True)
        for match in list(re.finditer("player-" + player_id,html))[:8]:
            print("MATCH",player_id,html[max(0,match.start()-200):match.end()+500].replace("\n"," ")[:800],flush=True)
    except Exception as e:print("ERROR",player_id,e,flush=True)
