from html.parser import HTMLParser
from urllib.request import Request, urlopen
import re

class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.table = 0
        self.row = 0
        self.cell = 0
        self.buff = []
        self.rows = []
        self.table_count = 0
        self.tables = []
        self.label = ""
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.table += 1
            self.table_count += 1
            self.label = a.get("class", "")
            self.tables.append((self.table_count, self.label))
        if self.table and tag=="tr":
            self.row += 1
            self.buff = []
        if self.row and tag in ("td", "th"):
            self.cell += 1
            self.txt = ""
    def handle_data(self, data):
        if self.cell:
            self.txt += data
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell:
            self.buff.append(" ".join(self.txt.split()))
            self.cell -= 1
        if tag=="tr" and self.row:
            if self.buff:self.rows.append((self.table_count,self.label,self.buff))
            self.row -= 1
        if tag=="table" and self.table:
            self.table -= 1

for slug in ["moskal-pawel", "rutkowski-mateusz", "daniluk-dawid", "solowiej-tomasz"]:
    url="https://podlaskaliga.pl/zawodnik/"+slug+"/"
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req,timeout=30) as response:
            html=response.read().decode("utf8","replace")
        parser=Reader()
        parser.feed(html)
        print("PLAYER",slug,len(html),"tables",parser.tables[:35])
        for tid,cl,row in parser.rows:
            if "139" in " ".join(row) or any(k in " ".join(row).lower() for k in ("suma","razem","2026","2025","2024","2023","2022","2021")):
                print("ROW",tid,cl,str(row)[:700])
        print("TOTALS",re.findall(r".{0,80}(?:139|132).{0,90}",html)[:12])
    except Exception as e:
        print("ERROR",slug,str(e))
