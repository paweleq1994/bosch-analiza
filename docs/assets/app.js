"use strict";
let DB=null;
const $=id=>document.getElementById(id);
const e=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const fmt=(n,d=2)=>Number.isFinite(Number(n))?Number(n).toLocaleString("pl-PL",{maximumFractionDigits:d}):"—";
const ppg=s=>s?.matches?fmt(s.points/s.matches):"—";
const videoId=v=>String(v?.video_id||v?.id||"");
const href=(route,label)=>'<a href="#/'+route+'">'+e(label)+'</a>';
const same=(a,b)=>String(a)===String(b);
const season=sid=>DB.seasons.find(s=>same(s.id,sid));
const result=m=>m.gf>m.ga?"W":m.gf<m.ga?"P":"R";
const resultClass=m=>m.gf>m.ga?"win":m.gf<m.ga?"loss":"draw";
const normalized=value=>String(value??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const headline=(name,description)=>'<div class="hero"><span class="eyebrow">Bosch Service Tech-Car</span><h1>'+e(name)+'</h1><p class="lead">'+e(description)+'</p></div>';
const metrics=items=>'<div class="metric-grid">'+items.map(([label,value])=>'<div class="metric"><small>'+e(label)+'</small><b>'+e(value)+'</b></div>').join("")+'</div>';
const section=(title,content)=>'<section><h2>'+e(title)+'</h2>'+content+'</section>';
const table=(heads,rows)=>'<div class="table-card"><table class="table"><thead><tr>'+heads.map(x=>'<th>'+e(x)+'</th>').join("")+'</tr></thead><tbody>'+rows.map(cols=>'<tr>'+cols.map(cell=>'<td>'+cell+'</td>').join("")+'</tr>').join("")+'</tbody></table></div>';
const cards=rows=>'<div class="grid">'+rows.map(row=>'<div class="card">'+row+'</div>').join("")+'</div>';
const empty=message=>'<div class="notice">'+e(message)+'</div>';
const filterInput=(placeholder="Szukaj…")=>'<div class="filters"><input id="local-filter" placeholder="'+e(placeholder)+'" aria-label="Filtruj wyniki"><select id="season-filter"><option value="">Wszystkie sezony</option>'+DB.seasons.slice().reverse().map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select></div>';
const seasonLink=s=>href("season/"+encodeURIComponent(s.id),s.name);
const playerLink=p=>href("player/"+encodeURIComponent(p.id),p.name);
const matchLink=m=>href("match/"+encodeURIComponent(m.id),m.opponent);
const winner=m=>'<strong class="'+resultClass(m)+'">'+e(m.gf+":"+m.ga)+'</strong>';
function matchList(matches,limit=0){const list=matches.slice().sort((a,b)=>b.date.localeCompare(a.date));return list.slice(0,limit||list.length).map(m=>'<div class="list-row"><div><div class="small">'+e(m.date)+' • '+href("season/"+encodeURIComponent(m.sid),m.season)+'</div>'+matchLink(m)+'</div>'+winner(m)+'</div>').join("")||empty("Brak spotkań w wybranym zakresie.")}
function barChart(rows,key,label){const max=Math.max(1,...rows.map(x=>Number(x[key])||0));return '<div class="card bar-chart">'+rows.map(s=>'<div class="bar-row"><span>'+e(s.name)+'</span><div class="bar-track"><span style="width:'+Math.max(0,Math.min(100,(Number(s[key])||0)/max*100))+'%"></span></div><b>'+e(label?label(s):fmt(s[key]))+'</b></div>').join("")+'</div>';}
function home(){const latest=DB.seasons.at(-1),recent=DB.matches.filter(m=>same(m.sid,latest.id));const leaders=DB.players.filter(p=>p.orlik2026).sort((a,b)=>(b.orlik2026.goals+b.orlik2026.assists)-(a.orlik2026.goals+a.orlik2026.assists)).slice(0,4);return headline("Wszystko o Bosch w jednym miejscu","Wyniki, historia sezonów, statystyki zawodników, mecze i nagrania. Bez przewijania gigantycznego raportu.")+metrics([["Ostatni sezon",latest.name],["Miejsce",latest.position+"."],["Punkty",latest.points],["Bramki",latest.gf+":"+latest.ga]])+'<div class="columns">'+section("Ostatnie wyniki",'<div class="card">'+matchList(recent,5)+'</div><p>'+href("season/"+latest.id,"Otwórz pełny sezon →")+'</p>')+section("Liderzy Orlika 2026",'<div class="card">'+leaders.map(p=>'<div class="list-row">'+playerLink(p)+'<strong>'+e(p.orlik2026.goals+p.orlik2026.assists)+' G+A</strong></div>').join("")+'</div><p>'+href("players","Wszyscy zawodnicy →")+'</p>')+'</div>'+section("Odkrywaj kompendium",cards([["Sezony","season/"+latest.id,"Zobacz pełną analizę Orlika 2026"],["Wszystkie mecze","matches","Znajdź wybrane spotkanie i nagrania"],["Rekordy","records","Najlepsze wyniki drużyny"],["Analityka","analysis","Zaawansowane porównania i benchmarking"]].map(([title,route,desc])=>'<h3>'+href(route,title+" →")+'</h3><p>'+e(desc)+'</p>')));}
function seasons(){return headline("Sezony","Wszystkie rozgrywki Boscha i porównanie ich wyników.")+metrics([["Sezonów",DB.seasons.length],["Łącznie spotkań",DB.seasons.reduce((n,s)=>n+s.matches,0)],["Najwięcej punktów",Math.max(...DB.seasons.map(s=>s.points))]])+section("Historia sezonów",cards(DB.seasons.slice().reverse().map(s=>'<span class="eyebrow">'+(normalized(s.name).includes("hala")?"HALA":"ORLIK")+'</span><h3>'+seasonLink(s)+'</h3><div class="row"><span>'+e(s.position)+'. miejsce</span><strong>'+e(s.points)+' pkt</strong></div><p>'+e(s.wins+"W "+s.draws+"R "+s.losses+"P • "+s.gf+":"+s.ga+" • "+ppg(s)+" PPG")+'</p>')))+section("Porównanie punktów",barChart(DB.seasons,"points",s=>String(s.points)));}
function seasonPage(id){const s=season(id);if(!s)return empty("Nie znaleziono sezonu.");const games=DB.matches.filter(m=>same(m.sid,s.id));const leaders=s.id==="orlik-2026"?DB.players.filter(p=>p.orlik2026).sort((a,b)=>b.orlik2026.goals-a.orlik2026.goals):s.name==="Hala 2025/2026"?DB.players.filter(p=>p.hala2526).sort((a,b)=>b.hala2526.goals-a.hala2526.goals):[];return headline(s.name,"Sezon Bosch Service Tech-Car • "+e(s.table||"Podlaska Liga Piłkarska"))+metrics([["Pozycja",s.position+"."],["Punkty",s.points],["Bilans",s.wins+"-"+s.draws+"-"+s.losses],["Bramki",s.gf+":"+s.ga],["PPG",ppg(s)],["Czyste konta",s.clean_sheets??"—"]])+section("Przebieg sezonu",'<div class="card">'+matchList(games)+'</div>')+section("Liderzy sezonu",leaders.length?table(["Zawodnik","M","G","A"],leaders.map(p=>{const x=s.id==="orlik-2026"?p.orlik2026:p.hala2526;return[playerLink(p),fmt(x.apps,0),fmt(x.goals,0),fmt(x.assists,0)]})):empty("Pełne rankingi sezonowe nie są dostępne w zachowanym źródle. Nie rekonstruujemy ich z sum całej kariery."))+section("Porównanie z innymi sezonami",barChart(DB.seasons.map(x=>({...x,ppg:x.matches?x.points/x.matches:0})),"ppg",x=>fmt(x.ppg)))+(s.id==="orlik-2026"?'<div class="notice">Orlik 2026: drugie miejsce, 35 punktów, seria 8 zwycięstw na zakończenie. Statystyki graczy pokazują zweryfikowanych liderów, nie pełną kadrę.</div>':"");}
function matchesPage(){return headline("Mecze","Wyniki, protokoły, pojedyncze spotkania i powiązane filmy.")+filterInput("Rywal, wynik lub data")+'<div id="filtered-matches"></div>';}
function matchDetail(id){const m=DB.matches.find(x=>same(x.id,id));if(!m)return empty("Nie znaleziono meczu.");const media=m.videos||[];return headline(m.opponent,m.date+" • "+m.season)+metrics([["Wynik Bosch",m.gf+":"+m.ga],["Rezultat",result(m)],["Do przerwy",m.halftime||"Brak danych"],["Nagrania",media.length]])+'<p>'+href("season/"+encodeURIComponent(m.sid),"← Powrót do sezonu")+'</p>'+section("Dane meczu",'<div class="card"><p>'+e(m.match||"Bosch Service Tech-Car — "+m.opponent)+'</p><p>Źródło: '+(m.event_link?'<a target="_blank" rel="noopener noreferrer" href="'+e(m.event_link)+'">Podlaska Liga Piłkarska ↗</a>':"Archiwum kompendium")+'</p></div>')+section("Nagrania",media.length?cards(media.map(v=>'<div class="video-thumb">▶</div><h3>'+e(v.segment||v.title||"Nagranie")+'</h3><a href="'+e(v.url||"https://www.youtube.com/watch?v="+v.video_id)+'" target="_blank" rel="noopener noreferrer">Oglądaj na YouTube ↗</a>')):empty("Brak przypisanego nagrania. Jeśli pojawi się na monitorowanym kanale, synchronizacja spróbuje je dopasować."));}
function players(){
    const sorting = '<div class="filters"><label>Sortowanie <select id="player-sort" aria-label="Sortuj zawodników"><option value="name">Alfabetycznie A–Z</option><option value="name-desc">Alfabetycznie Z–A</option><option value="apps">Najwięcej występów</option><option value="goals">Najwięcej goli</option><option value="assists">Najwięcej asyst</option><option value="points">Kanadyjka G+A</option><option value="motm">Najwięcej MVP</option><option value="yellow">Żółte kartki</option><option value="red">Czerwone kartki</option></select></label><label>Pokaż <select id="player-stat-filter" aria-label="Filtruj osiągnięcia"><option value="all">Wszyscy z sezonu</option><option value="scored">Z golem</option><option value="assisted">Z asystą</option><option value="motm">Z MVP</option><option value="yellow">Z żółtą kartką</option><option value="red">Z czerwoną kartką</option><option value="verified">Potwierdzone występy</option></select></label></div>';
    return headline("Zawodnicy","Profile, gole, asysty, osiągnięcia i dostępne dane sezonowe.")+filterInput("Szukaj zawodnika")+sorting+'<div id="filtered-players"></div>';
}
function playerDetail(id){const p=DB.players.find(x=>same(x.id,id)||((x.aliases||[]).some(alias=>same(alias,id))));if(!p)return empty("Nie znaleziono zawodnika.");const rows=(p.season_history||[]).map(h=>[e(h.name),e(h.apps??"—"),e(h.goals??"—"),e(h.assists??"—"),h.goals==null||h.assists==null?"—":e(h.goals+h.assists)]);const list=rows.length?table(["Sezon","M","G","A","G+A"],rows):empty("Brak danych sezonowych.");const careerRows=(p.career_totals?.season_rows||[]).map(record=>[e(record.name),e(record.team),e(record.apps??"—"),e(record.goals??"—"),e(record.assists??"—")]);const photos=(DB.media?.subjects||[]).find(x=>x.kind==="players"&&x.id===p.id);const gallery=photos?.photos?.length?section("Zdjęcia PLP",'<div class="grid">'+photos.photos.map(x=>'<a target="_blank" rel="noopener noreferrer" href="'+e(x.url)+'"><img loading="lazy" style="width:100%;max-height:230px;object-fit:contain" src="'+e(x.local?x.local:x.url)+'" alt="'+e(x.alt||p.name)+'"></a>').join("")+'</div>'):"";return headline(p.name,p.status||"Zawodnik Bosch Service Tech-Car")+metrics([["Mecze Boscha",p.apps??(p.orlik2026?.apps!=null?"≥ "+p.orlik2026.apps:"—")],["Gole Boscha",p.goals??(p.orlik2026?.goals!=null?"≥ "+p.orlik2026.goals:"—")],["Asysty Boscha",p.assists??(p.orlik2026?.assists!=null?"≥ "+p.orlik2026.assists:"—")],["MVP Boscha",p.motm??"—"]])+(p.career_totals?section("Cała kariera w PLP",metrics([["Mecze",p.career_totals.apps??"—"],["Gole",p.career_totals.goals??"—"],["Asysty",p.career_totals.assists??"—"],["MVP",p.career_totals.motm??"—"]])):"")+section("Sezony w Bosch Service Tech-Car",list)+(careerRows.length?section("Historia kariery w PLP — wszystkie kluby",table(["Sezon","Klub","M","G","A"],careerRows)):"")+'<div class="notice">„—” oznacza brak szczegółowych statystyk w archiwum, a nie zero. „≥” oznacza potwierdzone minimum z dostępnego sezonu, a nie pełny bilans kariery. Bilans Boscha obejmuje wszystkie dostępne sezony i Superpuchary, łącznie z Orlikiem 2026. Sumy całej kariery obejmują również inne kluby i mogą pochodzić ze starszego zestawienia PLP.</div>'+gallery+(p.peak?section("Najlepszy historyczny sezon",'<div class="card">'+e(p.peak)+'</div>'):"")+(p.profile_url?'<p><a href="'+e(p.profile_url)+'" target="_blank" rel="noopener noreferrer">Profil w PLP ↗</a></p>':"");}
function opponents(){const map=new Map();for(const m of DB.matches){const key=normalized(m.opponent);if(!map.has(key))map.set(key,{name:m.opponent,matches:[],key});map.get(key).matches.push(m);}DB.opponents=[...map.values()].sort((a,b)=>a.name.localeCompare(b.name,"pl"));return headline("Rywale","Bezpośrednie pojedynki z każdą drużyną.")+'<div class="filters"><input id="local-filter" placeholder="Znajdź rywala…"></div><div id="filtered-opponents"></div>';}
function opponentDetail(id){const ms=DB.matches.filter(m=>normalized(m.opponent)===id);if(!ms.length)return empty("Nie znaleziono rywala.");const wins=ms.filter(m=>m.gf>m.ga).length,draws=ms.filter(m=>m.gf===m.ga).length;return headline(ms[0].opponent,"Historia spotkań z Bosch Service Tech-Car")+metrics([["Mecze",ms.length],["Wygrane",wins],["Remisy",draws],["Porażki",ms.length-wins-draws]])+section("Wszystkie pojedynki",'<div class="card">'+matchList(ms)+'</div>');}
function videos(){
    return headline("Wideo","Archiwum filmów i nagrań przypisanych do meczów.")+
        metrics([["Materiały",DB.videos.length],["Powiązane z meczami",DB.videos.filter(video=>video.match_id).length]])+
        '<div class="filters"><input id="local-filter" placeholder="Tytuł, kanał…" aria-label="Szukaj nagrań"><label>Sortuj <select id="video-sort" aria-label="Sortuj filmy"><option value="newest">Najnowsze</option><option value="oldest">Najstarsze</option><option value="title">Tytuł A–Z</option><option value="title-desc">Tytuł Z–A</option><option value="matched">Najpierw powiązane z meczami</option></select></label></div><div id="filtered-videos"></div>'+
        '<div class="notice">Filmy są odtwarzane z YouTube. Daty pochodzą z dostępnych metadanych publikacji, a brak daty trafia na koniec listy.</div>';
}

function sortVideos(items,selectedSort){
    const sorted=items.slice();
    const newest=(first,second)=>String(second.date||"").localeCompare(String(first.date||""))||String(first.title||"").localeCompare(String(second.title||""),"pl");
    const oldest=(first,second)=>{
        if (!first.date) return second.date?1:0;
        if (!second.date) return -1;
        return String(first.date).localeCompare(String(second.date));
    };
    sorted.sort((first,second)=>{
        if(selectedSort==="oldest")return oldest(first,second);
        if(selectedSort==="title")return String(first.title||"").localeCompare(String(second.title||""),"pl");
        if(selectedSort==="title-desc")return String(second.title||"").localeCompare(String(first.title||""),"pl");
        if(selectedSort==="matched")return Number(Boolean(second.match_id))-Number(Boolean(first.match_id))||newest(first,second);
        return newest(first,second);
    });
    return sorted;
}

function records(){
    const seasons=DB.seasons.slice();
    const matches=DB.matches.slice();
    const players=DB.players.slice();
    const sourceNote='<div class="notice">Rankingi obejmują potwierdzone sezonowe dane PLP oraz oznaczone dane z historycznego archiwum Boscha. Historyczne dane nie są kompletne; prowadzący ranking nie musi być definitywnym rekordzistą. Brak danych nie oznacza zera, a goli drużynowych nie wolno przypisywać zawodnikom bez źródła.</div>';
    const measures=[
        ["Strzelcy — gole","goals",player=>player.goals,0],
        ["Asysty","assists",player=>player.assists,0],
        ["Kanadyjka — gole + asysty","points",player=>player.goals!=null&&player.assists!=null?player.goals+player.assists:null,0],
        ["Najwięcej występów","apps",player=>player.apps,0],
        ["MVP / piłkarz meczu","motm",player=>player.motm,0],
        ["Żółte kartki","yellow",player=>player.yellow,0],
        ["Czerwone kartki","red",player=>player.red,0],
        ["Gole na mecz — minimum 5 występów","goals_per_match",player=>player.apps>=5&&player.goals!=null?player.goals/player.apps:null,2],
        ["Asysty na mecz — minimum 5 występów","assists_per_match",player=>player.apps>=5&&player.assists!=null?player.assists/player.apps:null,2],
        ["Kanadyjka na mecz — minimum 5 występów","points_per_match",player=>player.apps>=5&&player.goals!=null&&player.assists!=null?(player.goals+player.assists)/player.apps:null,2],
        ["MVP na mecz — minimum 5 występów","motm_per_match",player=>player.apps>=5&&player.motm!=null?player.motm/player.apps:null,2]
    ];
    const boards=measures.map(([heading,key,getValue,precision])=>{
        const ranked=players.map(player=>({player,value:getValue(player)}))
            .filter(row=>Number.isFinite(row.value)&&row.value>0)
            .sort((a,b)=>b.value-a.value||a.player.name.localeCompare(b.player.name,"pl"))
            .slice(0,10);
        return section(heading,ranked.length?table(["#","Zawodnik","Wynik","Źródło"],ranked.map((row,index)=>[
            e(index+1),playerLink(row.player),fmt(row.value,precision),
            e(row.player.bosch_totals?"Sezony PLP":"Archiwum niepełne")
        ])):empty("Brak statystyk dostępnych dla tej kategorii."));
    }).join("");
    const scoreWins=matches.slice().sort((a,b)=>(b.gf-b.ga)-(a.gf-a.ga)).slice(0,10);
    const offensive=matches.slice().sort((a,b)=>b.gf-a.gf).slice(0,10);
    const goalCoverage=DB.analysis?.player_goal_coverage||[];
    const missing=goalCoverage.reduce((sum,row)=>sum+(row.unattributed_goals||0),0);
    const audit=section("Kontrola kompletności strzelców",'<div class="notice">Różnica między golami drużyny a golami przypisanymi w dostępnych rekordach: '+e(missing)+'. Mogą to być nieopisani strzelcy, gole samobójcze lub brakujące protokoły — bez weryfikacji nie przypisujemy ich nikomu.</div>'+table(["Sezon","Gole drużyny","Przypisane","Niewyjaśnione"],goalCoverage.map(row=>[e(row.season),e(row.team_goals),e(row.attributed_goals),e(row.unattributed_goals)])));
    const seasonal=section("Rekordy sezonowe",table(["Sezon","Miejsce","Punkty","PPG","Bramki","Gole/mecz","Stracone/mecz"],seasons.slice().sort((a,b)=>b.points-a.points).map(seasonRow=>[seasonLink(seasonRow),e(seasonRow.position??"—"),e(seasonRow.points),ppg(seasonRow),e(seasonRow.gf+":"+seasonRow.ga),fmt(seasonRow.gf/seasonRow.matches),fmt(seasonRow.ga/seasonRow.matches)])));
    return headline("Rekordy Boscha","Strzelcy, asysty, kanadyjka, kartki, MVP, występy, skuteczność, mecze i sezony — z kontrolą jakości źródeł.")+
        sourceNote+
        section("Najwyższe zwycięstwa",table(["Data","Rywal","Wynik","Sezon"],scoreWins.map(match=>[e(match.date),matchLink(match),winner(match),e(match.season)])))+
        section("Najwięcej goli Boscha w meczu",table(["Data","Rywal","Wynik","Sezon"],offensive.map(match=>[e(match.date),matchLink(match),winner(match),e(match.season)])))+
        seasonal+boards+audit;
}
function playerRankingStats(player,selectedSeasonId){
    const record=selectedSeasonId?playerSeasonRecord(player,selectedSeasonId):player;
    const goals=record?.goals;
    const assists=record?.assists;
    return {
        apps:record?.apps,
        goals,
        assists,
        points:Number.isFinite(goals)&&Number.isFinite(assists)?goals+assists:null,
        motm:record?.motm,
        yellow:record?.yellow,
        red:record?.red
    };
}
function sortPlayerItems(items,selectedSeasonId){
    const sort=$("player-sort")?.value||"name";
    const filter=$("player-stat-filter")?.value||"all";
    const filtered=items.filter(player=>{
        const stats=playerRankingStats(player,selectedSeasonId);
        if(filter==="scored")return stats.goals>0;
        if(filter==="assisted")return stats.assists>0;
        if(filter==="motm")return stats.motm>0;
        if(filter==="yellow")return stats.yellow>0;
        if(filter==="red")return stats.red>0;
        if(filter==="verified")return Number.isFinite(stats.apps)&&stats.apps>0;
        return true;
    });
    return filtered.sort((first,second)=>{
        const alphabetic=first.name.localeCompare(second.name,"pl",{sensitivity:"base"});
        if(sort==="name-desc")return -alphabetic;
        if(sort==="name")return alphabetic;
        const firstValue=playerRankingStats(first,selectedSeasonId)[sort];
        const secondValue=playerRankingStats(second,selectedSeasonId)[sort];
        return (Number.isFinite(secondValue)?secondValue:-Infinity)-(Number.isFinite(firstValue)?firstValue:-Infinity)||alphabetic;
    });
}
function analysis(){const seasons=DB.seasons.map(s=>({...s,ppg:s.points/s.matches,ga_pg:s.ga/s.matches,gf_pg:s.gf/s.matches}));const promo=DB.analysis?.promotions||[];return headline("Analityka","Głębsze spojrzenie na wyniki, skuteczność, defensywę i awans.")+section("Punkty na mecz",barChart(seasons,"ppg",s=>fmt(s.ppg)))+section("Stracone gole na mecz",barChart(seasons,"ga_pg",s=>fmt(s.ga_pg)))+section("Atak — gole na mecz",barChart(seasons,"gf_pg",s=>fmt(s.gf_pg)))+section("Porównywarka sezonów",'<div class="filters"><select id="compare-a">'+DB.seasons.map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select><select id="compare-b">'+DB.seasons.map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select></div><div id="compare-result"></div>')+section("Benchmark awansu",promo.length?table(["Sezon","Drużyna","Miejsce","PPG"],promo.slice(0,35).map((p,i)=>[e(i>0&&promo[i-1].sid===p.sid?"":p.season||p.season_name),e(p.team_name),e(p.rank),fmt(p.ppg)])):empty("Brak danych benchmarku."))+section("Scouting historyczny",cards((DB.analysis?.scouting||[]).slice(0,13).map(x=>'<h3>'+e(x.name)+'</h3><p><span class="pill">'+e(x.threat_level)+'</span></p><p>'+e(x.summary)+'</p>')))+'<div class="notice">Scouting Orlika 2026 to prognoza sporządzona przed sezonem. Nie jest oceną aktualnej formy. Głębokie statystyki o przebiegu meczu dla Orlika 2026 wymagają pełnych protokołów PLP.</div><p><a href="archive.html#splits">Zobacz pełne archiwum analiz technicznych →</a></p>';}
function compare(){const a=season($("compare-a")?.value),b=season($("compare-b")?.value);if(!a||!b)return;$("compare-result").innerHTML=table(["Wskaźnik",a.name,b.name],[["Punkty",a.points,b.points],["Mecze",a.matches,b.matches],["PPG",ppg(a),ppg(b)],["Gole na mecz",fmt(a.gf/a.matches),fmt(b.gf/b.matches)],["Stracone na mecz",fmt(a.ga/a.matches),fmt(b.ga/b.matches)]].map(row=>row.map(e)));}
function playerSeasonRecord(player, selectedSeasonId) {
    const officialSeason = player.season_stats?.[selectedSeasonId];

    if (officialSeason) {
        return officialSeason;
    }

    return (player.season_history || []).find(record => same(record.sid, selectedSeasonId)) || null;
}

function playerPlayedSeason(player, selectedSeasonId) {
    const seasonRecord = playerSeasonRecord(player, selectedSeasonId);

    return seasonRecord !== null && (seasonRecord.apps == null || Number(seasonRecord.apps) > 0);
}

function playerCard(player, selectedSeasonId) {
    const selectedSeason = selectedSeasonId ? season(selectedSeasonId) : null;
    const seasonRecord = selectedSeasonId ? playerSeasonRecord(player, selectedSeasonId) : null;
    const summary = selectedSeasonId
        ? "M: " + e(seasonRecord?.apps ?? "—") + " / G: " + e(seasonRecord?.goals ?? "—") + " / A: " + e(seasonRecord?.assists ?? "—")
        : player.orlik2026
            ? "Orlik 2026: " + e(player.orlik2026.goals ?? "—") + " G / " + e(player.orlik2026.assists ?? "—") + " A"
            : "Archiwum: " + e(player.goals ?? "—") + " G / " + e(player.assists ?? "—") + " A";

    return '<h3>' + playerLink(player) + '</h3><p>' + e(selectedSeason?.name || player.status) + '</p><div class="small">' + summary + '</div>';
}

function setupList(id, items, renderer, searcher = JSON.stringify, seasonMatcher = null) {
    const input = $("local-filter");
    const seasonSelect = $("season-filter");

    function paint() {
        const query = normalized(input?.value || "");
        const selectedSeasonId = seasonSelect?.value || "";
        const visibleItems = items.filter(item => {
            const matchesSearch = !query || normalized(searcher(item)).includes(query);
            const matchesSeason = !selectedSeasonId || seasonMatcher === null || seasonMatcher(item, selectedSeasonId);

            return matchesSearch && matchesSeason;
        });

        $(id).innerHTML = renderer(visibleItems, selectedSeasonId);
    }

    input?.addEventListener("input", paint);
    seasonSelect?.addEventListener("change", paint);
    paint();
    return paint;
}
function route(){if(!DB)return;const pieces=decodeURIComponent(location.hash.slice(2)||"").split("/");const name=pieces[0]||"",id=pieces.slice(1).join("/");const routes={"":home,seasons,matches:matchesPage,players,opponents,analysis,videos,records};const pages={season:()=>seasonPage(id),match:()=>matchDetail(id),player:()=>playerDetail(id),opponent:()=>opponentDetail(id)};$("app").innerHTML=pages[name]?pages[name]():routes[name]?routes[name]():empty("Nie znaleziono strony.");document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#/"+name||name==="season"&&a.getAttribute("href")==="#/seasons"||name==="player"&&a.getAttribute("href")==="#/players"||name==="match"&&a.getAttribute("href")==="#/matches"||name==="opponent"&&a.getAttribute("href")==="#/opponents"));if(name==="matches")setupList("filtered-matches",DB.matches,items=>'<div class="card">'+matchList(items)+'</div>',m=>[m.opponent,m.date,m.season,m.gf+":"+m.ga].join(" "),(match, selectedSeasonId)=>same(match.sid,selectedSeasonId));if(name==="players"){const repaint=setupList("filtered-players",DB.players,(items,selectedSeasonId)=>cards(sortPlayerItems(items,selectedSeasonId).map(player=>playerCard(player,selectedSeasonId))),player=>player.name,playerPlayedSeason);$("player-sort")?.addEventListener("change",repaint);$("player-stat-filter")?.addEventListener("change",repaint);}if(name==="opponents")setupList("filtered-opponents",DB.opponents,items=>cards(items.map(x=>'<h3>'+href("opponent/"+encodeURIComponent(x.key),x.name)+'</h3><p>'+x.matches.length+' spotkań</p>')),x=>x.name);if(name==="videos"){const repaint=setupList("filtered-videos",DB.videos,items=>cards(sortVideos(items,$("video-sort")?.value||"newest").slice(0,120).map(video=>'<div class="video-thumb">▶</div><h3>'+e(video.title)+'</h3><p>'+e(video.channel||"")+" • "+e(video.date||"")+'</p><p><a href="'+e(video.url)+'" target="_blank" rel="noopener noreferrer">Oglądaj ↗</a>'+(video.match_id?' • '+href("match/"+encodeURIComponent(video.match_id),"Mecz"):"")+'</p>')),video=>video.title+" "+video.channel);$("video-sort")?.addEventListener("change",repaint)};if(name==="analysis"){const selects=[$("compare-a"),$("compare-b")];if(selects[1])selects[1].value=DB.seasons.at(-1).id;for(const x of selects)x?.addEventListener("change",compare);compare();}window.scrollTo(0,0);}
function initSearch(){const dialog=$("search-dialog"),input=$("global-search");function open(){dialog.showModal();input.focus();} $("search-open").addEventListener("click",open);document.addEventListener("keydown",event=>{if(event.key==="/"&&document.activeElement.tagName!=="INPUT"){event.preventDefault();open();}if((event.key==="Escape")&&dialog.open)dialog.close();});input.addEventListener("input",()=>{const q=normalized(input.value);const records=[...DB.players.map(p=>({name:p.name,kind:"Zawodnik",url:"player/"+p.id})),...DB.seasons.map(s=>({name:s.name,kind:"Sezon",url:"season/"+s.id})),...DB.matches.map(m=>({name:m.date+" • "+m.opponent,kind:"Mecz",url:"match/"+m.id})),...[...new Set(DB.matches.map(m=>m.opponent))].map(o=>({name:o,kind:"Rywal",url:"opponent/"+normalized(o)}))];$("search-results").innerHTML=!q?"":records.filter(item=>normalized(item.name).includes(q)).slice(0,22).map(item=>'<a class="list-row" href="#/'+e(item.url)+'"><span>'+e(item.name)+'</span><small>'+e(item.kind)+'</small></a>').join("")||empty("Brak wyników.");$("search-results").querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>dialog.close()));});}
(async function(){const saved=localStorage.getItem("bosch-theme")||"dark";document.documentElement.dataset.theme=saved;$("theme-toggle").addEventListener("click",()=>{const theme=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=theme;localStorage.setItem("bosch-theme",theme);});try{const response=await fetch("assets/data.json",{cache:"no-store"});if(!response.ok)throw Error("HTTP "+response.status);DB=await response.json();initSearch();window.addEventListener("hashchange",route);route();}catch(error){$("app").innerHTML=empty("Nie udało się wczytać danych kompendium: "+error.message);}})();
