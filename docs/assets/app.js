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
const table=(heads,rows,footer=null)=>'<div class="table-card"><table class="table"><thead><tr>'+heads.map(heading=>'<th>'+e(heading)+'</th>').join("")+'</tr></thead><tbody>'+rows.map(columns=>'<tr>'+columns.map(cell=>'<td>'+cell+'</td>').join("")+'</tr>').join("")+'</tbody>'+(footer?'<tfoot><tr>'+footer.map(cell=>'<td>'+cell+'</td>').join("")+'</tr></tfoot>':"")+'</table></div>';
const cards=rows=>'<div class="grid">'+rows.map(row=>'<div class="card">'+row+'</div>').join("")+'</div>';
const empty=message=>'<div class="notice">'+e(message)+'</div>';
const filterInput=(placeholder="Szukaj…")=>'<div class="filters"><input id="local-filter" placeholder="'+e(placeholder)+'" aria-label="Filtruj wyniki"><select id="season-filter"><option value="">Wszystkie sezony</option>'+DB.seasons.slice().reverse().map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select></div>';
const seasonLink=s=>href("season/"+encodeURIComponent(s.id),s.name);
const playerLink=p=>href("player/"+encodeURIComponent(p.id),p.name);
const matchLink=m=>href("match/"+encodeURIComponent(m.id),m.opponent);
const winner=m=>'<strong class="'+resultClass(m)+'">'+e(m.gf+":"+m.ga)+'</strong>';
function matchList(matches,limit=0){const list=matches.slice().sort((a,b)=>b.date.localeCompare(a.date));return list.slice(0,limit||list.length).map(m=>'<div class="list-row"><div><div class="small">'+e(m.date)+' • '+href("season/"+encodeURIComponent(m.sid),m.season)+'</div>'+matchLink(m)+'</div>'+winner(m)+'</div>').join("")||empty("Brak spotkań w wybranym zakresie.")}
function barChart(rows,key,label){const max=Math.max(1,...rows.map(x=>Number(x[key])||0));return '<div class="card bar-chart">'+rows.map(s=>'<div class="bar-row"><span>'+e(s.name)+'</span><div class="bar-track"><span style="width:'+Math.max(0,Math.min(100,(Number(s[key])||0)/max*100))+'%"></span></div><b>'+e(label?label(s):fmt(s[key]))+'</b></div>').join("")+'</div>';}
function goalMinutes(scorer){
    if(scorer.minute_uncertain){
        return "Minuta nieczytelna w PLP";
    }

    return scorer.minutes.length?scorer.minutes.map(minute=>e(minute)+"′").join(", "):"—";
}

function goalScorerLinks(match,maximum=0){
    if(!match.goal_protocol?.verified)return "Oczekuje na weryfikację protokołu PLP";
    const scorers=match.goal_protocol?.scorers||[];
    const chosen=maximum?scorers.slice(0,maximum):scorers;
    const labels=chosen.map(scorer=>href("player/"+encodeURIComponent(scorer.player_id),scorer.name)+(scorer.goals>1?" ×"+e(scorer.goals):""));

    if(scorers.length>chosen.length){
        labels.push("+"+(scorers.length-chosen.length));
    }

    return labels.join(" · ")||(match.goal_protocol?.own_goals?"Gol samobójczy rywala":"Brak goli zawodników");
}

function goalMatchTable(match){
    const protocol=match.goal_protocol;

    if(!protocol){
        return empty("Brak dostępnego protokołu.");
    }

    const rows=protocol.scorers.map(scorer=>[
        href("player/"+encodeURIComponent(scorer.player_id),scorer.name),
        e(scorer.goals),
        goalMinutes(scorer),
        '<a target="_blank" rel="noopener noreferrer" href="'+e(protocol.source_url)+'">Protokół PLP ↗</a>'
    ]);
    const own=protocol.own_goals?'<div class="notice">Gole samobójcze rywali: <strong>'+e(protocol.own_goals)+'</strong>.</div>':"";
    const ownConceded=protocol.own_goals_conceded_scorers?.length
        ? '<div class="notice">Samobóje zawodników Boscha na korzyść rywali: '+
            protocol.own_goals_conceded_scorers.map(item=>href("player/"+encodeURIComponent(item.player_id),item.name)+(item.minutes?.length?" ("+item.minutes.map(minute=>e(minute)+"′").join(", ")+")":"")).join(", ")+
            '</div>'
        : "";
    const administrative=protocol.administrative_goals?'<div class="notice">Gole przyznane administracyjnie: <strong>'+e(protocol.administrative_goals)+'</strong>. Nie są dopisywane zawodnikom.</div>':"";
    const minutes=protocol.minute_uncertainties?'<div class="notice">Jedno oznaczenie gola PLP nie ma czytelnej minuty. Nazwisko strzelca pozostaje potwierdzone.</div>':"";

    return (rows.length?table(["Zawodnik","Gole","Minuty","Źródło"],rows):empty("Brak indywidualnych goli Boscha."))+own+ownConceded+administrative+minutes;
}

function goalMatchRows(matches){
    return matches.map(match=>{
        const protocol=match.goal_protocol||{scorers:[],own_goals:0,administrative_goals:0};

        return [
            e(match.date),
            matchLink(match),
            winner(match),
            e(match.season),
            goalScorerLinks(match),
            e(protocol.own_goals||0),
            e(protocol.own_goals_conceded||0),
            e(protocol.administrative_goals||0),
            '<a href="'+e(match.event_link)+'" target="_blank" rel="noopener noreferrer">PLP ↗</a>'
        ];
    });
}

function goalsArchive(){
    const coverage=DB.analysis?.player_goal_coverage||[];
    const sum=field=>coverage.reduce((total,record)=>total+(record[field]||0),0);

    return headline("Gole i protokoły PLP","Zweryfikowane protokoły i spotkania oczekujące na źródłowy zapis strzelców.")+
        metrics([["Mecze",DB.matches.length],["Gole drużyny",sum("team_goals")],["Gole zawodników",sum("attributed_goals")],["Samobóje rywali",sum("opponent_own_goals")],["Samobóje Boscha",DB.analysis?.match_protocol_audit?.total_own_goals_conceded||0],["Administracyjne",sum("administrative_goals")]])+
        '<div class="notice">Każdy mecz posiada oryginalny link PLP. Jedna minuta gola w spotkaniu z VESTA jest nieczytelna w źródle.</div>'+
        filterInput("Data, rywal, zawodnik lub wynik…")+
        '<div id="filtered-goals"></div>';
}

function home(){const latest=DB.seasons.at(-1),recent=DB.matches.filter(m=>same(m.sid,latest.id));const leaders=DB.players.map(player=>({player,stats:player.season_stats?.[latest.id]||null})).filter(row=>seasonPointsComplete(row.stats)).sort((a,b)=>(b.stats.goals+b.stats.assists)-(a.stats.goals+a.stats.assists)||b.stats.goals-a.stats.goals||a.player.name.localeCompare(b.player.name,"pl")).slice(0,4);return headline("Wszystko o Bosch w jednym miejscu","Wyniki, historia sezonów, statystyki zawodników, mecze i nagrania. Bez przewijania gigantycznego raportu.")+metrics([["Ostatni sezon",latest.name],["Miejsce",latest.position+"."],["Punkty",latest.points],["Bramki",latest.gf+":"+latest.ga]])+'<div class="columns">'+section("Ostatnie wyniki",'<div class="card">'+matchList(recent,5)+'</div><p>'+href("season/"+latest.id,"Otwórz pełny sezon →")+'</p>')+section("Liderzy "+latest.name,'<div class="card">'+leaders.map(({player,stats})=>'<div class="list-row">'+playerLink(player)+'<strong>'+e(stats.goals+stats.assists)+' G+A</strong></div>').join("")+'</div><p>'+href("players","Wszyscy zawodnicy →")+'</p>')+'</div>'+section("Odkrywaj kompendium",cards([["Sezony","season/"+latest.id,"Zobacz analizę sezonu "+latest.name],["Wszystkie mecze","matches","Znajdź wybrane spotkanie i nagrania"],["Gole i protokoły","goals",DB.matches.length+" meczów, strzelcy, minuty oraz samobóje"],["Rekordy","records","Najlepsze wyniki drużyny"],["Analityka","analysis","Zaawansowane porównania i benchmarking"]].map(([title,route,desc])=>'<h3>'+href(route,title+" →")+'</h3><p>'+e(desc)+'</p>')));}
function seasons(){return headline("Sezony","Wszystkie rozgrywki Boscha i porównanie ich wyników.")+metrics([["Sezonów",DB.seasons.length],["Łącznie spotkań",DB.seasons.reduce((n,s)=>n+s.matches,0)],["Najwięcej punktów",Math.max(...DB.seasons.map(s=>s.points))]])+section("Historia sezonów",cards(DB.seasons.slice().reverse().map(s=>'<span class="eyebrow">'+(normalized(s.name).includes("hala")?"HALA":"ORLIK")+'</span><h3>'+seasonLink(s)+'</h3><div class="row"><span>'+e(s.position)+'. miejsce</span><strong>'+e(s.points)+' pkt</strong></div><p>'+e(s.wins+"W "+s.draws+"R "+s.losses+"P • "+s.gf+":"+s.ga+" • "+ppg(s)+" PPG")+'</p>')))+section("Porównanie punktów",barChart(DB.seasons,"points",s=>String(s.points)));}
function seasonPointsComplete(stats){
    return Number.isInteger(stats?.goals)&&Number.isInteger(stats?.assists)&&!stats.stats_minimum&&stats.origin!=="plp_match_minimum";
}
function seasonPage(id){
    const selectedSeason=season(id);

    if(!selectedSeason){
        return empty("Nie znaleziono sezonu.");
    }

    const matches=DB.matches.filter(match=>same(match.sid,selectedSeason.id));
    const leaders=DB.players.map(player=>({
        player,
        stats:player.season_stats?.[selectedSeason.id] || (selectedSeason.id==="orlik-2026"?player.orlik2026:null) || (selectedSeason.id==="146"?player.hala2526:null)
    })).filter(entry=>entry.stats&&(
        Number(entry.stats.apps)>0||
        (entry.stats.apps==null&&(
            (Number.isInteger(entry.stats.goals)&&entry.stats.goals>0)||
            (Number.isInteger(entry.stats.assists)&&entry.stats.assists>0)
        ))
    ))
        .sort((first,second)=>{
            const firstPoints=Number(first.stats.goals||0)+Number(first.stats.assists||0);
            const secondPoints=Number(second.stats.goals||0)+Number(second.stats.assists||0);

            return secondPoints-firstPoints || Number(second.stats.goals||0)-Number(first.stats.goals||0) || first.player.name.localeCompare(second.player.name,"pl");
        });
    const completeLeaders=leaders.filter(({stats})=>seasonPointsComplete(stats));
    const partialLeaders=leaders.filter(({stats})=>!seasonPointsComplete(stats));
    const leadersTable=completeLeaders.length?table(["Zawodnik","M","G","A","G+A","Źródło"],completeLeaders.map(({player,stats})=>[
        playerLink(player),
        e(stats.apps??"—"),
        e(stats.goals??"—"),
        e(stats.assists??"—"),
        Number.isInteger(stats.goals)&&Number.isInteger(stats.assists)?e(stats.goals+stats.assists):"—",
        e(seasonStatisticsSource(stats))
    ])):empty("Brak potwierdzonych statystyk indywidualnych dla tego sezonu.");
    return headline(selectedSeason.name,"Sezon Bosch Service Tech-Car • "+e(selectedSeason.table||"Podlaska Liga Piłkarska"))+
        metrics([["Pozycja",selectedSeason.position+"."],["Punkty",selectedSeason.points],["Bilans",selectedSeason.wins+"-"+selectedSeason.draws+"-"+selectedSeason.losses],["Bramki",selectedSeason.gf+":"+selectedSeason.ga],["PPG",ppg(selectedSeason)],["Czyste konta",selectedSeason.clean_sheets??"—"]])+
        section("Przebieg sezonu",'<div class="card">'+matchList(matches)+'</div>')+
        section("Liderzy sezonu — kanadyjka (G+A)",leadersTable)+
        (partialLeaders.length?section("Zawodnicy z niepełnymi statystykami — bez miejsca w rankingu",
            table(["Zawodnik","M","G","A","Powód"],partialLeaders.map(({player,stats})=>[
                playerLink(player),e(stats.apps??"—"),e(stats.goals??"—"),
                e(stats.assists??"—"),"Brak pełnej liczby goli lub asyst w oficjalnym archiwum"
            ]))):"")+
        section("Gole i protokoły wszystkich meczów",table(["Data","Mecz","Wynik","Sezon","Strzelcy","Samobóje rywali","Samobóje Boscha","Administracyjne","PLP"],goalMatchRows(matches)))+
        section("Porównanie z innymi sezonami",barChart(DB.seasons.map(row=>({...row,ppg:row.matches?row.points/row.matches:0})),"ppg",row=>fmt(row.ppg)))+
        (selectedSeason.id==="orlik-2026"?'<div class="notice">Orlik 2026: drugie miejsce, 35 punktów, seria 8 zwycięstw na zakończenie. Gole indywidualne zweryfikowano we wszystkich 15 oryginalnych protokołach tego sezonu.</div>':"");
}
function matchesPage(){return headline("Mecze","Wyniki, protokoły, pojedyncze spotkania i powiązane filmy.")+filterInput("Rywal, wynik lub data")+'<div id="filtered-matches"></div>';}
function matchDetail(id){
    const match=DB.matches.find(record=>same(record.id,id));

    if(!match){
        return empty("Nie znaleziono meczu.");
    }

    const protocol=match.goal_protocol||{};
    const halves=splitMatchHalves(match);
    const media=match.videos||[];

    return headline(match.opponent,match.date+" • "+match.season)+
        metrics([["Wynik Boscha",match.gf+":"+match.ga],["Rezultat",result(match)],["Gole zawodników",protocol.player_goals??"—"],["Samobóje rywali",protocol.own_goals??"—"],["Samobóje Boscha",protocol.own_goals_conceded??"—"],["Administracyjne",protocol.administrative_goals??"—"],["Nagrania",media.length],["Do przerwy",halves?halves.first.gf+":"+halves.first.ga:"—"],["II połowa",halves?halves.second.gf+":"+halves.second.ga:"—"]])+
        '<p>'+href("season/"+encodeURIComponent(match.sid),"← Powrót do sezonu")+' · '+href("goals","Wszystkie protokoły →")+'</p>'+
        section("Bramki, strzelcy i minuty",goalMatchTable(match))+
        section("Dane meczu",'<div class="card"><p>'+e(match.match||"Bosch Service Tech-Car — "+match.opponent)+'</p><p>Źródło: <a href="'+e(match.event_link)+'" target="_blank" rel="noopener noreferrer">Oficjalny protokół PLP ↗</a></p></div>')+
        matchBoxScore(match)+
        section("Nagrania",media.length?cards(media.map(video=>'<div class="video-thumb">▶</div><h3>'+e(video.segment||video.title||"Nagranie")+'</h3><a href="'+e(video.url||"https://www.youtube.com/watch?v="+video.video_id)+'" target="_blank" rel="noopener noreferrer">Oglądaj na YouTube ↗</a>')):empty("Brak przypisanego nagrania."));
}
function verifiedPlayerName(entry){
    const known=DB.players.find(player=>same(player.id,entry.player_id));
    return known?playerLink(known):e(entry.name)+" <small>(niezidentyfikowany profil)</small>";
}
function matchBoxScore(match){
    const entries=match.player_performance||[];
    if(!entries.length)return section("Skład i statystyki zawodników",empty("Brak kompletnego protokołu zawodników."));
    const rows=entries.slice().sort((a,b)=>a.name.localeCompare(b.name,"pl")).map(entry=>[
        verifiedPlayerName(entry),e(entry.appearance),e(entry.goals??"—"),e(entry.assists??"—"),
        e(entry.motm??"—"),e(entry.yellow??"—"),e(entry.red??"—"),e(entry.second_yellow??"—")
    ]);
    const source=match.player_performance_source||match.event_link;
    return section("Oficjalny skład i statystyki meczu",
        '<p>Każdy wiersz pochodzi z tabeli PLP. Brak przypisanego profilu nie oznacza braku występu. <a target="_blank" rel="noopener noreferrer" href="'+e(source)+'">Zweryfikuj protokół ↗</a></p>'+
        table(["Zawodnik","M","G","A","MVP","ŻK","CK bezp.","Wykl. 2ŻK"],rows));
}
function playerMatchTimeline(player){
    const rows=DB.matches.flatMap(match=>(match.player_performance||[])
        .filter(entry=>same(entry.player_id,player.id))
        .map(entry=>[e(match.date),href("season/"+encodeURIComponent(match.sid),match.season),
            href("match/"+encodeURIComponent(match.id),match.opponent),
            e(match.gf+":"+match.ga),e(entry.goals??"—"),e(entry.assists??"—"),
            e(entry.motm??"—"),e(entry.yellow??"—"),e(entry.red??"—"),e(entry.second_yellow??"—"),
            '<a target="_blank" rel="noopener noreferrer" href="'+e(match.player_performance_source||match.event_link)+'">PLP ↗</a>']));
    rows.reverse();
    return section("Występy mecz po meczu — protokoły PLP",
        rows.length?table(["Data","Sezon","Rywal","Wynik","G","A","MVP","ŻK","CK bezp.","Wykl. 2ŻK","Źródło"],rows)
          :empty("Brak zidentyfikowanych występów w zachowanym archiwum meczowym."));
}
function playerComparison(){
    const options=DB.players.slice().sort((a,b)=>a.name.localeCompare(b.name,"pl"))
        .map(player=>'<option value="'+e(player.id)+'">'+e(player.name)+'</option>').join("");
    return headline("Porównywarka zawodników","Porównaj osiągnięcia Boscha — oddzielnie od kariery w innych klubach.")+
        '<div class="filters"><label>Pierwszy zawodnik <select id="compare-player-a">'+options+'</select></label>'+
        '<label>Drugi zawodnik <select id="compare-player-b">'+options+'</select></label>'+
        '<label>Sezon <select id="compare-player-season"><option value="">Cały Bosch</option>'+
        DB.seasons.map(row=>'<option value="'+e(row.id)+'">'+e(row.name)+'</option>').join("")+
        '</select></label></div><div id="compare-player-result"></div>';
}
function updatePlayerComparison(){
    const p1=DB.players.find(p=>same(p.id,$("compare-player-a")?.value));
    const p2=DB.players.find(p=>same(p.id,$("compare-player-b")?.value));
    const sid=$("compare-player-season")?.value;
    if(!p1||!p2)return;
    const read=(player,field)=>sid?playerSeasonRecord(player,sid)?.[field]:player[field];
    const minimum=player=>sid?
        Boolean(playerSeasonRecord(player,sid)?.stats_minimum)||playerSeasonRecord(player,sid)?.origin==="plp_match_minimum":
        Boolean(player.stats_minimum)||!player.bosch_totals;
    const display=(player,field)=>{
        const value=read(player,field);
        return Number.isInteger(value)&&minimum(player)?"≥ "+value:value??"—";
    };
    const stats=[["Występy","apps"],["Gole","goals"],["Asysty","assists"],
        ["MVP","motm"],["Żółte kartki","yellow"],["Bezpośrednie czerwone","red"]];
    const rows=stats.map(([name,field])=>[e(name),e(display(p1,field)),e(display(p2,field))]);
    const gpa=player=>{
        const appearances=read(player,"apps");
        const goals=read(player,"goals");
        const assists=read(player,"assists");
        return !minimum(player)&&Number.isInteger(appearances)&&appearances>0&&Number.isInteger(goals)&&Number.isInteger(assists)?
            fmt((goals+assists)/appearances):"—";
    };
    rows.push(["G+A / mecz",gpa(p1),gpa(p2)]);
    $("compare-player-result").innerHTML=table(["Wskaźnik",p1.name,p2.name],rows)+
        '<p class="small">„—” oznacza brak danych, „≥” — udokumentowane minimum. Wskaźnik G+A / mecz wymaga pełnego bilansu. Źródła znajdziesz w profilach obu zawodników.</p>'+
        '<p>'+playerLink(p1)+' · '+playerLink(p2)+'</p>';
}
function dataQuality(){
    const players=DB.players;
    const noPhoto=new Set(players.filter(player=>!(DB.media?.subjects||[]).some(subject=>
        subject.kind==="players"&&same(subject.id,player.id)&&subject.photos?.length)).map(p=>p.id));
    const unknown=DB.analysis?.match_player_backfill?.unmatched_player_ids||[];
    const unresolved=players.filter(player=>(player.season_coverage?.partial||false)||!player.career_totals||noPhoto.has(player.id));
    const rows=unresolved.map(player=>[
        playerLink(player),e(player.season_coverage?.partial?"Niepełny podział":"—"),
        e(player.career_totals?"OK":"Brak"),e(noPhoto.has(player.id)?"Brak":"OK")
    ]);
    return headline("Jakość i źródła danych","Przejrzysty stan archiwum i wymagające weryfikacji elementy.")+
        metrics([["Mecze",DB.matches.length],["Protokoły",DB.matches.filter(m=>m.goal_protocol?.verified).length],
        ["Zawodnicy",players.length],["Niezidentyfikowane ID",unknown.length],
        ["Brak zdjęcia",noPhoto.size],["Brak pełnej kariery",players.filter(p=>!p.career_totals).length],["Mecze bez nagrania",DB.matches.filter(m=>(m.videos||[]).length===0).length],["Filmy bez przypisania",DB.videos.filter(v=>!v.match_id).length]])+
        section("Kwestie do uzupełnienia",table(["Zawodnik","Sezony","Kariera","Zdjęcia"],rows))+
        section("Nierozpoznane identyfikatory z meczów",
            table(["ID PLP","Zapisane protokoły"],unknown.map(id=>[e(id),e(DB.matches.filter(m=>
            (m.player_performance||[]).some(row=>same(row.player_id,id))).length)])))+
        '<p><a download href="downloads/bosch-kompendium.xlsx">Pobierz pełne kompendium XLSX — zawodnicy, mecze, gole, źródła i braki ↧</a></p>'+
        '<p><a href="https://github.com/paweleq1994/bosch-analiza/blob/main/reports/source-reconciliation.md" target="_blank" rel="noopener noreferrer">Różnice oficjalnych źródeł PLP — zawodnik po zawodniku ↗</a></p>'+

        '<p><a href="https://github.com/paweleq1994/bosch-analiza/blob/main/reports/video-coverage.md" target="_blank" rel="noopener noreferrer">Audyt znanych nagrań i meczów bez filmu ↗</a></p>'+
        '<p><a href="https://github.com/paweleq1994/bosch-analiza/blob/main/reports/video-goal-review-queue.md" target="_blank" rel="noopener noreferrer">Gole wymagające potwierdzenia czasu YouTube ↗</a></p>'+
        '<p><a target="_blank" rel="noopener noreferrer" href="https://github.com/paweleq1994/bosch-analiza/blob/main/reports/player-source-reconciliation.md">Porównanie statystyk z oficjalnymi protokołami ↗</a></p>';
}
function players(){
    const sorting = '<div class="filters"><label>Sortowanie <select id="player-sort" aria-label="Sortuj zawodników"><option value="name">Alfabetycznie A–Z</option><option value="name-desc">Alfabetycznie Z–A</option><option value="apps">Najwięcej występów</option><option value="goals">Najwięcej goli</option><option value="assists">Najwięcej asyst</option><option value="points">Kanadyjka G+A</option><option value="motm">Najwięcej MVP</option><option value="yellow">Żółte kartki</option><option value="red">Bezpośrednie czerwone</option></select></label><label>Pokaż <select id="player-stat-filter" aria-label="Filtruj osiągnięcia"><option value="all">Wszyscy z sezonu</option><option value="scored">Z golem</option><option value="assisted">Z asystą</option><option value="motm">Z MVP</option><option value="yellow">Z żółtą kartką</option><option value="red">Z bezpośrednią czerwoną</option><option value="verified">Potwierdzone występy</option></select></label></div>';
    return headline("Zawodnicy","Profile, gole, asysty, osiągnięcia i dostępne dane sezonowe.")+filterInput("Szukaj zawodnika")+sorting+'<div id="filtered-players"></div>';
}
function seasonStatisticsSource(record){
    if(record?.origin==="plp_archived_public_season"){
        return "Archiwalny profil PLP (Internet Archive)";
    }
    if(record?.origin==="plp_archived_season"){
        return "Tabela PLP — archiwum";
    }

    if(record?.origin==="archived_peak"){
        return "Archiwum Boscha — najlepszy sezon";
    }

    if(record?.origin==="participation_only"){
        return "Potwierdzony udział, brak statystyk";
    }

    if(record?.origin==="plp_match_protocols"){
        return "Oficjalny protokół PLP — strzelcy i minuty";
    }

    if(record?.origin==="plp_confirmed_identity_merge"){
        return "PLP — połączone historyczne profile tej samej osoby";
    }

    if(record?.origin==="plp_match_minimum"){
        return "Oficjalny protokół PLP — potwierdzone minimum";
    }

    if(record?.origin==="plp_public_season"){
        return "PLP — oficjalny profil sezonowy";
    }

    if(record?.origin==="PLP public all-career table"){
        return "Tabela kariery PLP";
    }

    return "PLP — statystyki sezonowe";
}

function playerTrendRows(player){
    return (player.season_history||[]).filter(record=>[
        "apps","goals","assists","motm"
    ].some(field=>Number.isInteger(record[field]))).map(record=>({
        name:record.name,
        apps:record.apps,
        goals:record.goals,
        assists:record.assists,
        motm:record.motm,
        rate:Number.isInteger(record.apps)&&record.apps>0&&
            Number.isInteger(record.goals)&&Number.isInteger(record.assists)
            ?(record.goals+record.assists)/record.apps:null,
        source:seasonStatisticsSource(record)
    }));
}
function playerTrendSection(player){
    const data=playerTrendRows(player);
    if(!data.length)return section("Rozwój zawodnika sezon po sezonie",
        empty("Brak wystarczających źródłowych statystyk do przedstawienia trendu."));
    const exact=data.filter(record=>Number.isFinite(record.rate));
    const best=exact.slice().sort((a,b)=>b.rate-a.rate)[0];
    const trendTable=table(["Sezon","M","G","A","G+A / mecz","Źródło"],data.map(row=>[
        e(row.name),e(row.apps??"—"),e(row.goals??"—"),e(row.assists??"—"),
        row.rate===null?"—":fmt(row.rate,2),e(row.source)
    ]));
    return section("Rozwój zawodnika sezon po sezonie",
        (best?metrics([["Najwydajniejszy sezon G+A / mecz",best.name],
            ["Średnia G+A / mecz w tym sezonie",fmt(best.rate,2)]])
            :'<div class="notice">Brak sezonu z pełnym bilansem G+A i meczów.</div>')+
        section("Bramki (tylko potwierdzone sezony)",
            barChart(data.filter(row=>Number.isInteger(row.goals)),"goals",row=>String(row.goals)))+
        section("Asysty (tylko potwierdzone sezony)",
            barChart(data.filter(row=>Number.isInteger(row.assists)),"assists",row=>String(row.assists)))+
        trendTable+
        '<div class="notice">Brak danych nie oznacza 0. Nie sumujemy historycznych wartości minimalnych z pełnym bilansem PLP.</div>'
    );
}
function officialSourceLinks(urls,label){
    const unique=[...new Set(urls.filter(url=>/^https:\/\/podlaskaliga\.pl\//.test(url||"")))];
    if(!unique.length)return e("Brak publicznego źródła statystycznego");
    const refs=unique.slice(0,3).map((url,index)=>
        '<a target="_blank" rel="noopener noreferrer" href="'+e(url)+'">'+e(label)+" "+(index+1)+" ↗</a>"
    );
    if(unique.length>3)refs.push(e("+"+(unique.length-3)+" kolejne w historii meczów"));
    return refs.join(" · ");
}
function playerProvenanceSection(player){
    const career=player.career_totals||null;
    const careerUrl=career?.source_url||player.profile_url||"";
    const fullHistory=Boolean(player.bosch_totals)&&!player.stats_minimum;
    const metrics=[
        ["Występy","apps"],["Gole","goals"],["Asysty","assists"],
        ["MVP","motm"],["Żółte kartki","yellow"],["Bezpośrednie czerwone","red"]
    ];
    const rows=metrics.map(([name,field])=>{
        const boschValue=player[field];
        const careerValue=career?.[field];
        const boschStatus=Number.isInteger(boschValue)
            ?(fullHistory?"Bilans sezonów PLP":"Źródłowo potwierdzone minimum / archiwum")
            :"Brak potwierdzonej wartości";
        const careerStatus=Number.isInteger(careerValue)
            ?(career?.public_season_rows?.length?"Oficjalny HTML wszystkich rozgrywek":"PLP API")
            :"Brak pełnego publicznego bilansu";
        return [
            e(name),Number.isInteger(boschValue)?e(boschValue):"—",
            e(boschStatus),
            Number.isInteger(careerValue)?e(careerValue):"—",
            e(careerStatus)
        ];
    });
    return section("Pochodzenie każdej statystyki",
        '<div class="notice">Bosch to mecze naszej drużyny, a pełna kariera PLP może obejmować inne kluby i Superpuchary. Te kolumny nie muszą być równe. Znak „—” oznacza brak źródła, nie zero.</div>'+
        '<p>'+ (careerUrl?'<a target="_blank" rel="noopener noreferrer" href="'+e(careerUrl)+'">Oficjalny profil i kariera PLP ↗</a>':e("Brak pełnego publicznego bilansu"))+
        '. Źródła pojedynczych występów znajdują się poniżej, w historii protokołów.</p>'+
        table(["Miara","Bosch","Pewność danych","PLP cała kariera","Źródło kariery"],rows)+
        '<p class="small">ŻK to liczba żółtych kartek. Bezpośrednie czerwone zachowują zapis PLP. Wykluczenia po dwóch żółtych są wykazywane oddzielnie w protokołach: '+e(player.second_yellow||0)+' w zachowanym archiwum ligowym.</p>');
}
function verifiedVideoMinuteLink(playerId,matchId,minute){
    const cues=DB.analysis?.verified_goal_video_cues||[];
    const found=cues.find(row=>same(row.match_id,matchId)&&
        same(row.player_id,playerId)&&String(row.minute)===String(minute));
    if(!found)return e(minute)+"′";
    return '<a target="_blank" rel="noopener noreferrer" href="'+e(found.url)+'" title="Potwierdzony moment gola wideo">'+e(minute)+"′ ▶ YouTube</a>";
}
function playerDetail(id){
    const player=DB.players.find(candidate=>same(candidate.id,id)||(candidate.aliases||[]).some(alias=>same(alias,id)));

    if(!player){
        return empty("Nie znaleziono zawodnika.");
    }

    const seasonRows=(player.season_history||[]).map(record=>[
        e(record.name),
        e(record.apps??"—"),
        record.origin==="plp_match_minimum"&&Number.isInteger(record.goals)?"≥ "+e(record.goals):e(record.goals??"—"),
        e(record.assists??"—"),
        Number.isInteger(record.goals)&&Number.isInteger(record.assists)?e(record.goals+record.assists):"—",
        e(record.motm??"—"),
        e(record.yellow??"—"),
        e(record.red??"—"),
        record.source_url?'<a target="_blank" rel="noopener noreferrer" href="'+e(record.source_url)+'">'+e(seasonStatisticsSource(record))+' ↗</a>':e(seasonStatisticsSource(record))
    ]);
    const summaryRow=[
        '<strong>Łącznie Bosch</strong>',
        '<strong>'+e(player.apps??"—")+'</strong>',
        '<strong>'+e(player.goals??"—")+'</strong>',
        '<strong>'+e(player.assists??"—")+'</strong>',
        '<strong>'+(Number.isInteger(player.goals)&&Number.isInteger(player.assists)?e(player.goals+player.assists):"—")+'</strong>',
        e(player.motm??"—"),
        e(player.yellow??"—"),
        e(player.red??"—"),
        e(player.bosch_totals?"PLP — pełny bilans":"Archiwalny bilans Bosch")
    ];
    const seasonTable=seasonRows.length
        ? table(["Sezon","M","G","A","G+A","MVP","ŻK","CK bezp.","Źródło"],seasonRows,summaryRow)
        : empty("Brak szczegółowych danych sezonowych.");
    const unassigned=player.season_coverage?.unassigned||{};
    const remainingTotals=[
        ["meczów",unassigned.apps],
        ["goli",unassigned.goals],
        ["asyst",unassigned.assists]
    ].filter(([,value])=>Number.isInteger(value)&&value>0);
    const remainingNote=remainingTotals.length
        ? '<div class="notice">Niepełny podział na sezony: '+remainingTotals.map(([label,value])=>e(value)+" "+e(label)).join(", ")+'. Wiersz „Łącznie Bosch” pochodzi z historycznego bilansu zawodnika i nie jest sumą wyświetlonych sezonów. Nie przypisujemy brakujących statystyk do sezonów bez potwierdzenia.</div>'
        : "";
    const careerRows=(player.career_totals?.season_rows||[]).map(record=>[
        e(record.name),
        e(record.team),
        e(record.apps??"—"),
        e(record.goals??"—"),
        e(record.assists??"—")
    ]);
    const publicCareerRows=(player.career_totals?.public_season_rows||[]).map(record=>[
        e(record.name),
        e(record.apps),
        e(record.goals),
        e(record.assists),
        e(record.motm),
        e(record.yellow),
        e(record.red)
    ]);
    const publicCareerSection=publicCareerRows.length
        ? section("Oficjalna tabela całej kariery PLP — komplet rozgrywek",
            '<p>Źródło: <a target="_blank" rel="noopener noreferrer" href="'+e(player.career_totals.source_url)+'">Profil PLP ↗</a>. Obejmuje wszystkie sezony oraz Superpuchary — niezależnie od klubów.</p>'+
            table(["Rozgrywki","M","G","A","MVP","ŻK","CK bezp."],publicCareerRows))
        : "";
    const matchesWithGoals=(player.goal_matches||[]).map(entry=>[
        e(entry.date),
        href("match/"+encodeURIComponent(entry.match_id),entry.opponent),
        e(entry.score),
        e(entry.goals),
        entry.minute_uncertain?"Minuta nieczytelna w PLP":entry.minutes.map(minute=>verifiedVideoMinuteLink(player.id,entry.match_id,minute)).join(", "),
        '<a target="_blank" rel="noopener noreferrer" href="'+e(entry.source_url)+'">Protokół ↗</a>'
    ]);
    const scoredMatchSection=section(
        "Gole mecz po meczu — oficjalne protokoły",
        matchesWithGoals.length
            ? table(["Data","Rywal","Wynik","Gole","Minuty","PLP"],matchesWithGoals)
            : empty("Brak indywidualnych goli w przeanalizowanych meczach ligowych.")
    );
    const ownGoals=player.own_goal_matches||[];
    const ownGoalHistory=ownGoals.length?section("Samobóje w barwach Boscha",
        '<div class="notice">Gole samobójcze liczą się rywalowi, nie zawodnikowi Boscha.</div>'+
        table(["Data","Przeciwnik","Samobóje","Protokół"],ownGoals.map(entry=>[
            e(entry.date),
            href("match/"+encodeURIComponent(entry.match_id),entry.opponent),
            e(entry.goals),
            '<a target="_blank" rel="noopener noreferrer" href="'+e(entry.source_url)+'">PLP ↗</a>'
        ]))
    ):"";
    const combinedProfileLinks=(player.alternate_profile_urls||[]).map(url=>
        '<a target="_blank" rel="noopener noreferrer" href="'+e(url)+'">'+e(url)+'</a>'
    );
    const profileMergeNote=combinedProfileLinks.length
        ? section("Historyczne profile PLP tej samej osoby",
            '<div class="notice">Dwa źródłowe profile PLP zostały scalone, a poprzednie adresy działają jako aliasy. '+combinedProfileLinks.join(" • ")+'</div>'
        )
        : "";
    const photos=(DB.media?.subjects||[]).find(subject=>subject.kind==="players"&&subject.id===player.id);
    const gallery=photos?.photos?.length?section("Zdjęcia PLP",
        '<div class="grid">'+photos.photos.map(photo=>
            '<a target="_blank" rel="noopener noreferrer" href="'+e(photo.url)+'"><img loading="lazy" style="width:100%;max-height:230px;object-fit:contain" src="'+e(photo.local||photo.url)+'" alt="'+e(photo.alt||player.name)+'"></a>'
        ).join("")+'</div>'
    ):"";

    const teamPhotoCandidates=(DB.analysis?.historical_team_media_candidates||[])
        .filter(item=>same(item.player_id,player.id));
    const historicTeamGallery=teamPhotoCandidates.length
        ?section("Historyczne zdjęcia dawnych drużyn — do weryfikacji",
            '<div class="notice">To archiwalne fotografie klubów, w których odnotowano zawodnika. Samo powiązanie klubowe NIE potwierdza, że zawodnik znajduje się na zdjęciu. Nie są one liczone jako zdjęcia profilowe.</div>'+
            table(["Archiwalny klub","Materiał PLP","Weryfikacja"],teamPhotoCandidates.map(item=>[
                e(item.team),
                '<a target="_blank" rel="noopener noreferrer" href="'+e(item.url)+'">Otwórz zdjęcie historyczne ↗</a>',
                "Osoba na zdjęciu niepotwierdzona"
            ])))
        :"";
    return headline(player.name,player.status||"Zawodnik Bosch Service Tech-Car")+
        metrics([["Mecze Boscha",player.apps??(player.orlik2026?.apps!=null?"≥ "+player.orlik2026.apps:"—")],["Gole Boscha",player.stats_minimum&&Number.isInteger(player.goals)?"≥ "+player.goals:player.goals??(player.orlik2026?.goals!=null?"≥ "+player.orlik2026.goals:"—")],["Asysty Boscha",player.assists??(player.orlik2026?.assists!=null?"≥ "+player.orlik2026.assists:"—")],["Samobóje",player.own_goals_conceded??0],["MVP Boscha",player.motm??"—"]])+
        (player.career_totals?section("Cała kariera w PLP",metrics([["Mecze",player.career_totals.apps??"—"],["Gole",player.career_totals.goals??"—"],["Asysty",player.career_totals.assists??"—"],["MVP",player.career_totals.motm??"—"]])):"")+
        section("Sezony w Bosch Service Tech-Car",seasonTable+remainingNote)+
        playerProvenanceSection(player)+
        playerTrendSection(player)+
        publicCareerSection+
        playerMatchTimeline(player)+
        scoredMatchSection+
        ownGoalHistory+
        profileMergeNote+
        (careerRows.length?section("Historia kariery wg zapisów API — może pomijać Superpuchary",table(["Sezon","Klub","M","G","A"],careerRows)):"")+
        '<div class="notice">„—” oznacza brak szczegółowych statystyk w archiwum, a nie zero. „≥” oznacza potwierdzone minimum z dostępnego sezonu. Sumy całej kariery PLP mogą obejmować także inne kluby.</div>'+
        gallery+
        historicTeamGallery+
        (player.peak?section("Najlepszy historyczny sezon",'<div class="card">'+e(player.peak)+'</div>'):"")+
        (player.profile_url?'<p><a href="'+e(player.profile_url)+'" target="_blank" rel="noopener noreferrer">Profil w PLP ↗</a></p>':"");
}
function groupOpponentHistory(matches){
    const namesToIds=new Map();
    for(const match of matches){
        if(match.opponent_id==null)continue;
        const name=normalized(match.opponent);
        const ids=namesToIds.get(name)||new Set();
        ids.add(String(match.opponent_id));
        namesToIds.set(name,ids);
    }
    const groups=new Map();
    for(const match of matches){
        const name=normalized(match.opponent);
        const candidates=namesToIds.get(name)||new Set();
        const id=match.opponent_id!=null?String(match.opponent_id):
            candidates.size===1?[...candidates][0]:null;
        const key=id?"plp-"+id:"name-"+name;
        if(!groups.has(key)){
            groups.set(key,{id,name:match.opponent,key,aliases:[],matches:[],recentDate:""});
        }
        const group=groups.get(key);
        group.matches.push(match);
        if(!group.aliases.includes(match.opponent))group.aliases.push(match.opponent);
        if(match.date>=group.recentDate){
            group.name=match.opponent;
            group.recentDate=match.date;
        }
    }
    return [...groups.values()].sort((a,b)=>a.name.localeCompare(b.name,"pl"));
}
function opponents(){
    DB.opponents=groupOpponentHistory(DB.matches);
    return headline("Rywale","Historia klubów według oficjalnego ID PLP — także po zmianach nazw.")+
        '<div class="filters"><input id="local-filter" placeholder="Znajdź rywala…"></div>'+
        '<div id="filtered-opponents"></div>';
}
function opponentDetail(id){
    const groups=groupOpponentHistory(DB.matches);
    const exact=groups.find(group=>group.key===id);
    const legacy=groups.filter(group=>group.aliases.some(name=>normalized(name)===id));
    const selected=exact||(legacy.length===1?legacy[0]:null);
    if(!selected&&legacy.length>1){
        return headline("Wybierz właściwego rywala","Ta sama nazwa występuje przy różnych ID PLP.")+
            cards(legacy.map(group=>'<h3>'+href("opponent/"+encodeURIComponent(group.key),group.name)+
                '</h3><p>ID PLP: '+e(group.id)+' · '+e(group.matches.length)+' meczów</p>'));
    }
    const games=selected?.matches||[];
    if(!games.length)return empty("Nie znaleziono rywala.");

    const victories=games.filter(match=>match.gf>match.ga).length;
    const draws=games.filter(match=>match.gf===match.ga).length;
    const leaders=new Map();

    for(const match of games){
        for(const scorer of match.goal_protocol?.scorers||[]){
            const entry=leaders.get(scorer.player_id)||{id:scorer.player_id,name:scorer.name,goals:0};
            entry.goals+=scorer.goals;
            leaders.set(scorer.player_id,entry);
        }
    }

    const ranked=[...leaders.values()].sort((first,second)=>second.goals-first.goals||first.name.localeCompare(second.name,"pl"));
    const leaderTable=ranked.length?table(["Strzelec","Gole przeciw rywalowi"],ranked.map(row=>[
        href("player/"+encodeURIComponent(row.id),row.name),
        e(row.goals)
    ])):empty("Brak goli zawodników Boscha przeciwko temu rywalowi.");

    return headline(selected.name,"Historia spotkań z Bosch Service Tech-Car")+
        (selected.aliases.length>1?section("Historyczne nazwy rywala",'<div class="card">'+e(selected.aliases.join(" · "))+'</div>'):"")+
        metrics([["Mecze",games.length],["Wygrane",victories],["Remisy",draws],["Porażki",games.length-victories-draws],["Bramki Boscha",games.reduce((sum,match)=>sum+match.gf,0)]])+
        section("Najskuteczniejsi przeciw rywalowi",leaderTable)+
        section("Wszystkie pojedynki",'<div class="card">'+matchList(games)+'</div>');
}
function videos(){
    return headline("Wideo","Archiwum filmów i nagrań przypisanych do meczów.")+
        metrics([["Materiały",DB.videos.length],["Powiązane z meczami",DB.videos.filter(video=>video.match_id).length]])+
        '<div class="filters"><input id="local-filter" placeholder="Tytuł, kanał…" aria-label="Szukaj nagrań"><label>Sortuj <select id="video-sort" aria-label="Sortuj filmy"><option value="newest">Najnowsze</option><option value="oldest">Najstarsze</option><option value="title">Tytuł A–Z</option><option value="title-desc">Tytuł Z–A</option><option value="matched">Najpierw powiązane z meczami</option></select></label></div><div id="filtered-videos"></div>'+
        '<div class="notice">Sortowanie uwzględnia datę publikacji YouTube. Jeśli jej brakuje, używa daty potwierdzonego meczu, opisanej jako „Mecz”. Materiały bez obu dat trafiają na koniec.</div>';
}
function normalizedVideoDate(value){
    const text=String(value||"");
    const match=/^(\d{4})-?(\d{2})-?(\d{2})(?:T.*)?$/.exec(text);
    if(!match)return "";
    const iso=match.slice(1).join("-");
    return !Number.isNaN(Date.parse(iso))?iso:"";
}
function videoDate(video){
    return normalizedVideoDate(video.date)||normalizedVideoDate(DB?.matches?.find(match=>same(match.id,video.match_id))?.date);
}
function videoDateLabel(video){
    return normalizedVideoDate(video.date)|| (videoDate(video)?"Mecz: "+videoDate(video)+" (brak daty publikacji)":"Data publikacji nieznana");
}
function videoReviewLabel(video){
    return video.status==="rejected"?'<p class="notice">Powiązanie odrzucone: '+e(video.review_reason||"Materiał wymaga ponownej identyfikacji")+'</p>':
        video.match_id?"":'<p class="small">Materiał oczekuje na potwierdzenie meczu.</p>';
}

function sortVideos(items,selectedSort){
    const sorted=items.slice();
    const newest=(first,second)=>videoDate(second).localeCompare(videoDate(first))||String(first.title||"").localeCompare(String(second.title||""),"pl");
    const oldest=(first,second)=>{
        if (!videoDate(first)) return videoDate(second)?1:0;
        if (!videoDate(second)) return -1;
        return videoDate(first).localeCompare(videoDate(second));
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
    const sourceNote='<div class="notice">Gole 113 ligowych spotkań zostały zweryfikowane w oryginalnych protokołach PLP. Łączne statystyki zawodników mogą obejmować również Superpuchary, a asysty, kartki i występy mają odrębne źródła.</div>';
    const measures=[
        ["Strzelcy — gole","goals",player=>player.goals,0],
        ["Asysty","assists",player=>player.assists,0],
        ["Kanadyjka — gole + asysty","points",player=>player.goals!=null&&player.assists!=null?player.goals+player.assists:null,0],
        ["Najwięcej występów","apps",player=>player.apps,0],
        ["MVP / piłkarz meczu","motm",player=>player.motm,0],
        ["Żółte kartki","yellow",player=>player.yellow,0],
        ["Bezpośrednie czerwone","red",player=>player.red,0],
        ["Gole na mecz — minimum 5 występów","goals_per_match",player=>player.apps>=5&&player.goals!=null?player.goals/player.apps:null,2],
        ["Asysty na mecz — minimum 5 występów","assists_per_match",player=>player.apps>=5&&player.assists!=null?player.assists/player.apps:null,2],
        ["Kanadyjka na mecz — minimum 5 występów","points_per_match",player=>player.apps>=5&&player.goals!=null&&player.assists!=null?(player.goals+player.assists)/player.apps:null,2],
        ["MVP na mecz — minimum 5 występów","motm_per_match",player=>player.apps>=5&&player.motm!=null?player.motm/player.apps:null,2]
    ];
    const boards=measures.map(([heading,key,getValue,precision])=>{
        const measured=players.map(player=>({player,value:getValue(player)}))
            .filter(row=>Number.isFinite(row.value)&&row.value>0)
            .sort((a,b)=>b.value-a.value||a.player.name.localeCompare(b.player.name,"pl"));
        const complete=measured.filter(row=>row.player.bosch_totals&&!row.player.stats_minimum)
            .slice(0,10);
        const partial=measured.filter(row=>!row.player.bosch_totals||row.player.stats_minimum)
            .slice(0,10);
        const completeTable=complete.length?table(["#","Zawodnik","Wynik","Źródło"],complete.map((row,index)=>[
            e(index+1),playerLink(row.player),fmt(row.value,precision),"Suma zweryfikowanych sezonów PLP"
        ])):empty("Brak w pełni porównywalnych statystyk tej kategorii.");
        return section(heading,completeTable)+
            (partial.length?section(heading+" — udokumentowane minimum (bez rankingu)",
                table(["Zawodnik","Wartość minimum","Status"],partial.map(row=>[
                    playerLink(row.player),fmt(row.value,precision),
                    "Niepełna historia; wartość może być zaniżona"
                ]))):"");
    }).join("");
    const scoreWins=matches.slice().sort((a,b)=>(b.gf-b.ga)-(a.gf-a.ga)).slice(0,10);
    const offensive=matches.slice().sort((a,b)=>b.gf-a.gf).slice(0,10);
    const goalCoverage=DB.analysis?.player_goal_coverage||[];
    const totalGoals=goalCoverage.reduce((sum,row)=>sum+row.team_goals,0);
    const playerGoals=goalCoverage.reduce((sum,row)=>sum+row.attributed_goals,0);
    const ownGoals=goalCoverage.reduce((sum,row)=>sum+(row.opponent_own_goals||0),0);
    const awardedGoals=goalCoverage.reduce((sum,row)=>sum+row.administrative_goals,0);
    const unexplained=goalCoverage.reduce((sum,row)=>sum+row.unattributed_goals,0);
    const pendingGoals=goalCoverage.reduce((sum,row)=>sum+(row.pending_match_goals||0),0);
    const audit=section("Kontrola kompletności strzelców",
        metrics([["Gole drużyny",totalGoals],["Gole zawodników",playerGoals],["Samobóje rywali",ownGoals],["Administracyjne",awardedGoals],["Do wyjaśnienia",unexplained],["Oczekuje na protokół",pendingGoals]])+
        '<div class="notice">Rozliczenie '+e(matches.filter(match=>match.goal_protocol?.verified).length)+' zweryfikowanych meczów: <strong>'+e(totalGoals)+' = '+e(playerGoals)+' goli zawodników + '+e(ownGoals)+' samobóje rywali + '+e(awardedGoals)+' administracyjny'+(pendingGoals?' + '+e(pendingGoals)+' oczekuje na protokół':'')+'</strong>. '+
        'Pozostała różnica: <strong>'+e(unexplained)+'</strong>. Gole z protokołów są potwierdzone, ale asysty i kartki mogą mieć nadal niepełne archiwa.</div>'+
        table(["Sezon","Bramki drużyny","Gole zawodników","Samobóje rywali","Administracyjne","Czeka na protokół","Do wyjaśnienia"],goalCoverage.map(row=>[
            e(row.season),e(row.team_goals),e(row.attributed_goals),e(row.opponent_own_goals||0),e(row.administrative_goals),e(row.pending_match_goals||0),e(row.unattributed_goals)
        ]))+
        '<p>'+href("goals","Zobacz wszystkie 113 meczów i oryginalne protokoły →")+'</p>'
    );
    const allScorerGames=matches.flatMap(match=>(match.goal_protocol?.scorers||[]).map(scorer=>({...scorer,match})));
    const biggestPerformances=allScorerGames.slice().sort((a,b)=>b.goals-a.goals||a.match.date.localeCompare(b.match.date)).slice(0,15);
    const matchRecords=section("Najwięcej goli jednego zawodnika w meczu",
        table(["Strzelec","Gole","Rywal","Data","Minuty"],biggestPerformances.map(row=>[
            href("player/"+encodeURIComponent(row.player_id),row.name),e(row.goals),matchLink(row.match),e(row.match.date),goalMinutes(row)
        ]))
    );
    const fastestGoalRows=allScorerGames.flatMap(row=>row.minutes.map(minute=>({
        minute:Number(String(minute).split("+")[0]),original:minute,player_id:row.player_id,name:row.name,match:row.match
    }))).filter(row=>Number.isFinite(row.minute)).sort((a,b)=>a.minute-b.minute||a.match.date.localeCompare(b.match.date)).slice(0,12);
    const fastestGoals=section("Najszybsze gole Boscha",
        table(["Minuta","Strzelec","Rywal","Sezon"],fastestGoalRows.map(row=>[
            e(row.original+"′"),href("player/"+encodeURIComponent(row.player_id),row.name),matchLink(row.match),e(row.match.season)
        ]))
    );
    const ownGoalRecords=section("Samobóje rywali",
        table(["Data","Rywal","Samobóje","Oficjalne źródło"],matches.filter(match=>match.goal_protocol?.own_goals).map(match=>[
            e(match.date),matchLink(match),e(match.goal_protocol.own_goals),
            '<a href="'+e(match.goal_protocol.source_url)+'" target="_blank" rel="noopener noreferrer">PLP ↗</a>'
        ]))
    );
    const ownGoalPlayers=players.filter(player=>(player.own_goals_conceded||0)>0)
        .sort((first,second)=>second.own_goals_conceded-first.own_goals_conceded);
    const ownConcededRecords=section("Samobóje zawodników Boscha — dla przeciwników",
        table(["Zawodnik","Samobóje","Potwierdzone protokoły"],ownGoalPlayers.map(player=>[
            playerLink(player),
            e(player.own_goals_conceded),
            (player.own_goal_matches||[]).map(entry=>href("match/"+encodeURIComponent(entry.match_id),entry.opponent)).join(", ")
        ]))
    );
    const administrativeRecords=section("Korekty administracyjne wyników",
        table(["Data","Rywal","Bramki administracyjne","Oficjalne źródło"],matches.filter(match=>match.goal_protocol?.administrative_goals).map(match=>[
            e(match.date),matchLink(match),e(match.goal_protocol.administrative_goals),
            '<a href="'+e(match.goal_protocol.source_url)+'" target="_blank" rel="noopener noreferrer">PLP ↗</a>'
        ]))
    );
    const seasonal=section("Rekordy sezonowe",table(["Sezon","Miejsce","Punkty","PPG","Bramki","Gole/mecz","Stracone/mecz"],seasons.slice().sort((a,b)=>b.points-a.points).map(seasonRow=>[seasonLink(seasonRow),e(seasonRow.position??"—"),e(seasonRow.points),ppg(seasonRow),e(seasonRow.gf+":"+seasonRow.ga),fmt(seasonRow.gf/seasonRow.matches),fmt(seasonRow.ga/seasonRow.matches)])));
    return headline("Rekordy Boscha","Strzelcy, asysty, kanadyjka, kartki, MVP, występy, skuteczność, mecze i sezony — z kontrolą jakości źródeł.")+
        sourceNote+
        section("Najwyższe zwycięstwa",table(["Data","Rywal","Wynik","Sezon"],scoreWins.map(match=>[e(match.date),matchLink(match),winner(match),e(match.season)])))+
        section("Najwięcej goli Boscha w meczu",table(["Data","Rywal","Wynik","Sezon"],offensive.map(match=>[e(match.date),matchLink(match),winner(match),e(match.season)])))+
        seasonal+boards+matchRecords+fastestGoals+ownGoalRecords+ownConcededRecords+administrativeRecords+audit;
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
function streakMetrics(fixtures){
    const sorted=fixtures.slice().sort((a,b)=>a.date.localeCompare(b.date)||String(a.id).localeCompare(String(b.id)));
    const best={wins:0,unbeaten:0,losses:0};
    let wins=0,unbeaten=0,losses=0;
    for(const match of sorted){
        const r=result(match);
        wins=r==="W"?wins+1:0;
        unbeaten=r!=="P"?unbeaten+1:0;
        losses=r==="P"?losses+1:0;
        best.wins=Math.max(best.wins,wins);
        best.unbeaten=Math.max(best.unbeaten,unbeaten);
        best.losses=Math.max(best.losses,losses);
    }
    const latest=sorted.slice(-5).reverse();
    return {best,latest,cleanSheets:sorted.filter(m=>m.ga===0).length};
}
function goalMinuteGroups(fixtures){
    const rows=[{name:"1–10",count:0},{name:"11–20",count:0},{name:"21–30",count:0},{name:"31–40",count:0},{name:"41+",count:0}];
    let unknown=0;
    for(const match of fixtures){
        for(const scorer of match.goal_protocol?.scorers||[]){
            for(const minute of scorer.minutes||[]){
                const parsed=Number.parseInt(String(minute),10);
                if(!Number.isFinite(parsed)||parsed<=0){unknown++;continue;}
                const index=parsed<=40?Math.min(3,Math.floor((parsed-1)/10)):4;
                rows[index].count+=1;
            }
            unknown+=Math.max(0,(scorer.goals||0)-(scorer.minutes||[]).length);
        }
    }
    return {rows,unknown};
}
function splitMatchHalves(match){
    const score=/^(\d+)\s*:\s*(\d+)$/.exec(String(match.halftime||""));
    if(!score||!String(match.event_link||"").startsWith("https://podlaskaliga.pl/wydarzenie/"))return null;
    const gf=Number(score[1]),ga=Number(score[2]);
    if(!Number.isInteger(match.gf)||!Number.isInteger(match.ga)||gf>match.gf||ga>match.ga)return null;
    return {first:{gf,ga},second:{gf:match.gf-gf,ga:match.ga-ga},source:match.event_link};
}
function halfTimeMetrics(fixtures){
    const halves=[{name:"I połowa",gf:0,ga:0,wins:0,draws:0,losses:0},
                  {name:"II połowa",gf:0,ga:0,wins:0,draws:0,losses:0}];
    const states=[{name:"Prowadzenie do przerwy",matches:0,wins:0,draws:0,losses:0},
                  {name:"Remis do przerwy",matches:0,wins:0,draws:0,losses:0},
                  {name:"Strata do przerwy",matches:0,wins:0,draws:0,losses:0}];
    let verified=0;
    for(const match of fixtures){
        const split=splitMatchHalves(match);
        if(!split)continue;
        verified++;
        [split.first,split.second].forEach((period,index)=>{
            const row=halves[index];
            row.gf+=period.gf;row.ga+=period.ga;
            row[period.gf>period.ga?"wins":period.gf===period.ga?"draws":"losses"]++;
        });
        const state=states[split.first.gf>split.first.ga?0:split.first.gf===split.first.ga?1:2];
        state.matches++;
        state[match.gf>match.ga?"wins":match.gf===match.ga?"draws":"losses"]++;
    }
    return {verified,unavailable:fixtures.length-verified,halves,states};
}
function enhancedHistoricalAnalysis(){
    const form=streakMetrics(DB.matches);
    const minutes=goalMinuteGroups(DB.matches);
    const periods=halfTimeMetrics(DB.matches);
    const recordedHalftimes=DB.matches.filter(m=>/^\d+\s*:\s*\d+$/.test(String(m.halftime||"")));
    const latest=form.latest.map(match=>[
        e(match.date),href("match/"+encodeURIComponent(match.id),match.opponent),
        e(match.gf+":"+match.ga),e(result(match))
    ]);
    const withVideo=DB.matches.filter(m=>(m.videos||[]).length>0).length;
    return section("Serie i ostatnia forma",
        metrics([["Najdłuższa seria zwycięstw",form.best.wins],
                 ["Najdłuższa seria bez porażki",form.best.unbeaten],
                 ["Najdłuższa seria porażek",form.best.losses],
                 ["Czyste konta",form.cleanSheets]])+
        table(["Data","Rywal","Wynik","Rezultat"],latest))+
        section("Kiedy padały nasze gole",
            barChart(minutes.rows,"count",row=>String(row.count))+
            (minutes.unknown?empty("Gole bez czytelnej minuty w protokole: "+minutes.unknown):""))+
        section("Pierwsza i druga połowa — potwierdzone wyniki PLP",
            metrics([["Mecze z poprawnym wynikiem do przerwy",periods.verified],
                     ["Bez potwierdzonego podziału",periods.unavailable]])+
            table(["Część meczu","Gole Boscha","Gole rywala","Wygrane połowy","Remisy","Przegrane połowy"],
                periods.halves.map(row=>[e(row.name),e(row.gf),e(row.ga),e(row.wins),e(row.draws),e(row.losses)]))+
            table(["Stan do przerwy","Mecze","Wygrane na koniec","Remisy na koniec","Porażki na koniec"],
                periods.states.map(row=>[e(row.name),e(row.matches),e(row.wins),e(row.draws),e(row.losses)]))+
            '<p class="small">Podział opiera się na wynikach do przerwy z protokołów PLP. Gole II połowy to wynik końcowy minus potwierdzony wynik do przerwy. Brakujący lub sprzeczny wynik jest wyłączany z obliczeń. Źródła znajdują się w szczegółach meczów.</p>')+
        section("Pokrycie archiwum nagraniami",
            metrics([["Mecze z nagraniem",withVideo],
                     ["Mecze bez nagrania",DB.matches.length-withVideo],
                     ["Dostępne wyniki do przerwy",recordedHalftimes.length]])+
            table(["Sezon","Mecze","Z wideo","Bez wideo"],DB.seasons.map(season=>{
                const entries=DB.matches.filter(m=>same(m.sid,season.id));
                const covered=entries.filter(m=>(m.videos||[]).length>0).length;
                return [e(season.name),e(entries.length),e(covered),e(entries.length-covered)];
            })));
}
function analysis(){const seasons=DB.seasons.map(s=>({...s,ppg:s.points/s.matches,ga_pg:s.ga/s.matches,gf_pg:s.gf/s.matches}));const promo=DB.analysis?.promotions||[];return headline("Analityka","Głębsze spojrzenie na wyniki, skuteczność, defensywę i awans.")+enhancedHistoricalAnalysis()+section("Punkty na mecz",barChart(seasons,"ppg",s=>fmt(s.ppg)))+section("Stracone gole na mecz",barChart(seasons,"ga_pg",s=>fmt(s.ga_pg)))+section("Atak — gole na mecz",barChart(seasons,"gf_pg",s=>fmt(s.gf_pg)))+section("Gole zawodników w kolejnych sezonach",barChart(DB.analysis.player_goal_coverage.map(row=>({name:row.season,goals:row.attributed_goals})),"goals",row=>String(row.goals)))+section("Strzelcy — każde spotkanie",'<p>'+href("goals","Otwórz wszystkie protokoły meczowe →")+"</p>")+ section("Porównywarka sezonów",'<div class="filters"><select id="compare-a">'+DB.seasons.map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select><select id="compare-b">'+DB.seasons.map(s=>'<option value="'+e(s.id)+'">'+e(s.name)+'</option>').join("")+'</select></div><div id="compare-result"></div>')+section("Benchmark awansu",promo.length?table(["Sezon","Drużyna","Miejsce","PPG"],promo.slice(0,35).map((p,i)=>[e(i>0&&promo[i-1].sid===p.sid?"":p.season||p.season_name),e(p.team_name),e(p.rank),fmt(p.ppg)])):empty("Brak danych benchmarku."))+section("Scouting historyczny",cards((DB.analysis?.scouting||[]).slice(0,13).map(x=>'<h3>'+e(x.name)+'</h3><p><span class="pill">'+e(x.threat_level)+'</span></p><p>'+e(x.summary)+'</p>')))+'<div class="notice">Scouting Orlika 2026 jest archiwalną prognozą. Historyczne protokoły meczowe zostały sprawdzone, a gole i samobóje połączone z wynikami sezonów.</div><p><a href="archive.html#splits">Zobacz pełne archiwum analiz technicznych →</a></p>';}
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

    return seasonRecord !== null || Boolean(player.roster_seasons?.[selectedSeasonId]);
}

function playerCard(player, selectedSeasonId) {
    const selectedSeason = selectedSeasonId ? season(selectedSeasonId) : null;
    const seasonRecord = selectedSeasonId ? playerSeasonRecord(player, selectedSeasonId) : null;
    const summary = selectedSeasonId
        ? "M: " + e(seasonRecord?.apps ?? "—") + " / G: " + e(seasonRecord?.goals ?? "—") + " / A: " + e(seasonRecord?.assists ?? "—")
        : player.orlik2026
            ? "Orlik 2026: " + e(player.orlik2026.goals ?? "—") + " G / " + e(player.orlik2026.assists ?? "—") + " A"
            : "Archiwum: " + e(player.goals ?? "—") + " G / " + e(player.assists ?? "—") + " A";

    return (seasonRecord?.apps===0?'<span class="pill">Zgłoszony — 0 występów</span>':'') + '<h3>' + playerLink(player) + '</h3><p>' + e(selectedSeason?.name || player.status) + '</p><div class="small">' + summary + '</div>';
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
function route(){if(!DB)return;const pieces=decodeURIComponent(location.hash.slice(2)||"").split("/");const name=pieces[0]||"",id=pieces.slice(1).join("/");const routes={"":home,seasons,matches:matchesPage,goals:goalsArchive,players,opponents,analysis,videos,records,compare:playerComparison,quality:dataQuality};const pages={season:()=>seasonPage(id),match:()=>matchDetail(id),player:()=>playerDetail(id),opponent:()=>opponentDetail(id)};$("app").innerHTML=pages[name]?pages[name]():routes[name]?routes[name]():empty("Nie znaleziono strony.");document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#/"+name||name==="season"&&a.getAttribute("href")==="#/seasons"||name==="player"&&a.getAttribute("href")==="#/players"||name==="match"&&a.getAttribute("href")==="#/matches"||name==="opponent"&&a.getAttribute("href")==="#/opponents"));if(name==="goals")setupList(
    "filtered-goals",
    DB.matches,
    items=>table(["Data","Rywal","Wynik","Sezon","Strzelcy","Samobóje rywali","Samobóje Boscha","Administracyjne","PLP"],goalMatchRows(items.slice().sort((a,b)=>b.date.localeCompare(a.date)))),
    match=>[match.opponent,match.date,match.season,match.gf+":"+match.ga,...(match.goal_protocol?.scorers||[]).map(scorer=>scorer.name)].join(" "),
    (match,selectedSeasonId)=>same(match.sid,selectedSeasonId)
);
if(name==="matches")setupList("filtered-matches",DB.matches,items=>'<div class="card">'+matchList(items)+'</div>',m=>[m.opponent,m.date,m.season,m.gf+":"+m.ga].join(" "),(match, selectedSeasonId)=>same(match.sid,selectedSeasonId));if(name==="players"){const repaint=setupList("filtered-players",DB.players,(items,selectedSeasonId)=>cards(sortPlayerItems(items,selectedSeasonId).map(player=>playerCard(player,selectedSeasonId))),player=>player.name,playerPlayedSeason);$("player-sort")?.addEventListener("change",repaint);$("player-stat-filter")?.addEventListener("change",repaint);}if(name==="opponents")setupList("filtered-opponents",DB.opponents,items=>cards(items.map(x=>'<h3>'+href("opponent/"+encodeURIComponent(x.key),x.name)+'</h3><p>'+x.matches.length+' spotkań</p>')),x=>x.name);if(name==="videos"){const repaint=setupList("filtered-videos",DB.videos,items=>cards(sortVideos(items,$("video-sort")?.value||"newest").map(video=>'<div class="video-thumb">▶</div><h3>'+e(video.title)+'</h3><p>'+e(video.channel||"")+" • "+e(videoDateLabel(video))+'</p>'+videoReviewLabel(video)+'<p><a href="'+e(video.url)+'" target="_blank" rel="noopener noreferrer">Oglądaj ↗</a>'+(video.match_id?' • '+href("match/"+encodeURIComponent(video.match_id),"Mecz"):"")+'</p>')),video=>video.title+" "+video.channel);$("video-sort")?.addEventListener("change",repaint)};if(name==="compare"){const controls=[$("compare-player-a"),$("compare-player-b"),$("compare-player-season")];if(controls[1]&&DB.players.length>1)controls[1].value=DB.players[1].id;for(const control of controls)control?.addEventListener("change",updatePlayerComparison);updatePlayerComparison();}if(name==="analysis"){const selects=[$("compare-a"),$("compare-b")];if(selects[1])selects[1].value=DB.seasons.at(-1).id;for(const x of selects)x?.addEventListener("change",compare);compare();}window.scrollTo(0,0);}
function initSearch(){const dialog=$("search-dialog"),input=$("global-search");function open(){dialog.showModal();input.focus();} $("search-open").addEventListener("click",open);document.addEventListener("keydown",event=>{if(event.key==="/"&&document.activeElement.tagName!=="INPUT"){event.preventDefault();open();}if((event.key==="Escape")&&dialog.open)dialog.close();});input.addEventListener("input",()=>{const q=normalized(input.value);const records=[...DB.players.map(p=>({name:p.name,kind:"Zawodnik",url:"player/"+p.id})),...DB.seasons.map(s=>({name:s.name,kind:"Sezon",url:"season/"+s.id})),...DB.matches.map(m=>({name:m.date+" • "+m.opponent,kind:"Mecz",url:"match/"+m.id})),...groupOpponentHistory(DB.matches).map(o=>({name:o.name+" "+o.aliases.join(" "),kind:"Rywal",url:"opponent/"+o.key}))];$("search-results").innerHTML=!q?"":records.filter(item=>normalized(item.name).includes(q)).slice(0,22).map(item=>'<a class="list-row" href="#/'+e(item.url)+'"><span>'+e(item.name)+'</span><small>'+e(item.kind)+'</small></a>').join("")||empty("Brak wyników.");$("search-results").querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>dialog.close()));});}
(async function(){const saved=localStorage.getItem("bosch-theme")||"dark";document.documentElement.dataset.theme=saved;$("theme-toggle").addEventListener("click",()=>{const theme=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=theme;localStorage.setItem("bosch-theme",theme);});try{const response=await fetch("assets/data.json",{cache:"no-store"});if(!response.ok)throw Error("HTTP "+response.status);DB=await response.json();initSearch();window.addEventListener("hashchange",route);route();}catch(error){$("app").innerHTML=empty("Nie udało się wczytać danych kompendium: "+error.message);}})();
