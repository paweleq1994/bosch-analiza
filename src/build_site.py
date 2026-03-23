from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "bosch_service_tech_car_data_v3.json"
VIDEO_PATH = ROOT / "data" / "bosch_service_tech_car_video_library_v3.json"
OUT_PATH = ROOT / "docs" / "index.html"


TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kompendium Wiedzy o Bosch Service Tech-Car</title>
  <style>
    :root{--bg:#f3f7fb;--panel:#fff;--soft:#eef5ff;--ink:#132238;--muted:#5b6b7d;--line:#d6e0ea;--blue:#1d4ed8;--teal:#0f766e;--orange:#ea580c;--red:#dc2626;--gold:#b7791f;--shadow:0 14px 40px rgba(19,34,56,.08);--mobile-toolbar-h:74px}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at top left,rgba(37,99,235,.08),transparent 26%),linear-gradient(180deg,#eef4fb 0%,#fafcff 100%);color:var(--ink);font-family:Aptos,Bahnschrift,"Segoe UI",sans-serif;line-height:1.45}
    a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
    .shell{width:min(98vw,1920px);margin:0 auto;padding:18px 0 48px}
    .hero{background:linear-gradient(135deg,#0b1324 0%,#0f766e 48%,#2563eb 100%);color:#fff;border-radius:28px;padding:30px 30px 24px;box-shadow:var(--shadow)}
    .hero h1{margin:0 0 8px;font-size:clamp(2rem,3.4vw,3.8rem);line-height:1.02;letter-spacing:-.03em}
    .hero p{margin:0;max-width:1120px;color:rgba(255,255,255,.92)}
    .hero-stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:20px}
    .hero-card,.panel,.mini-card{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:14px 16px}
    .hero-label,.k,.toolbar label,.toolbar-fly label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:inherit;opacity:.78;font-weight:700}
    .hero-value,.v{margin-top:6px;font-size:1.35rem;font-weight:800}
    body.toolbar-lock{overflow:hidden}
    .toolbar-sentinel{height:1px}
    .toolbar{position:relative;z-index:20;margin-top:16px;padding:14px;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}
    .toolbar-mobile,.toolbar-backdrop,.toolbar-fly{display:none}
    .toolbar-mobile-bar{display:flex;align-items:center;justify-content:space-between;gap:12px}
    .toolbar-mobile-copy{min-width:0}
    .toolbar-mobile-label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .toolbar-toggle{display:inline-grid;place-items:center;width:46px;min-width:46px;min-height:46px;border-radius:14px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:800;padding:0;cursor:pointer}
    .toolbar-toggle-box{display:grid;gap:4px;width:18px}
    .toolbar-toggle-box span{display:block;height:2px;border-radius:99px;background:var(--ink);transition:transform .18s ease,opacity .18s ease}
    .toolbar.open .toolbar-toggle-box span:nth-child(1){transform:translateY(6px) rotate(45deg)}
    .toolbar.open .toolbar-toggle-box span:nth-child(2){opacity:0}
    .toolbar.open .toolbar-toggle-box span:nth-child(3){transform:translateY(-6px) rotate(-45deg)}
    .toolbar-summary{font-size:.92rem;color:var(--muted);padding:2px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .toolbar-panel{display:block}
    .toolbar-panel-head{display:none}
    .toolbar-panel-title{margin-top:4px;font-size:1.05rem;font-weight:800;letter-spacing:-.02em}
    .toolbar-close{display:inline-grid;place-items:center;width:42px;min-width:42px;min-height:42px;border-radius:12px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-size:1.35rem;line-height:1;cursor:pointer;padding:0}
    .toolbar-compact{align-items:center;justify-content:space-between;gap:14px}
    .toolbar-compact-copy{min-width:0}
    .toolbar-compact-title{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .toolbar-compact-summary{margin-top:3px;font-size:.95rem;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .toolbar-compact-actions{display:flex;gap:8px;align-items:center;flex-shrink:0}
    .toolbar-compact-btn{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 14px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:800;cursor:pointer}
    .toolbar-range{margin-bottom:14px}
    .range-block{padding:14px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%)}
    .range-help{margin-top:6px;color:var(--muted);font-size:.92rem}
    .range-row{display:grid;gap:8px;margin-top:12px}
    .range-title{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .chip-group{display:flex;gap:8px;flex-wrap:wrap}
    .chip-btn{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:0 12px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:700;cursor:pointer}
    .chip-btn.active{background:#e9f1ff;border-color:#7aa6ff;color:#163f94;box-shadow:inset 0 0 0 1px rgba(29,78,216,.18)}
    .toolbar-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:end}
    .control{display:grid;gap:6px}
    .toolbar input,.toolbar select,.toolbar button,.toolbar-fly input,.toolbar-fly select,.toolbar-fly button{min-height:46px;border-radius:14px;border:1px solid var(--line);background:#fff;padding:0 14px;font:inherit;color:var(--ink)}
    .toolbar button,.toolbar-fly button{font-weight:800;cursor:pointer}
    .nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
    .nav a{padding:10px 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);font-weight:700}
    .toolbar-fly{position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:130;width:min(880px,calc(100vw - 28px))}
    .toolbar-fly.active{display:block}
    .toolbar-fly-shell{padding:10px 12px;background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:18px;box-shadow:0 14px 36px rgba(19,34,56,.12)}
    .toolbar-fly.open .toolbar-fly-shell{box-shadow:0 18px 40px rgba(19,34,56,.12),0 34px 84px rgba(19,34,56,.22)}
    .toolbar-fly .toolbar-compact{display:flex}
    .toolbar-fly-panel{display:none}
    .toolbar-fly.open .toolbar-fly-panel{display:block;margin-top:12px}
    .section{margin-top:18px;background:var(--panel);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow);overflow:visible}
    .head{padding:24px 24px 0}.head h2{margin:0;font-size:1.45rem;letter-spacing:-.02em}.head p{margin:8px 0 0;color:var(--muted)}
    .body{padding:18px 24px 24px}
    .cards,.season-grid,.player-grid,.chart-grid,.split,.dense-grid{display:grid;gap:14px}
    .cards>*,.season-grid>*,.player-grid>*,.chart-grid>*,.split>*,.dense-grid>*{min-width:0}
    .cards{grid-template-columns:repeat(5,1fr)}
    .card,.season-card,.player-card{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
    .value{margin-top:8px;font-size:1.42rem;font-weight:800;letter-spacing:-.03em}
    .sub{margin-top:8px;color:var(--muted);font-size:.94rem}
    .season-grid{grid-template-columns:repeat(4,1fr);margin-top:14px}
    .player-grid{grid-template-columns:repeat(6,1fr);margin-top:14px}
    .chart-grid{grid-template-columns:repeat(2,1fr)}
    .split,.dense-2{grid-template-columns:1fr 1fr}
    .split-wide{grid-template-columns:minmax(0,1.3fr) minmax(320px,.9fr)}
    .dense-3{grid-template-columns:repeat(3,1fr)}
    .season-card{cursor:pointer;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}
    .season-card:hover{transform:translateY(-2px);border-color:rgba(29,78,216,.45);box-shadow:0 12px 28px rgba(29,78,216,.12)}
    .season-card.active{border-color:rgba(29,78,216,.7);background:linear-gradient(180deg,#f7fbff 0%,#eef5ff 100%)}
    .tags,.identity-badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.identity-badges{margin-top:0;align-items:center}.tag{display:inline-flex;align-items:center;justify-self:start;width:fit-content;max-width:100%;white-space:nowrap;padding:6px 10px;border-radius:999px;font-size:.82rem;font-weight:800;border:1px solid var(--line);background:#fff}.blue{background:#eef4ff;border-color:#bfd4ff;color:#1e40af}.teal{background:#ecfdf5;border-color:#9de5d6;color:#0f766e}.orange{background:#fff7ed;border-color:#fdba74;color:#9a3412}.red{background:#fef2f2;border-color:#fca5a5;color:#991b1b}.gold{background:#fff7e6;border-color:#f6c36f;color:#8a5c00}
    .table-card,.chart,.chapter-note{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .table-top{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.table-top h3{margin:0;font-size:1rem}.meta{color:var(--muted);font-size:.9rem}
    .table-wrap{overflow-x:auto;overflow-y:visible;border:1px solid var(--line);border-radius:14px;background:#fff}
    .table-wrap.scroller{max-height:620px;overflow-y:auto}
    table{width:100%;border-collapse:collapse;font-size:.94rem}thead th{position:sticky;top:0;z-index:1;background:#eef5fb;color:#17324c;border-bottom:1px solid var(--line)}
    th,td{padding:10px 10px;text-align:left;vertical-align:top;border-bottom:1px solid #eef3f8;overflow-wrap:break-word}tbody tr:nth-child(even) td{background:#fbfdff}tbody tr:hover td{background:#f4f9ff}
    td a{white-space:nowrap;display:inline-block}
    td[data-label="ID"],td[data-label="Link"]{white-space:nowrap;min-width:76px}
    th button{all:unset;cursor:pointer;font-weight:800;display:inline-flex;align-items:center;gap:6px}.sort{display:inline-flex;width:12px;justify-content:center;color:var(--muted)}
    .status{display:inline-flex;justify-self:start;width:fit-content;max-width:100%;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:800}.obecny{background:#dcfce7;color:#166534}.arch{background:#fff7ed;color:#9a3412}.win{background:#dcfce7;color:#166534}.draw{background:#eff6ff;color:#1d4ed8}.loss{background:#fef2f2;color:#991b1b}
    .chart h3{margin:0 0 12px;font-size:1rem}.chart svg{display:block;width:100%;height:auto}
    .chapter-note{margin-top:16px;background:linear-gradient(180deg,#f8fbff 0%,#eef5ff 100%);border-color:#cadeff}.chapter-note strong{display:block;margin-bottom:6px;font-size:.84rem;letter-spacing:.08em;text-transform:uppercase;color:#18406b}.chapter-note p{margin:.4rem 0 0;overflow-wrap:anywhere}
    .term{display:inline-flex;align-items:center;border-bottom:1px dashed rgba(19,34,56,.38);cursor:help;font-weight:800}
    .term:focus-visible{outline:2px solid rgba(37,99,235,.35);outline-offset:3px;border-radius:4px}
    .tooltip-layer{position:fixed;left:0;top:0;max-width:min(340px,calc(100vw - 24px));padding:10px 12px;border-radius:12px;background:#0b1324;color:#fff;box-shadow:0 14px 28px rgba(11,19,36,.26);font-size:12px;font-weight:600;line-height:1.45;opacity:0;pointer-events:none;transform:translateY(4px);transition:opacity .12s ease,transform .12s ease;z-index:9999}
    .tooltip-layer.show{opacity:1;transform:translateY(0)}
    .empty{padding:18px;text-align:center;color:var(--muted);background:#fff;border:1px dashed var(--line);border-radius:14px}
    .reco-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    .reco-card{background:linear-gradient(180deg,#fff 0%,#f9fbfe 100%);border:1px solid var(--line);border-radius:18px;padding:16px}
    .reco-card h3{margin:0 0 8px;font-size:1rem}
    .reco-card p{margin:8px 0 0;color:var(--muted);overflow-wrap:anywhere}
    .foot{margin-top:12px;color:var(--muted);font-size:.9rem}
    @media (max-width:1480px){.split,.split-wide{grid-template-columns:1fr}}
    @media (max-width:1280px){.cards{grid-template-columns:repeat(3,1fr)}.season-grid{grid-template-columns:repeat(2,1fr)}.player-grid{grid-template-columns:repeat(3,1fr)}.chart-grid,.dense-2,.dense-3,.reco-grid{grid-template-columns:1fr}.hero-stats{grid-template-columns:repeat(2,1fr)}.toolbar-grid{grid-template-columns:1fr 1fr}}
    @media (max-width:900px){.shell{width:100%!important;padding:0!important}.hero,.section{margin-left:10px;margin-right:10px}.hero{margin-top:calc(var(--mobile-toolbar-h) + 22px);padding:24px 20px 20px}.toolbar-sentinel{display:none}.toolbar-fly{display:none!important}.toolbar{position:fixed;top:10px;left:10px;right:10px;z-index:120;margin:0;padding:0;background:transparent;border:none;border-radius:0;box-shadow:none;backdrop-filter:none}.toolbar-mobile{display:block;position:relative;z-index:3;padding:10px 12px;background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 34px rgba(19,34,56,.12)}.toolbar.open .toolbar-mobile{box-shadow:0 16px 36px rgba(19,34,56,.16)}.toolbar-mobile-copy{max-width:calc(100% - 62px)}.toolbar-mobile-bar{min-height:52px}.toolbar-summary{padding-top:4px;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.toolbar-toggle{width:48px;min-width:48px;min-height:48px;border-radius:16px;box-shadow:0 8px 20px rgba(19,34,56,.08)}.toolbar-backdrop{display:block;position:fixed;inset:0;z-index:1;background:rgba(11,19,36,.38);opacity:0;pointer-events:none;transition:opacity .18s ease}.toolbar.open .toolbar-backdrop{opacity:1;pointer-events:auto}.toolbar-panel{display:block;position:fixed;z-index:2;top:calc(var(--mobile-toolbar-h) + 18px);left:10px;right:10px;bottom:10px;width:auto;padding:16px 14px 20px;background:rgba(255,255,255,.985);border:1px solid var(--line);border-radius:22px;box-shadow:0 20px 48px rgba(19,34,56,.18);overflow:auto;transform:translateY(14px);opacity:0;pointer-events:none;transition:transform .2s ease,opacity .2s ease}.toolbar.open .toolbar-panel{transform:translateY(0);opacity:1;pointer-events:auto}.toolbar-panel-head{display:block;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid #eef3f8}.toolbar-close{display:none}.toolbar-grid{grid-template-columns:1fr}.toolbar-panel .nav{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.toolbar-panel .nav a{display:flex;align-items:center;justify-content:center;width:100%;min-width:0;border-radius:14px;text-align:center;white-space:normal;overflow-wrap:anywhere}.head,.body{padding-left:16px;padding-right:16px}.cards{grid-template-columns:1fr 1fr}.season-grid,.player-grid{grid-template-columns:1fr}.tag,.status{width:auto;max-width:100%;white-space:normal;overflow-wrap:anywhere;line-height:1.25}.sub,.range-help,.toolbar-panel-title,.toolbar-summary,.chapter-note,.reco-card{overflow-wrap:anywhere}}
    @media (max-width:720px){.cards{grid-template-columns:1fr}.hero-stats{grid-template-columns:1fr 1fr}thead{display:none}table,tbody,tr,td{display:block;width:100%}tbody tr{border-bottom:1px solid var(--line)}td{display:grid;grid-template-columns:minmax(108px,42%) 1fr;gap:12px}td::before{content:attr(data-label);font-weight:800;color:var(--muted)}.table-wrap.scroller{max-height:none}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <h1>Kompendium Wiedzy o Bosch Service Tech-Car</h1>
      <p>Interaktywne kompendium wiedzy o drużynie Bosch Service Tech-Car, oparte na danych Podlaskiej Ligi Piłkarskiej i publicznym materiale wideo. Można tu filtrować po sezonie, wyszukiwać zawodników i sortować tabele po kliknięciu.</p>
      <div class="hero-stats" id="hero-stats"></div>
    </header>

    <div class="toolbar-sentinel" id="toolbar-sentinel" aria-hidden="true"></div>
    <div class="toolbar" id="toolbar">
      <div class="toolbar-mobile">
        <div class="toolbar-mobile-bar">
          <div class="toolbar-mobile-copy">
            <div class="toolbar-mobile-label">Menu mobilne</div>
            <div class="toolbar-summary" id="toolbar-summary"></div>
          </div>
          <button id="toolbar-toggle" class="toolbar-toggle" type="button" aria-expanded="false" aria-controls="toolbar-panel" aria-label="Otwórz filtry i nawigację">
            <span class="toolbar-toggle-box" aria-hidden="true"><span></span><span></span><span></span></span>
          </button>
        </div>
      </div>
      <div class="toolbar-backdrop" id="toolbar-backdrop"></div>
      <div class="toolbar-panel-inline" id="toolbar-panel-inline">
      <div class="toolbar-panel" id="toolbar-panel">
        <div class="toolbar-panel-head">
          <div>
            <div class="toolbar-mobile-label">Menu</div>
            <div class="toolbar-panel-title">Filtry i nawigacja</div>
          </div>
          <button id="toolbar-close" class="toolbar-close" type="button" aria-label="Zamknij menu">×</button>
        </div>
        <div class="toolbar-range">
          <div class="range-block">
            <div class="toolbar-mobile-label">Zakres statystyk zbiorczych</div>
            <div class="range-help">Łącz dowolnie grupy sezonów, lata i konkretne sezony. Strona przeliczy zbiorcze podsumowanie dla aktywnego zakresu.</div>
            <div class="range-row">
              <div class="range-title">Szybkie grupy</div>
              <div class="chip-group" id="group-chips"></div>
            </div>
            <div class="range-row">
              <div class="range-title">Roczniki</div>
              <div class="chip-group" id="year-chips"></div>
            </div>
            <div class="range-row">
              <div class="range-title">Konkretne sezony</div>
              <div class="chip-group" id="season-chips"></div>
            </div>
            <div class="range-row">
              <div class="chip-group">
                <button id="range-all" class="chip-btn" type="button">Wszystkie sezony</button>
              </div>
            </div>
          </div>
        </div>
        <div class="toolbar-grid">
          <div class="control">
            <label for="query-filter">Wyszukiwanie</label>
            <input id="query-filter" type="search" placeholder="Szukaj zawodnika, rywala, sezonu, meczu...">
          </div>
          <div class="control">
            <label for="status-filter">Status Zawodnika</label>
            <select id="status-filter">
              <option value="all">Wszyscy</option>
              <option value="obecny">Tylko obecni</option>
              <option value="archiwalny">Tylko archiwalni</option>
            </select>
          </div>
          <div class="control">
            <label for="video-filter">Filtr Wideo</label>
            <select id="video-filter">
              <option value="all">Wszystko</option>
              <option value="with">Tylko z wideo</option>
              <option value="without">Tylko bez wideo</option>
              <option value="full">Tylko pełne mecze</option>
            </select>
          </div>
          <div class="control">
            <label>&nbsp;</label>
            <button id="reset-filters" type="button">Resetuj filtry</button>
          </div>
        </div>
        <nav class="nav">
          <a href="#overview">Przegląd</a>
          <a href="#seasons">Sezony</a>
          <a href="#splits">Splity</a>
          <a href="#control">Kontrola</a>
          <a href="#players">Zawodnicy</a>
          <a href="#matches">Mecze</a>
          <a href="#opponents">Rywalizacja</a>
          <a href="#video">Wideo</a>
          <a href="#recommendations">Rekomendacje</a>
        </nav>
      </div>
      </div>
    </div>

    <div class="toolbar-fly" id="toolbar-fly" aria-hidden="true">
      <div class="toolbar-fly-shell">
        <div class="toolbar-compact">
          <div class="toolbar-compact-copy">
            <div class="toolbar-compact-title">Aktywny zakres</div>
            <div class="toolbar-compact-summary" id="toolbar-fly-summary"></div>
          </div>
          <div class="toolbar-compact-actions">
            <button id="toolbar-desktop-toggle" class="toolbar-compact-btn" type="button" aria-expanded="false" aria-controls="toolbar-panel">Rozwiń filtry</button>
          </div>
        </div>
        <div class="toolbar-fly-panel" id="toolbar-fly-panel"></div>
      </div>
    </div>

    <section class="section" id="overview">
      <div class="head"><h2>Przegląd</h2><p>Najważniejsze karty i legenda skrótów. Wybór sezonu przelicza karty sezonowe i filtruje tabele, które mają sens sezonowy.</p></div>
      <div class="body">
        <div class="cards" id="summary-cards"></div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Legenda Skrótów</h3><div class="meta">Skróty używane w całym dashboardzie</div></div>
          <div id="legend-table"></div>
        </div>
        <div class="dense-grid dense-2" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Słownik Pojęć</h3><div class="meta">Rozwinięcie nieoczywistych terminów analitycznych</div></div>
            <div id="concept-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Odzyskane Profile Ukryte</h3><div class="meta">Anonimowe ID rozpoznane po archiwalnych składach</div></div>
            <div id="hidden-table"></div>
          </div>
        </div>
        <div class="chapter-note" id="overview-note"></div>
      </div>
    </section>

    <section class="section" id="seasons">
      <div class="head"><h2>Sezony</h2><p>Kliknij kartę sezonu, aby ustawić filtr dla całej strony. Tabele można sortować kliknięciem w nagłówek kolumny.</p></div>
      <div class="body">
        <div class="chart-grid">
          <div class="chart"><h3>Punkty w sezonach</h3><div id="points-chart"></div></div>
          <div class="chart"><h3>PPG w sezonach</h3><div id="ppg-chart"></div></div>
          <div class="chart"><h3>Pierwszy gol Bosch</h3><div id="first-goal-chart"></div></div>
          <div class="chart"><h3>Pokrycie wideo</h3><div id="video-chart"></div></div>
        </div>
        <div class="season-grid" id="season-cards"></div>
        <div class="split split-wide" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Sezony ligowe</h3><div class="meta" id="season-meta"></div></div>
            <div id="season-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Scorecard awansu</h3><div class="meta">Najkrótsza odpowiedź: ile brakuje do I ligi?</div></div>
            <div id="scorecard-table"></div>
          </div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card">
            <div class="table-top"><h3>Benchmark Awansu</h3><div class="meta">Bosch kontra próg 2. miejsca</div></div>
            <div id="benchmark-table"></div>
          </div>
          <div class="table-card">
            <div class="table-top"><h3>Peak vs Bieżący Sezon</h3><div class="meta">Najmocniejszy Bosch kontra obecny poziom</div></div>
            <div id="peak-table"></div>
          </div>
        </div>
        <div class="chapter-note" id="seasons-note"></div>
      </div>
    </section>

    <section class="section" id="splits">
      <div class="head"><h2>Splity i Fazy Gry</h2><p>Ten rozdział rozbija Bosch na porównania hali z orlikiem, mecze z górą i dołem tabeli, stany do przerwy, sposób zapisu meczu w bazie ligi oraz rozkład minut goli. To tutaj opisane są mniej oczywiste pojęcia typu <span class="term" tabindex="0" data-tip="Split to po prostu podział danych na porównywalne grupy. Split konkurencyjności rozbija mecze na rywali z górnej i dolnej połowy tabeli, żeby sprawdzić, czy zespół daje liczby także przeciw mocniejszym.">split konkurencyjności</span>.</p></div>
      <div class="body">
        <div class="chart-grid">
          <div class="chart"><h3>Rozkład Minut Goli · Historia</h3><div id="timing-all-chart"></div></div>
          <div class="chart"><h3>Rozkład Minut Goli · Bieżący Sezon</h3><div id="timing-current-chart"></div></div>
          <div class="chart"><h3>Peak vs Teraz</h3><div id="peak-chart"></div></div>
          <div class="chart"><h3>Split Powierzchni</h3><div id="surface-chart"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Hala vs Orlik</h3><div class="meta">Historia Bosch według powierzchni</div></div><div id="surface-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Slot zapisu · Historia</h3><div class="meta">Bosch jako 1. lub 2. zespół w technicznym wpisie meczu w bazie ligi</div></div><div id="slot-all-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Slot zapisu · Bieżący Sezon</h3><div class="meta">Czy techniczny sposób zapisania meczu coś zmienia w obecnej kampanii</div></div><div id="slot-current-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Stan do Przerwy · Historia</h3><div class="meta">Jak wynik po pierwszej połowie przekłada się na punkty</div></div><div id="halftime-all-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Stan do Przerwy · Bieżący Sezon</h3><div class="meta">Czy Bosch umie odwracać słabsze pierwsze połowy</div></div><div id="halftime-current-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Split Konkurencyjności · Bieżący</h3><div class="meta">Top half kontra Bottom half</div></div><div id="tier-current-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Split Konkurencyjności · Peak</h3><div class="meta">Jak wyglądał Bosch w swoim historycznym maksimum</div></div><div id="tier-peak-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Peak vs Teraz · Tabela</h3><div class="meta">Najważniejsze luki jakościowe rozpisane wprost</div></div><div id="peak-compare-table"></div></div>
        </div>
        <div class="chapter-note" id="splits-note"></div>
      </div>
    </section>

    <section class="section" id="control">
      <div class="head"><h2>Kontrola Meczu</h2><p>Jak Bosch wchodzi w mecz, jak punktuje w spotkaniach stykowych i jak szeroko rozłożona jest produkcja.</p></div>
      <div class="body">
        <div class="split">
          <div class="table-card"><div class="table-top"><h3>Pierwszy gol i reakcja</h3><div class="meta">Sezony ligowe</div></div><div id="state-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Mecze stykowe</h3><div class="meta">Remisy i mecze rozstrzygnięte jedną bramką</div></div><div id="close-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Ciągłość kadry</h3><div class="meta">Stabilność rdzenia</div></div><div id="continuity-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Koncentracja produkcji</h3><div class="meta">Jak szeroko rozłożone są gole i punkty</div></div><div id="concentration-table"></div></div>
        </div>
        <div class="chapter-note" id="control-note"></div>
      </div>
    </section>

    <section class="section" id="players">
      <div class="head"><h2>Zawodnicy</h2><p>Bieżący liderzy oraz pełna tabela zawodników z możliwością wyszukiwania i filtrowania po statusie.</p></div>
      <div class="body">
        <div class="player-grid" id="current-player-cards"></div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Najwięcej występów</h3><div class="meta">Historia Bosch</div></div><div id="apps-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Największa produkcja ofensywna</h3><div class="meta">Historia Bosch</div></div><div id="points-table"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Karty zawodników</h3><div class="meta">Sortowalne i filtrowalne</div></div>
          <div id="player-cards-table"></div>
        </div>
        <div class="table-card" style="margin-top:16px">
          <div class="table-top"><h3>Partnerstwa Zawodników</h3><div class="meta">Które duety dają najwięcej punktów na mecz</div></div>
          <div id="partnership-table"></div>
        </div>
        <div class="chapter-note" id="players-note"></div>
      </div>
    </section>

    <section class="section" id="matches">
      <div class="head"><h2>Pełny Log Meczów</h2><p>Oficjalne mecze Bosch w jednej bazie: wynik, rezultat, stan do przerwy, sposób zapisu meczu w bazie ligi, pokrycie wideo i link do wydarzenia. To główna tabela robocza do filtrowania całej historii.</p></div>
      <div class="body">
        <div class="table-card">
          <div class="table-top"><h3>Oficjalne Mecze Bosch</h3><div class="meta">Chronologia całej historii dostępnej w publicznej bazie danych ligi</div></div>
          <div id="match-log-table"></div>
        </div>
        <div class="chapter-note" id="matches-note"></div>
      </div>
    </section>

    <section class="section" id="opponents">
      <div class="head"><h2>Rywalizacja</h2><p>Head-to-head, najlepsze i najgorsze wyniki oraz benchmark awansu.</p></div>
      <div class="body">
        <div class="table-card"><div class="table-top"><h3>Head-to-head</h3><div class="meta">Najczęściej spotykani rywale</div></div><div id="h2h-table"></div></div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Najwyższe zwycięstwa</h3><div class="meta">Top dodatnich rekordów</div></div><div id="best-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Najcięższe porażki</h3><div class="meta">Top ujemnych rekordów</div></div><div id="worst-table"></div></div>
        </div>
        <div class="chapter-note" id="opponents-note"></div>
      </div>
    </section>

    <section class="section" id="video">
      <div class="head"><h2>Wideo</h2><p>Biblioteka publicznych nagrań Bosch: pokrycie sezonów, rekomendowane materiały i pełna lista sparowanych meczów.</p></div>
      <div class="body">
        <div class="split">
          <div class="table-card"><div class="table-top"><h3>Pokrycie sezonów wideo</h3><div class="meta">Ile oficjalnych meczów ma publiczny materiał</div></div><div id="video-season-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Profil Kanałów</h3><div class="meta">Które źródło daje ile materiału i z jakiego okresu</div></div><div id="channel-table"></div></div>
        </div>
        <div class="split" style="margin-top:16px">
          <div class="table-card"><div class="table-top"><h3>Priorytetowe mecze do obejrzenia</h3><div class="meta">Najcenniejsze analitycznie materiały</div></div><div id="recommended-table"></div></div>
          <div class="table-card"><div class="table-top"><h3>Materiały niedopasowane</h3><div class="meta">Filmy Bosch bez pewnego przypisania do oficjalnego meczu</div></div><div id="unmatched-table"></div></div>
        </div>
        <div class="table-card" style="margin-top:16px"><div class="table-top"><h3>Oficjalne mecze dopasowane do wideo</h3><div class="meta">Pełna biblioteka publicznych nagrań Bosch</div></div><div id="matched-table"></div></div>
        <div class="chapter-note" id="video-note"></div>
        <div class="foot">Wynik zawsze jest zapisany z perspektywy Bosch. Zapis „Bosch jako 1. zespół / 2. zespół” oznacza wyłącznie kolejność drużyn w technicznym wpisie meczu w bazie ligi.</div>
      </div>
    </section>

    <section class="section" id="recommendations">
      <div class="head"><h2>Rekomendacje</h2><p>Końcowe wnioski wdrożeniowe pod awans do I ligi. To sekcja decyzyjna: co poprawić, po co i po czym poznamy postęp.</p></div>
      <div class="body">
        <div class="reco-grid" id="recommendation-cards"></div>
        <div class="chapter-note" id="recommendations-note"></div>
      </div>
    </section>
  </div>
  <div id="global-tooltip" class="tooltip-layer" aria-hidden="true"></div>

  <script id="report-data" type="application/json">__REPORT_JSON__</script>
  <script id="video-data" type="application/json">__VIDEO_JSON__</script>
  <script>
    const REPORT=JSON.parse(document.getElementById('report-data').textContent);
    const VIDEO=JSON.parse(document.getElementById('video-data').textContent);
    const LEGEND=[["KPI","kluczowy wskaźnik efektywności"],["PPG","punkty na mecz"],["Pkt","punkty"],["Poz.","pozycja w tabeli"],["M","mecze"],["W / R / P","wygrane / remisy / porażki"],["RB","różnica bramek"],["CS","clean sheets, czyli czyste konta"],["G","gole"],["A","asysty"],["G+A","gole plus asysty"],["G+A/M","gole plus asysty na mecz"],["MVP","piłkarz meczu"],["Top6","liczba oznaczeń top6 w publicznej bazie ligi"],["ŻK / CZK","żółte kartki / czerwone kartki"],["HT","wynik do przerwy"],["API ligi","techniczny interfejs i baza danych strony ligi"],["1. gol Bosch %","odsetek meczów, w których Bosch zdobył pierwszą bramkę"],["PPG po 1:0","średnia punktów po strzeleniu pierwszego gola"],["PPG po 0:1","średnia punktów po stracie pierwszego gola"],["Top half / Bottom half","górna i dolna połowa tabeli"]];
    const TERMS={KPI:'Kluczowy wskaźnik efektywności. W tym raporcie to liczba, która szybko mówi, czy Bosch jest blisko poziomu awansu.',PPG:'Punkty na mecz. Pozwala porównywać sezony o różnej liczbie spotkań.',Pkt:'Punkty w tabeli ligowej.','Poz.':'Pozycja Bosch w tabeli sezonu.',M:'Liczba meczów.','W / R / P':'Wygrane, remisy i porażki.',RB:'Różnica bramek, czyli gole strzelone minus gole stracone.',CS:'Clean sheets, czyli mecze bez straconej bramki.',G:'Gole zawodnika lub drużyny.',A:'Asysty zawodnika.','G+A':'Gole plus asysty, czyli pełna produkcja ofensywna zawodnika.','G+A/M':'Średnia produkcja goli i asyst na jeden mecz.',MVP:'Piłkarz meczu według publicznych oznaczeń ligi.',Top6:'Dodatkowe wyróżnienie w publicznej bazie ligi.',API:'API to techniczny sposób, w jaki strona ligi udostępnia dane. W praktyce możesz czytać to po prostu jako bazę danych strony ligi.','API ligi':'Techniczny interfejs i baza danych strony ligi. W tym projekcie to źródło oficjalnych meczów, tabel i profili.','ŻK / CZK':'Żółte i czerwone kartki.',HT:'Wynik do przerwy. Pozwala ocenić, jak Bosch zaczyna spotkania.','1. gol Bosch %':'Odsetek meczów, w których Bosch zdobył pierwszą bramkę.','PPG po 1:0':'Średnia punktów, gdy Bosch strzela pierwszy gol.','PPG po 0:1':'Średnia punktów, gdy pierwszy gol strzela rywal.','Top half / Bottom half':'Górna i dolna połowa tabeli.','Mecz stykowy':'Remis albo mecz rozstrzygnięty jedną bramką. To najlepszy test zarządzania detalem.','Mecze stykowe':'Remisy albo mecze rozstrzygnięte jedną bramką. Pokazują, jak drużyna radzi sobie w końcówkach i pod presją.','Split konkurencyjności':'Podział meczów na rywali z górnej i dolnej połowy tabeli.','Ciągłość kadry':'Odsetek zawodników, którzy wrócili z poprzedniego sezonu.','Ciągłość':'Skrót od ciągłości kadry, czyli procentu zawodników zachowanych z poprzedniego sezonu.','Koncentracja produkcji':'Pokazuje, czy gole i punkty są szeroko rozłożone, czy skupione w kilku nazwiskach.','Slot API':'Informacja techniczna o tym, czy Bosch był zapisany jako pierwszy czy drugi zespół w bazie ligi. Nie mówi nic o sile drużyny, tylko o kolejności zapisu meczu.',Slot:'Skrót od sposobu zapisu meczu w bazie ligi. Pokazuje techniczną kolejność drużyn w danych.','Profil niepubliczny':'Zawodnik odzyskany z anonimowego identyfikatora ligi.','Archiwalny':'Zawodnik bez występu w bieżącym sezonie Hala 2025/2026.','Benchmark awansu':'Poziom drużyny z 2. miejsca, czyli realnego progu wejścia wyżej.','Wypuszczone pkt':'Punkty oddane po objęciu prowadzenia. To koszt niedomkniętych meczów.','Top1 goli':'Odsetek wszystkich goli Bosch strzelonych przez najlepszego strzelca.','Top3 goli':'Odsetek wszystkich goli Bosch strzelonych przez trzech najskuteczniejszych zawodników.','Top5 G+A':'Odsetek całej produkcji goli i asyst wygenerowanej przez pięciu najlepszych zawodników.','Gole/m':'Gole strzelone na mecz.','Stracone/m':'Gole stracone na mecz.','Pokrycie %':'Odsetek oficjalnych meczów, które mają publicznie dostępne wideo.',Segmenty:'Liczba dopasowanych fragmentów lub części materiału wideo do konkretnego spotkania.'};
    const CONCEPTS=[['Mecz stykowy','Remis albo mecz rozstrzygnięty jedną bramką.','To najlepszy test jakości końcówki i zarządzania detalem.'],['Split konkurencyjności','Podział meczów na rywali z górnej i dolnej połowy tabeli.','Pokazuje, czy Bosch daje liczby także przeciw mocniejszym.'],['Ciągłość kadry','Odsetek zawodników, którzy wrócili z poprzedniego sezonu.','Im wyższa, tym łatwiej o automatyzmy i stabilność.'],['Koncentracja produkcji','Jak duża część goli i G+A pochodzi od małej grupy zawodników.','Pokazuje, czy Bosch jest szeroki ofensywnie, czy zależny od kilku nazwisk.'],['API ligi','Techniczna baza danych i interfejs strony ligi.','W tym raporcie oznacza źródło oficjalnych meczów, tabel i profili.'],['Slot API','Układ techniczny rekordu: Bosch jako 1. albo 2. zespół.','Pomaga sprawdzić, czy sposób zapisu meczu nie myli interpretacji.'],['Benchmark awansu','Poziom drużyny z 2. miejsca.','To najprostsza odpowiedź, ile brakuje Bosch do realnej walki o awans.'],['Wypuszczone pkt','Punkty oddane mimo wcześniejszego prowadzenia.','To najszybsze źródło poprawy bez rewolucji kadrowej.'],['Pokrycie wideo','Odsetek meczów z publicznym nagraniem.','Im wyższe pokrycie, tym łatwiej łączyć liczby z realnym obrazem gry.']];
    const state={query:'',status:'all',sort:{}},renderers=[];
    state.video='all';
    state.groups=new Set();
    state.years=new Set();
    state.seasons=new Set();
    const GROUP_OPTIONS=[{id:'current',label:'Bieżący'},{id:'peak',label:'Peak historyczny'},{id:'hala',label:'Wszystkie hale'},{id:'orlik',label:'Wszystkie orliki'}];
    const stateMap=new Map(REPORT.state_rows.map(r=>[String(r.sid),r])),closeMap=new Map(REPORT.close_game_rows.map(r=>[String(r.sid),r])),contMap=new Map(REPORT.continuity_rows.map(r=>[String(r.sid),r])),concMap=new Map(REPORT.concentration_rows.map(r=>[String(r.sid),r])),videoMap=new Map(VIDEO.season_rows.map(r=>[String(r.sid),r])),benchmarkMap=new Map(REPORT.benchmark.map(r=>[String(r.season_id),r])),playerCardMap=new Map(REPORT.player_cards.map(r=>[r.player_id,r]));
    const tooltipLayer=document.getElementById('global-tooltip');
    let activeTooltipTerm=null;
    const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    const escAttr=s=>esc(s).replaceAll("'","&#39;");
    const norm=s=>String(s??'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
    const num=v=>{if(typeof v==='number')return v;const n=Number(String(v).replace('%','').replace(',','.'));return Number.isNaN(n)?null:n};
    const safeNum=(v,fallback=0)=>{const n=num(v);return n===null?fallback:n};
    const tip=(label,key=label)=>`<span class="term" tabindex="0" data-tip="${escAttr(TERMS[key]||TERMS[label]||'')}">${esc(label)}</span>`;
    const formatDate=value=>{if(!value)return'';const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleDateString('pl-PL')};
    const prettyNum=(value,decimals=2)=>{if(value==null||!Number.isFinite(value))return'-';const rounded=Number(value.toFixed(decimals));return String(rounded).replace(/\\.0$/,'')};
    const extractSeasonYear=label=>{const matches=String(label??'').match(/\\d{4}/g);return matches&&matches.length?matches[matches.length-1]:'0'};
    const seasonMeta=REPORT.season_rows.map(r=>({...r,sid_str:String(r.sid),surface:norm(r.season).includes('hala')?'hala':'orlik',year_key:extractSeasonYear(r.season)}));
    const seasonMetaMap=new Map(seasonMeta.map(r=>[r.sid_str,r]));
    const allSeasonIds=seasonMeta.map(r=>r.sid_str);
    const yearOptions=[...new Set(seasonMeta.map(r=>r.year_key))].sort((a,b)=>Number(a)-Number(b));
    const mobileCharts=()=>window.matchMedia('(max-width: 720px)').matches;
    const wrapLabel=(value,maxChars=14)=>{const words=String(value??'').split(/\\s+/).filter(Boolean);if(!words.length)return[''];const lines=[];let line='';for(const word of words){const candidate=line?`${line} ${word}`:word;if(candidate.length<=maxChars||!line){line=candidate}else{lines.push(line);line=word}}if(line)lines.push(line);return lines.slice(0,3)};
    const svgLabel=(x,y,value,{maxChars=14,lineHeight=12,fontSize=10,fill='#5b6b7d'}={})=>{const lines=wrapLabel(value,maxChars);const startY=y-((lines.length-1)*lineHeight)/2;return `<text x="${x}" y="${startY}" text-anchor="middle" font-size="${fontSize}" fill="${fill}">${lines.map((line,index)=>`<tspan x="${x}" dy="${index===0?0:lineHeight}">${esc(line)}</tspan>`).join('')}</text>`};
    const rowSeason=r=>String(r.sid??r.season_id??'');
    const toggleSetValue=(set,value)=>{set.has(value)?set.delete(value):set.add(value)};
    function selectedSeasonIds(){
      const ids=new Set();
      if(state.groups.has('current')) ids.add(String(REPORT.current_season_id));
      if(state.groups.has('peak')) ids.add(String(REPORT.peak_season_id));
      if(state.groups.has('hala')) seasonMeta.filter(r=>r.surface==='hala').forEach(r=>ids.add(r.sid_str));
      if(state.groups.has('orlik')) seasonMeta.filter(r=>r.surface==='orlik').forEach(r=>ids.add(r.sid_str));
      if(state.years.size) seasonMeta.filter(r=>state.years.has(r.year_key)).forEach(r=>ids.add(r.sid_str));
      if(state.seasons.size) state.seasons.forEach(id=>ids.add(id));
      if(!ids.size) allSeasonIds.forEach(id=>ids.add(id));
      return ids;
    }
    const selectedSeasonRows=()=>seasonMeta.filter(r=>selectedSeasonIds().has(r.sid_str));
    const seasonRow=()=>selectedSeasonRows().length===1?selectedSeasonRows()[0]:null;
    const passSeason=r=>selectedSeasonIds().has(rowSeason(r));
    const activeRangeLabel=()=>{const rows=selectedSeasonRows();if(!state.groups.size&&!state.years.size&&!state.seasons.size)return'Wszystkie sezony';if(rows.length===1)return rows[0].season;if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('hala'))return'Wszystkie hale';if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('orlik'))return'Wszystkie orliki';if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('current'))return REPORT.current_season_name;if(state.groups.size===1&&!state.years.size&&!state.seasons.size&&state.groups.has('peak'))return REPORT.peak_season_name;if(!state.groups.size&&state.years.size===1&&!state.seasons.size)return`Rok ${[...state.years][0]}`;return`${rows.length} sezonów`};
    const passQuery=r=>!state.query||norm(JSON.stringify(r)).includes(norm(state.query));
    const passVideo=r=>{if(state.video==='all')return true;const withVideo=Number(r.video_count??r.matches_with_video??r.matched??0)>0;const coverage=norm(r.coverage_type??'');if(state.video==='with')return withVideo;if(state.video==='without'){if(r.matches_with_video!=null)return Number(r.matches_with_video)===0;if(r.video_count!=null)return Number(r.video_count)===0;if(r.matched!=null&&r.unmatched!=null)return Number(r.matched)===0;return !withVideo}if(state.video==='full')return coverage.includes('pełne')||coverage.includes('pelne')||Number(r.full_matches??0)>0;return true};
    function renderRangeControls(){
      const groupEl=document.getElementById('group-chips'),yearEl=document.getElementById('year-chips'),seasonEl=document.getElementById('season-chips');
      if(groupEl)groupEl.innerHTML=GROUP_OPTIONS.map(item=>`<button type="button" class="chip-btn ${state.groups.has(item.id)?'active':''}" data-kind="group" data-value="${item.id}">${esc(item.label)}</button>`).join('');
      if(yearEl)yearEl.innerHTML=yearOptions.map(year=>`<button type="button" class="chip-btn ${state.years.has(year)?'active':''}" data-kind="year" data-value="${year}">Rok ${esc(year)}</button>`).join('');
      if(seasonEl)seasonEl.innerHTML=seasonMeta.map(row=>`<button type="button" class="chip-btn ${state.seasons.has(row.sid_str)?'active':''}" data-kind="season" data-value="${row.sid_str}">${esc(row.season)}</button>`).join('');
    }
    function bindControls(){
      document.getElementById('query-filter').addEventListener('input',e=>{state.query=e.target.value;refresh()});
      document.getElementById('status-filter').addEventListener('change',e=>{state.status=e.target.value;refresh()});
      document.getElementById('video-filter').addEventListener('change',e=>{state.video=e.target.value;refresh()});
      [['group-chips','group',state.groups],['year-chips','year',state.years],['season-chips','season',state.seasons]].forEach(([id,kind,set])=>{document.getElementById(id)?.addEventListener('click',e=>{const btn=e.target.closest(`button[data-kind="${kind}"]`);if(!btn)return;toggleSetValue(set,btn.dataset.value);sync();refresh()})});
      document.getElementById('range-all')?.addEventListener('click',()=>{state.groups.clear();state.years.clear();state.seasons.clear();sync();refresh()});
      document.getElementById('reset-filters').addEventListener('click',()=>{state.query='';state.status='all';state.video='all';state.groups.clear();state.years.clear();state.seasons.clear();sync();refresh()});
    }
    let toolbarObserver=null;
    const isMobileToolbar=()=>window.matchMedia('(max-width: 900px)').matches;
    function moveToolbarPanel(targetId){
      const panel=document.getElementById('toolbar-panel');
      const target=document.getElementById(targetId);
      if(panel&&target&&panel.parentElement!==target) target.appendChild(panel);
    }
    function updateToolbarSummary(){
      const summary=document.getElementById('toolbar-summary');
      const compactSummary=document.getElementById('toolbar-fly-summary');
      const seasonLabel=activeRangeLabel();
      const statusLabel=({all:'wszyscy',obecny:'obecni',archiwalny:'archiwalni'})[state.status]||state.status;
      const videoLabel=({all:'wideo: wszystko',with:'wideo: tylko z nagraniem',without:'wideo: bez nagrania',full:'wideo: pełne mecze'})[state.video]||state.video;
      const queryPart=state.query?`szukaj: ${state.query.length>18?`${state.query.slice(0,18)}…`:state.query}`:'';
      const text=[seasonLabel,statusLabel,videoLabel,queryPart].filter(Boolean).join(' • ');
      if(summary) summary.textContent=text;
      if(compactSummary) compactSummary.textContent=text;
    }
    function setToolbarOpen(open){
      const toolbar=document.getElementById('toolbar');
      const toggle=document.getElementById('toolbar-toggle');
      if(!toolbar||!toggle) return;
      moveToolbarPanel('toolbar-panel-inline');
      const expanded=isMobileToolbar()&&open;
      toolbar.classList.toggle('open',expanded);
      toggle.setAttribute('aria-expanded',expanded?'true':'false');
      toggle.setAttribute('aria-label',expanded?'Zamknij filtry i nawigację':'Otwórz filtry i nawigację');
      document.body.classList.toggle('toolbar-lock',expanded);
      updateToolbarSummary();
    }
    function updateDesktopToggle(){
      const fly=document.getElementById('toolbar-fly');
      const desktopToggle=document.getElementById('toolbar-desktop-toggle');
      if(!fly||!desktopToggle) return;
      const expanded=fly.classList.contains('open');
      desktopToggle.textContent=expanded?'Zwiń filtry':'Rozwiń filtry';
      desktopToggle.setAttribute('aria-expanded',expanded?'true':'false');
    }
    function setDesktopFlyOpen(open){
      const fly=document.getElementById('toolbar-fly');
      if(!fly||isMobileToolbar()){
        moveToolbarPanel('toolbar-panel-inline');
        updateDesktopToggle();
        return;
      }
      const expanded=Boolean(open)&&fly.classList.contains('active');
      fly.classList.toggle('open',expanded);
      moveToolbarPanel(expanded?'toolbar-fly-panel':'toolbar-panel-inline');
      updateDesktopToggle();
    }
    function syncDesktopFly(active){
      const fly=document.getElementById('toolbar-fly');
      if(!fly||isMobileToolbar()){
        fly?.classList.remove('active','open');
        fly?.setAttribute('aria-hidden','true');
        moveToolbarPanel('toolbar-panel-inline');
        updateDesktopToggle();
        return;
      }
      fly.classList.toggle('active',active);
      fly.setAttribute('aria-hidden',active?'false':'true');
      if(!active) setDesktopFlyOpen(false);
      else updateDesktopToggle();
    }
    function installToolbarObserver(){
      const sentinel=document.getElementById('toolbar-sentinel');
      if(toolbarObserver){
        toolbarObserver.disconnect();
        toolbarObserver=null;
      }
      if(!sentinel||isMobileToolbar()){
        syncDesktopFly(false);
        return;
      }
      toolbarObserver=new IntersectionObserver(entries=>{
        const entry=entries[0];
        syncDesktopFly(!entry.isIntersecting);
      },{threshold:[0],rootMargin:'-10px 0px 0px 0px'});
      toolbarObserver.observe(sentinel);
    }
    function syncToolbarState(){
      setToolbarOpen(false);
      setDesktopFlyOpen(false);
      installToolbarObserver();
    }
    function initToolbar(){
      const toolbar=document.getElementById('toolbar');
      const toggle=document.getElementById('toolbar-toggle');
      const close=document.getElementById('toolbar-close');
      const backdrop=document.getElementById('toolbar-backdrop');
      const desktopToggle=document.getElementById('toolbar-desktop-toggle');
      const fly=document.getElementById('toolbar-fly');
      if(!toolbar||!toggle) return;
      const mq=window.matchMedia('(max-width: 900px)');
      toggle.addEventListener('click',()=>setToolbarOpen(!toolbar.classList.contains('open')));
      close?.addEventListener('click',()=>setToolbarOpen(false));
      backdrop?.addEventListener('click',()=>setToolbarOpen(false));
      desktopToggle?.addEventListener('click',()=>{
        if(isMobileToolbar()) return;
        setDesktopFlyOpen(!fly?.classList.contains('open'));
      });
      mq.addEventListener('change',()=>syncToolbarState());
      window.addEventListener('resize',()=>installToolbarObserver());
      document.addEventListener('keydown',e=>{
        if(e.key==='Escape'&&mq.matches&&toolbar.classList.contains('open')) setToolbarOpen(false);
        if(e.key==='Escape'&&!mq.matches&&fly?.classList.contains('open')) setDesktopFlyOpen(false);
      });
      document.addEventListener('click',e=>{
        if(isMobileToolbar()||!fly?.classList.contains('open')) return;
        if(fly.contains(e.target)) return;
        setDesktopFlyOpen(false);
      });
      document.querySelectorAll('.nav a').forEach(link=>link.addEventListener('click',()=>{
        if(mq.matches) setToolbarOpen(false);
        if(!mq.matches) setDesktopFlyOpen(false);
      }));
      syncToolbarState();
    }
    function initResponsiveCharts(){
      let lastMode=mobileCharts();
      window.addEventListener('resize',()=>{const nextMode=mobileCharts();if(nextMode!==lastMode){lastMode=nextMode;refresh()}});
    }
    function placeTooltip(target){
      if(!target||!tooltipLayer)return;
      const text=target.dataset.tip||'';
      if(!text){hideTooltip();return}
      tooltipLayer.textContent=text;
      tooltipLayer.classList.add('show');
      tooltipLayer.setAttribute('aria-hidden','false');
      tooltipLayer.style.left='12px';
      tooltipLayer.style.top='12px';
      const margin=12;
      const rect=target.getBoundingClientRect();
      const tipRect=tooltipLayer.getBoundingClientRect();
      let left=rect.left+(rect.width/2)-(tipRect.width/2);
      left=Math.max(margin,Math.min(left,window.innerWidth-tipRect.width-margin));
      let top=rect.bottom+12;
      if(top+tipRect.height>window.innerHeight-margin) top=rect.top-tipRect.height-12;
      if(top<margin) top=Math.max(margin,Math.min(window.innerHeight-tipRect.height-margin,rect.bottom+12));
      tooltipLayer.style.left=`${left}px`;
      tooltipLayer.style.top=`${top}px`;
    }
    function showTooltip(target){activeTooltipTerm=target;placeTooltip(target)}
    function hideTooltip(){activeTooltipTerm=null;if(!tooltipLayer)return;tooltipLayer.classList.remove('show');tooltipLayer.setAttribute('aria-hidden','true')}
    function initTooltips(){
      document.addEventListener('mouseover',e=>{const term=e.target.closest?.('.term');if(term&&term.dataset.tip)showTooltip(term)});
      document.addEventListener('mouseout',e=>{if(!activeTooltipTerm)return;const next=e.relatedTarget&&e.relatedTarget.closest?e.relatedTarget.closest('.term'):null;if(next===activeTooltipTerm)return;if(e.target.closest?.('.term')===activeTooltipTerm)hideTooltip()});
      document.addEventListener('focusin',e=>{const term=e.target.closest?.('.term');if(term&&term.dataset.tip)showTooltip(term)});
      document.addEventListener('focusout',e=>{if(e.target.closest?.('.term')===activeTooltipTerm)hideTooltip()});
      window.addEventListener('scroll',()=>{if(activeTooltipTerm)placeTooltip(activeTooltipTerm)},true);
      window.addEventListener('resize',()=>{if(activeTooltipTerm)placeTooltip(activeTooltipTerm)});
    }
    function sync(){document.getElementById('query-filter').value=state.query;document.getElementById('status-filter').value=state.status;document.getElementById('video-filter').value=state.video;renderRangeControls();updateToolbarSummary()}
    const sumBy=(rows,pick)=>rows.reduce((acc,row)=>acc+safeNum(pick(row),0),0);
    const statusFor=(current,target,mode='high')=>{if(current==null||target==null||!Number.isFinite(current)||!Number.isFinite(target))return'luka';if(mode==='low'){if(current<=target)return'mocne';if(current<=target*1.1)return'blisko';return'luka'}if(current>=target)return'mocne';if(current>=target*0.9)return'blisko';return'luka'};
    const selectedMatchRows=()=>VIDEO.match_rows.filter(r=>selectedSeasonIds().has(String(r.sid)));
    function activeAggregate(){
      const seasonRows=selectedSeasonRows();
      const ids=new Set(seasonRows.map(r=>r.sid_str));
      const stateRows=REPORT.state_rows.filter(r=>ids.has(String(r.sid)));
      const closeRows=REPORT.close_game_rows.filter(r=>ids.has(String(r.sid)));
      const continuityRows=REPORT.continuity_rows.filter(r=>ids.has(String(r.sid)));
      const concentrationRows=REPORT.concentration_rows.filter(r=>ids.has(String(r.sid)));
      const videoRows=VIDEO.season_rows.filter(r=>ids.has(String(r.sid)));
      const benchmarkRows=REPORT.benchmark.filter(r=>ids.has(String(r.season_id)));
      const team={matches:sumBy(seasonRows,r=>r.matches),points:sumBy(seasonRows,r=>r.points),wins:sumBy(seasonRows,r=>r.wins),draws:sumBy(seasonRows,r=>r.draws),losses:sumBy(seasonRows,r=>r.losses),gf:sumBy(seasonRows,r=>r.gf),ga:sumBy(seasonRows,r=>r.ga),clean_sheets:sumBy(seasonRows,r=>r.clean_sheets),failed_to_score:sumBy(seasonRows,r=>r.failed_to_score)};
      team.gd=team.gf-team.ga;
      team.ppg=team.matches?team.points/team.matches:0;
      team.gfpg=team.matches?team.gf/team.matches:0;
      team.gapg=team.matches?team.ga/team.matches:0;
      const firstFor=sumBy(stateRows,r=>r.first_for),firstAgainst=sumBy(stateRows,r=>r.first_against),leadScoringPoints=stateRows.reduce((acc,row)=>acc+safeNum(row.first_for,0)*safeNum(row.ppg_when_scoring_first,0),0),leadConcedingPoints=stateRows.reduce((acc,row)=>acc+safeNum(row.first_against,0)*safeNum(row.ppg_when_conceding_first,0),0);
      const stateAgg={matches:team.matches,first_for:firstFor,first_against:firstAgainst,first_goal_share:team.matches?(firstFor/team.matches)*100:0,ppg_when_scoring_first:firstFor?leadScoringPoints/firstFor:0,ppg_when_conceding_first:firstAgainst?leadConcedingPoints/firstAgainst:0,points_dropped_from_leads:sumBy(stateRows,r=>r.points_dropped_from_leads)};
      const closeMatches=sumBy(closeRows,r=>r.close_matches),closeWins=sumBy(closeRows,r=>r.close_wins),closeDraws=sumBy(closeRows,r=>r.close_draws),closeLosses=sumBy(closeRows,r=>r.close_losses);
      const closeAgg={close_matches:closeMatches,close_wins:closeWins,close_draws:closeDraws,close_losses:closeLosses,close_ppg:closeMatches?((closeWins*3)+(closeDraws))/closeMatches:0};
      const continuityWeight=sumBy(continuityRows,r=>r.roster);
      const continuityAgg={roster:sumBy(continuityRows,r=>r.roster),returning:sumBy(continuityRows,r=>r.returning),newcomers:sumBy(continuityRows,r=>r.newcomers),departures:sumBy(continuityRows,r=>r.departures),continuity:continuityWeight?continuityRows.reduce((acc,row)=>acc+safeNum(row.continuity,0)*safeNum(row.roster,0),0)/continuityWeight:null};
      const totalGoals=Math.max(1,team.gf),totalMatches=Math.max(1,team.matches),concentrationAgg={scorers:sumBy(concentrationRows,r=>r.scorers),roster:sumBy(concentrationRows,r=>r.roster),top1_goal_share:(seasonRows.reduce((acc,row)=>acc+safeNum(row.gf,0)*(safeNum(concentrationMap(rowSeason(row))?.top1_goal_share,0)/100),0)/totalGoals)*100,top3_goal_share:(seasonRows.reduce((acc,row)=>acc+safeNum(row.gf,0)*(safeNum(concentrationMap(rowSeason(row))?.top3_goal_share,0)/100),0)/totalGoals)*100,top5_point_share:(concentrationRows.reduce((acc,row)=>acc+safeNum(row.top5_point_share,0)*safeNum(stateMap.get(String(row.sid))?.matches??seasonMetaMap.get(String(row.sid))?.matches,0),0)/Math.max(1,concentrationRows.reduce((acc,row)=>acc+safeNum(stateMap.get(String(row.sid))?.matches??seasonMetaMap.get(String(row.sid))?.matches,0),0)))};
      const videoAgg={matches_total:sumBy(videoRows,r=>r.matches_total),matches_with_video:sumBy(videoRows,r=>r.matches_with_video),minutes:sumBy(videoRows,r=>r.minutes),full_matches:sumBy(videoRows,r=>r.full_matches)};
      videoAgg.coverage_pct=videoAgg.matches_total?(videoAgg.matches_with_video/videoAgg.matches_total)*100:0;
      const benchmarkAgg={bosch_points:sumBy(benchmarkRows,r=>r.bosch_points),bosch_matches:sumBy(benchmarkRows,r=>r.bosch_matches),second_points:sumBy(benchmarkRows,r=>r.second_points),second_matches:sumBy(benchmarkRows,r=>r.second_matches)};
      benchmarkAgg.bosch_ppg=benchmarkAgg.bosch_matches?benchmarkAgg.bosch_points/benchmarkAgg.bosch_matches:null;
      benchmarkAgg.second_ppg=benchmarkAgg.second_matches?benchmarkAgg.second_points/benchmarkAgg.second_matches:null;
      benchmarkAgg.gap_ppg=benchmarkAgg.bosch_ppg!=null&&benchmarkAgg.second_ppg!=null?benchmarkAgg.second_ppg-benchmarkAgg.bosch_ppg:null;
      return{seasonRows,team,state:stateAgg,close:closeAgg,continuity:continuityAgg,concentration:concentrationAgg,video:videoAgg,benchmark:benchmarkAgg};
    }
    function concentrationMap(sid){return concMap.get(String(sid))||{}}
    function surfaceRowsActive(){const groups=[['hala','Hala'],['orlik','Orlik']];return groups.map(([surface,label])=>{const rows=selectedSeasonRows().filter(r=>r.surface===surface);if(!rows.length)return null;const matches=sumBy(rows,r=>r.matches),points=sumBy(rows,r=>r.points),gf=sumBy(rows,r=>r.gf),ga=sumBy(rows,r=>r.ga);return{label,seasons:rows.length,matches,points,ppg:matches?Number((points/matches).toFixed(2)):0,gfpg:matches?Number((gf/matches).toFixed(2)):0,gapg:matches?Number((ga/matches).toFixed(2)):0}}).filter(Boolean)}
    function scorecardRowsActive(){const agg=activeAggregate();const targetMap=new Map(REPORT.scorecard_rows.map(row=>[row[0],safeNum(row[2],0)]));const dropPerMatch=agg.team.matches?agg.state.points_dropped_from_leads/agg.team.matches:0;return[['PPG',prettyNum(agg.team.ppg),prettyNum(agg.benchmark.second_ppg??targetMap.get('PPG')),statusFor(agg.team.ppg,agg.benchmark.second_ppg??targetMap.get('PPG'),'high'),'zbiorczy próg 2. miejsca dla aktywnego zakresu'],['Gole stracone / mecz',prettyNum(agg.team.gapg),prettyNum(targetMap.get('Gole stracone / mecz')),statusFor(agg.team.gapg,targetMap.get('Gole stracone / mecz'),'low'),'ile Bosch traci w zaznaczonych sezonach'],['PPG w meczach stykowych',prettyNum(agg.close.close_ppg),prettyNum(targetMap.get('PPG w meczach stykowych')),statusFor(agg.close.close_ppg,targetMap.get('PPG w meczach stykowych'),'high'),'czy Bosch dowozi wyrównane spotkania'],['Pierwszy gol Bosch (%)',prettyNum(agg.state.first_goal_share,1),prettyNum(targetMap.get('Pierwszy gol Bosch (%)'),1),statusFor(agg.state.first_goal_share,targetMap.get('Pierwszy gol Bosch (%)'),'high'),'kontrola wejścia w mecz'],['Ciągłość kadry (%)',prettyNum(agg.continuity.continuity,1),prettyNum(targetMap.get('Ciągłość kadry (%)'),1),statusFor(agg.continuity.continuity,targetMap.get('Ciągłość kadry (%)'),'high'),'stabilność rdzenia w wybranym zakresie'],['Wypuszczone pkt z prowadzeń / mecz',prettyNum(dropPerMatch,2),prettyNum(targetMap.get('Wypuszczone pkt z prowadzeń / mecz'),2),statusFor(dropPerMatch,targetMap.get('Wypuszczone pkt z prowadzeń / mecz'),'low'),'jak często Bosch oddaje przewagę']].map(([metric,current,target,status,note])=>({metric,current,target,status,note}))}
    function peakComparisonRowsActive(){const agg=activeAggregate(),peakSeason=seasonMetaMap.get(String(REPORT.peak_season_id)),peakClose=closeMap.get(String(REPORT.peak_season_id))||{},peakContinuity=contMap.get(String(REPORT.peak_season_id))||{},peakConcentration=concMap.get(String(REPORT.peak_season_id))||{};return[['PPG',prettyNum(agg.team.ppg),prettyNum(peakSeason?.ppg)],['Gole/mecz',prettyNum(agg.team.gfpg),prettyNum(peakSeason?.gf/Math.max(1,peakSeason?.matches??1))],['Stracone/mecz',prettyNum(agg.team.gapg),prettyNum(peakSeason?.ga/Math.max(1,peakSeason?.matches??1))],['PPG w meczach stykowych',prettyNum(agg.close.close_ppg),prettyNum(peakClose.close_ppg)],['Ciągłość kadry',`${prettyNum(agg.continuity.continuity,1)}%`,`${prettyNum(peakContinuity.continuity,1)}%`],['Top3 udział goli',`${prettyNum(agg.concentration.top3_goal_share,1)}%`,`${prettyNum(peakConcentration.top3_goal_share,1)}%`]]}
    function h2hRowsActive(){const groups=new Map();selectedMatchRows().forEach(row=>{const key=`${row.opponent_id||row.opponent}`;if(!groups.has(key))groups.set(key,{opponent:row.display_opponent||row.opponent,matches:0,wins:0,draws:0,losses:0,gf:0,ga:0,seasons:new Set()});const item=groups.get(key);item.matches+=1;item.gf+=safeNum(row.gf,0);item.ga+=safeNum(row.ga,0);item.seasons.add(row.season);if(row.gf>row.ga)item.wins+=1;else if(row.gf<row.ga)item.losses+=1;else item.draws+=1});return[...groups.values()].map(item=>({...item,gd:item.gf-item.ga,ppg:item.matches?(((item.wins*3)+item.draws)/item.matches):0,seasons_label:[...item.seasons].sort((a,b)=>a.localeCompare(b,'pl',{numeric:true,sensitivity:'base'})).join(', ')}))}
    function resultsRowsActive(direction='best'){return[...selectedMatchRows()].map(row=>({...row,score:`${row.gf}:${row.ga}`,margin:row.gf-row.ga})).sort((a,b)=>direction==='best'?b.margin-a.margin:a.margin-b.margin)}
    function table(target,cols,rowsFn,opts={}){
      const el=document.getElementById(target); if(!el) return;
      const sort=state.sort[target]||{key:opts.defaultSort||cols[0].key,dir:opts.defaultDir||'desc'}; state.sort[target]=sort;
      function render(){
        let rows=rowsFn(); if(opts.season!==false) rows=rows.filter(passSeason); if(opts.query!==false) rows=rows.filter(passQuery); if(opts.video!==false) rows=rows.filter(passVideo); if(opts.filter) rows=rows.filter(opts.filter);
        const col=cols.find(c=>c.key===sort.key)||cols[0];
        rows=[...rows].sort((a,b)=>{const av=col.sort?col.sort(a):a[sort.key], bv=col.sort?col.sort(b):b[sort.key], an=num(av), bn=num(bv); let r=0; if(an!==null&&bn!==null) r=an-bn; else r=String(av??'').localeCompare(String(bv??''),'pl',{numeric:true,sensitivity:'base'}); return sort.dir==='asc'?r:-r});
        if(!rows.length){el.innerHTML='<div class="empty">Brak wyników dla aktywnych filtrów.</div>'; return}
        const useScroller=Boolean(opts.scroller&&rows.length>(opts.scrollerRows??10));
        const head=cols.map(c=>`<th><button type="button" data-key="${c.key}">${c.labelHtml||(TERMS[c.label]?tip(c.label,c.label):esc(c.label))}<span class="sort">${sort.key===c.key?(sort.dir==='asc'?'↑':'↓'):'↕'}</span></button></th>`).join('');
        const body=rows.map(r=>`<tr>${cols.map(c=>`<td data-label="${esc(c.label)}">${c.render?c.render(r):(r[c.key]??'')}</td>`).join('')}</tr>`).join('');
        el.innerHTML=`<div class="table-wrap ${useScroller?'scroller':''}"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
        el.querySelectorAll('th button').forEach(btn=>btn.addEventListener('click',()=>{const key=btn.dataset.key;if(sort.key===key)sort.dir=sort.dir==='asc'?'desc':'asc';else{sort.key=key;sort.dir='desc'};render()}));
      }
      renderers.push(render); render();
    }
    function hero(){const total=REPORT.season_rows.reduce((a,r)=>a+r.matches,0),w=REPORT.season_rows.reduce((a,r)=>a+r.wins,0),d=REPORT.season_rows.reduce((a,r)=>a+r.draws,0),l=REPORT.season_rows.reduce((a,r)=>a+r.losses,0),videoPct=((VIDEO.matched_rows.length/Math.max(1,total))*100).toFixed(0);document.getElementById('hero-stats').innerHTML=[['Mecze ligowe',total],['Bilans',`${w}-${d}-${l}`],['Peak',REPORT.peak_season_name],['Bieżący sezon',REPORT.current_season_name],['Aktywny zakres',activeRangeLabel()],['Pokrycie wideo',`${videoPct}%`]].map(([k,v])=>`<div class="hero-card"><div class="hero-label">${esc(k)}</div><div class="hero-value">${esc(v)}</div></div>`).join('')}
    function summary(){const el=document.getElementById('summary-cards');const s=seasonRow();const agg=activeAggregate();let rows=[]; if(s){const st=stateMap.get(String(s.sid))||{},cl=closeMap.get(String(s.sid))||{},ct=contMap.get(String(s.sid))||{},cn=concMap.get(String(s.sid))||{},vd=videoMap.get(String(s.sid))||{};rows=[['Sezon',s.season,s.table_title],['Pozycja',s.pos,`${s.points} pkt`],['Bilans',`${s.wins}-${s.draws}-${s.losses}`,`${s.gf}:${s.ga}`],['PPG',s.ppg,'punkty na mecz'],['1. gol Bosch',`${st.first_goal_share??0}%`,`${st.first_for??0}/${st.matches??s.matches} meczów`],['Mecze stykowe',cl.close_ppg??'-',`${cl.close_matches??0} meczów`],['Ciągłość',ct.continuity!=null?`${ct.continuity}%`:'-',`${ct.roster??'-'} zawodników`],['Top3 goli',`${cn.top3_goal_share??0}%`,`${cn.scorers??0} strzelców`],['Wideo',`${vd.coverage_pct??0}%`,`${vd.matches_with_video??0}/${vd.matches_total??s.matches} meczów`]]} else {rows=[['Zakres',activeRangeLabel(),`${agg.seasonRows.length} sezonów w podsumowaniu zbiorczym`],['Bilans zbiorczy',`${agg.team.wins}-${agg.team.draws}-${agg.team.losses}`,`${agg.team.gf}:${agg.team.ga}`],['Punkty łącznie',agg.team.points,`${agg.team.matches} meczów`],['PPG zbiorcze',prettyNum(agg.team.ppg),`target: ${prettyNum(agg.benchmark.second_ppg??safeNum(REPORT.scorecard_rows[0][2],0))}`],['1. gol Bosch',`${prettyNum(agg.state.first_goal_share,1)}%`,`${agg.state.first_for}/${agg.team.matches} meczów`],['Mecze stykowe',prettyNum(agg.close.close_ppg),`${agg.close.close_matches} meczów`],['Ciągłość',agg.continuity.continuity!=null?`${prettyNum(agg.continuity.continuity,1)}%`:'-',`${agg.continuity.roster} wpisów kadrowych`],['Top3 goli',`${prettyNum(agg.concentration.top3_goal_share,1)}%`,`${agg.concentration.scorers} wpisów strzeleckich`],['Wideo',`${prettyNum(agg.video.coverage_pct,1)}%`,`${agg.video.matches_with_video}/${agg.video.matches_total} meczów`]]} el.innerHTML=rows.map(([k,v,sb])=>`<div class="card"><div class="label">${esc(k)}</div><div class="value">${esc(v)}</div><div class="sub">${esc(sb)}</div></div>`).join('')}
    function seasonCards(){const el=document.getElementById('season-cards');const activeIds=selectedSeasonIds();el.innerHTML=REPORT.season_rows.filter(passQuery).map(r=>{const st=stateMap.get(String(r.sid))||{},vd=videoMap.get(String(r.sid))||{};return `<article class="season-card ${activeIds.has(String(r.sid))?'active':''}" data-season="${r.sid}"><div class="label">${esc(r.table_title)}</div><div class="value">${esc(r.season)}</div><div class="sub">Pozycja ${r.pos} | ${r.points} pkt | ${r.gf}:${r.ga}</div><div class="tags"><span class="tag blue">PPG ${r.ppg}</span><span class="tag teal">1. gol ${st.first_goal_share??0}%</span><span class="tag orange">Wideo ${vd.coverage_pct??0}%</span></div></article>`}).join('')||'<div class="empty">Brak sezonów dla aktywnego wyszukiwania.</div>';el.querySelectorAll('.season-card').forEach(card=>card.addEventListener('click',()=>{toggleSetValue(state.seasons,String(card.dataset.season));sync();refresh();window.scrollTo({top:0,behavior:'smooth'})}))}
    function bars(id,rows,labelKey,valKey,color,suffix=''){const el=document.getElementById(id), data=rows.filter(passSeason).filter(passQuery); if(!data.length){el.innerHTML='<div class="empty">Brak danych.</div>';return} const mobile=mobileCharts(),w=560,h=mobile?280:240,left=18,right=18,bottom=mobile?102:70,top=14,gap=mobile?10:12,bw=(w-left-right-gap*(data.length-1))/data.length,max=Math.max(...data.map(r=>safeNum(r[valKey],0)),1); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${data.map((r,i)=>{const v=safeNum(r[valKey],0),bh=(v/max)*(h-top-bottom),x=left+i*(bw+gap),y=h-bottom-bh; return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${color}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="11" fill="#425466">${v}${suffix}</text>${svgLabel(x+bw/2,h-(mobile?46:44),r[labelKey],{maxChars:mobile?10:14,lineHeight:mobile?11:12,fontSize:mobile?10:11})}`}).join('')}</svg>`}
    function currentPlayers(){const el=document.getElementById('current-player-cards'); el.innerHTML=REPORT.current_players.filter(passQuery).slice(0,6).map(r=>`<article class="player-card"><div class="label">Bieżący sezon</div><div class="value">${esc(r.name)}</div><div class="tags"><span class="tag blue">${r.apps} meczów</span><span class="tag teal">${r.points} G+A</span><span class="tag orange">${r.motm} MVP</span></div><div class="sub">Gole ${r.goals} | Asysty ${r.assists} | ŻK ${r.yellow} | CZK ${r.red}</div></article>`).join('')}
    function resultBadge(r){const cls=r.gf>r.ga?'win':r.gf<r.ga?'loss':'draw';const text=r.gf>r.ga?'wygrana':r.gf<r.ga?'porażka':'remis';return `<span class="status ${cls}">${text}</span>`}
    function distribution(id,payload,color){const el=document.getElementById(id);if(!el)return;if(!payload||!payload.labels||!payload.labels.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),data=payload.labels.map((label,index)=>({label,value:payload.values[index]}));const w=560,h=mobile?286:250,left=18,right=18,bottom=mobile?108:74,top=16,gap=16,bw=(w-left-right-gap*(data.length-1))/data.length,max=Math.max(...data.map(r=>safeNum(r.value,0)),1),totals=payload.totals||{};el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${data.map((r,i)=>{const v=safeNum(r.value,0),bh=(v/max)*(h-top-bottom),x=left+i*(bw+gap),y=h-bottom-bh;return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${color}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="11" fill="#425466">${v}</text>${svgLabel(x+bw/2,h-(mobile?54:44),r.label,{maxChars:mobile?10:14,lineHeight:mobile?11:12,fontSize:mobile?10:11})}`}).join('')}<text x="${left}" y="${h-14}" font-size="10" fill="#5b6b7d">Gole: ${totals.goals??0} · Strzelcy: ${totals.unique_scorers??0} · Dublety: ${totals.braces??0} · Hat-tricki: ${totals.hat_tricks??0}</text></svg>`}
    function comparisonChart(){const el=document.getElementById('peak-chart');if(!el)return;const rows=peakComparisonRowsActive().filter(r=>num(r[1])!==null&&num(r[2])!==null).slice(0,6);if(!rows.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),w=560,h=mobile?326:270,left=24,right=18,bottom=mobile?132:82,top=16,gap=mobile?18:24,bw=28,group=(w-left-right-gap*(rows.length-1))/rows.length,max=Math.max(...rows.flatMap(r=>[safeNum(r[1],0),safeNum(r[2],0)]),1);el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${rows.map((r,i)=>{const cur=safeNum(r[1],0),peak=safeNum(r[2],0),base=left+i*(group+gap),h1=(cur/max)*(h-top-bottom),h2=(peak/max)*(h-top-bottom);return `<rect x="${base}" y="${h-bottom-h1}" width="${bw}" height="${h1}" rx="8" fill="#ea580c"></rect><rect x="${base+bw+6}" y="${h-bottom-h2}" width="${bw}" height="${h2}" rx="8" fill="#1d4ed8"></rect><text x="${base+bw/2}" y="${h-bottom-h1-6}" text-anchor="middle" font-size="10" fill="#425466">${cur}</text><text x="${base+bw+6+bw/2}" y="${h-bottom-h2-6}" text-anchor="middle" font-size="10" fill="#425466">${peak}</text>${svgLabel(base+bw,h-(mobile?72:46),r[0],{maxChars:mobile?12:16,lineHeight:mobile?11:12,fontSize:mobile?10:10})}`}).join('')}<text x="${left}" y="${h-16}" font-size="10" fill="#5b6b7d">pomarańczowy: aktywny zakres · niebieski: peak</text></svg>`}
    function surfaceChart(){const el=document.getElementById('surface-chart');if(!el)return;const rows=surfaceRowsActive();if(!rows.length){el.innerHTML='<div class="empty">Brak danych.</div>';return}const mobile=mobileCharts(),w=560,h=mobile?286:250,left=24,right=18,bottom=mobile?98:70,top=16,gap=48,bw=26,max=Math.max(...rows.flatMap(r=>[safeNum(r.ppg,0),safeNum(r.gfpg,0),safeNum(r.gapg,0)]),1);el.innerHTML=`<svg viewBox="0 0 ${w} ${h}"><line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="#d5dee8"></line>${rows.map((r,i)=>{const base=left+i*(bw*3+gap),vals=[[safeNum(r.ppg,0),'#1d4ed8','PPG'],[safeNum(r.gfpg,0),'#0f766e','GF/m'],[safeNum(r.gapg,0),'#ea580c','GA/m']];return vals.map((v,j)=>{const bh=(v[0]/max)*(h-top-bottom),x=base+j*(bw+8),y=h-bottom-bh;return `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="8" fill="${v[1]}"></rect><text x="${x+bw/2}" y="${y-6}" text-anchor="middle" font-size="10" fill="#425466">${v[0]}</text>${svgLabel(x+bw/2,h-(mobile?56:42),v[2],{maxChars:mobile?8:10,lineHeight:mobile?11:10,fontSize:mobile?9:9})}`}).join('')+`${svgLabel(base+bw+16,h-(mobile?20:18),r.label,{maxChars:mobile?10:12,lineHeight:11,fontSize:10,fill:'#425466'})}`}).join('')}</svg>`}
    function recommendationRows(){const currentBenchmark=benchmarkMap.get(String(REPORT.current_season_id));const currentState=stateMap.get(String(REPORT.current_season_id))||REPORT.current_state||{};const currentClose=closeMap.get(String(REPORT.current_season_id))||{};const currentConcentration=concMap.get(String(REPORT.current_season_id))||{};const currentTier=REPORT.tier_split_current||[];const topHalf=currentTier.find(r=>norm(r.label).includes('top'));const bottomHalf=currentTier.find(r=>norm(r.label).includes('bottom'));const currentPlayer=REPORT.current_players[0];const gapPpg=currentBenchmark?((currentBenchmark.second_points/Math.max(1,currentBenchmark.second_matches))-(currentBenchmark.bosch_points/Math.max(1,currentBenchmark.bosch_matches))).toFixed(2):null;return[{priority:'Priorytet 1',title:'Domknąć prowadzenia i końcówki',impact:'najszybszy wzrost punktów bez rewolucji kadrowej',detail:`Bosch oddał już ${currentState.points_dropped_from_leads??0} ${tip('wypuszczone pkt','Wypuszczone pkt')}, a w ${currentClose.close_matches??0} ${tip('meczach stykowych','Mecze stykowe')} robi ${currentClose.close_ppg??'-'} ${tip('PPG','PPG')}.`,target:'zmniejszyć liczbę oddanych punktów po prowadzeniu i podnieść PPG w meczach stykowych do poziomu zespołu z top2'},{priority:'Priorytet 2',title:'Podnieść jakość przeciw mocnym rywalom',impact:'bez tego Bosch zostanie solidnym środkiem II ligi',detail:topHalf&&bottomHalf?`W ${tip('splicie konkurencyjności','Split konkurencyjności')} Bosch punktuje wyraźnie lepiej z bottom half (${bottomHalf.ppg} PPG) niż z top half (${topHalf.ppg} PPG).`:'Największy zapas jakości nadal leży w meczach z górą tabeli.',target:'zbliżyć PPG z top half do poziomu pozwalającego regularnie bić się o podium'},{priority:'Priorytet 3',title:'Uszczelnić fazę bez piłki',impact:'awans zwykle buduje się obroną, nie samym wolumenem goli',detail:currentBenchmark?`Do progu awansu brakuje dziś około ${gapPpg} ${tip('PPG','PPG')} na mecz, a najprostsza droga do odzyskania tego dystansu prowadzi przez niższą liczbę bramek traconych.`:'W bieżącej próbce nadal łatwiej poprawić obronę niż wyciągnąć jeszcze wyższy sufit ofensywny.',target:'zejść z liczbą bramek traconych i częściej utrzymywać kontrolę po objęciu prowadzenia'},{priority:'Priorytet 4',title:'Zachować szerokość ataku, ale odciążyć lidera',impact:'lepsza odporność kadry na słabszy dzień jednego zawodnika',detail:currentPlayer?`${currentPlayer.name} jest dziś liderem produkcji, ale obecnie top3 odpowiada za ${currentConcentration.top3_goal_share??0}% goli Bosch.`:`Potrzebne jest utrzymanie wieloźródłowej ofensywy, bo peak Bosch nigdy nie opierał się na jednym nazwisku.`,target:'utrzymać szeroką produkcję i dołożyć stabilne drugie-trzecie źródło liczb'},{priority:'Priorytet 5',title:'Rozbudować świeżą bibliotekę wideo',impact:'bez tego trudniej o pracę korekcyjną i monitoring postępu',detail:`Publiczne pokrycie bieżącego sezonu wynosi ${videoMap.get(String(REPORT.current_season_id))?.coverage_pct??0}%.`,target:'budować własne archiwum bieżących meczów, żeby liczby od razu podpinać pod konkretne klipy'}]}
    function renderRecommendations(){const el=document.getElementById('recommendation-cards');if(!el)return;const rows=recommendationRows().filter(passQuery);el.innerHTML=rows.map(r=>`<article class="reco-card"><div class="label">${esc(r.priority)}</div><h3>${esc(r.title)}</h3><div class="tags"><span class="tag blue">${esc(r.impact)}</span></div><p>${r.detail}</p><p><strong>Cel:</strong> ${esc(r.target)}</p></article>`).join('')||'<div class="empty">Brak rekomendacji dla aktywnego wyszukiwania.</div>'}
    function renderNotes(){const agg=activeAggregate(),peakPlayer=REPORT.overall_points[0],currentPlayer=REPORT.current_players[0],h2h=h2hRowsActive().filter(r=>r.matches>=2),bestH2H=[...h2h].sort((a,b)=>b.ppg-a.ppg)[0],worstH2H=[...h2h].sort((a,b)=>a.ppg-b.ppg)[0],note=lines=>`<strong>Wniosek Rozdziału</strong>${lines.map(line=>`<p>${line}</p>`).join('')}`,set=(id,html)=>{const el=document.getElementById(id);if(el)el.innerHTML=html};set('overview-note',note([`Aktywny zakres obejmuje ${agg.team.matches} meczów ligowych Bosch w układzie: ${activeRangeLabel()}.`,`W tym zakresie po własnym otwarciu Bosch robi ${prettyNum(agg.state.ppg_when_scoring_first)} ${tip('PPG','PPG')}, a po stracie pierwszej bramki ${prettyNum(agg.state.ppg_when_conceding_first)}.`]));set('seasons-note',note([`Zakres ${activeRangeLabel()} daje zbiorcze ${prettyNum(agg.team.ppg)} ${tip('PPG','PPG')}.`,agg.benchmark.second_ppg!=null?`Do progu awansu dla tych sezonów brakuje około ${prettyNum(agg.benchmark.gap_ppg)} ${tip('PPG','PPG')} na mecz.`:`Dla części zaznaczonych sezonów nie ma pełnego benchmarku 2. miejsca, więc próg awansu jest tylko częściowo porównywalny.`]));set('splits-note',note([`W wybranym zakresie można porówniać hale z orlikiem albo sklejać pełne lata, np. rok 2025 jako Hala 2024/2025 plus Orlik 2025.`,`To właśnie tutaj najlepiej widać, czy Bosch jest mocniejszy na konkretnej powierzchni i jak bardzo zmienia profil gry między przekrojami.`]));set('control-note',note([`W aktywnym zakresie Bosch oddał ${agg.state.points_dropped_from_leads} ${tip('wypuszczone pkt','Wypuszczone pkt')} po objęciu prowadzenia.`,`W ${agg.close.close_matches} ${tip('meczach stykowych','Mecze stykowe')} robi ${prettyNum(agg.close.close_ppg)} ${tip('PPG','PPG')}, więc końcówki nadal pozostają jednym z głównych obszarów poprawy.`]));set('players-note',note([currentPlayer&&peakPlayer?`${currentPlayer.name} pozostaje dziś najproduktywniejszy w bieżącej kadrze, a historycznie najwyższy pułap liczb daje ${peakPlayer.name}.`:`Sekcja zawodników pokazuje pełne tło indywidualne Bosch.`,`W warstwie zbiorczej aktywny zakres daje ${prettyNum(agg.concentration.top3_goal_share,1)}% udziału top3 strzelców, więc łatwo porównać, czy atak jest szeroki czy skupiony.`]));set('matches-note',note([`Tabela meczowa działa teraz także jako filtr zakresów: możesz łączyć kilka sezonów i od razu zobaczyć wspólną próbkę spotkań.`,`To najlepsze miejsce do sprawdzania całych bloków typu same hale, same orliki albo pełny rok rozgrywkowy.`]));set('opponents-note',note([bestH2H?`W aktywnym zakresie najlepiej punktowany regularny rywal to ${bestH2H.opponent} (${prettyNum(bestH2H.ppg)} ${tip('PPG','PPG')}).`:'W aktywnym zakresie próba H2H jest zbyt mała, by pewnie wskazać najwygodniejszego rywala.',worstH2H?`Najtrudniej punktować przeciw ${worstH2H.opponent} (${prettyNum(worstH2H.ppg)} ${tip('PPG','PPG')}).`:'W aktywnym zakresie próba H2H jest zbyt mała, by pewnie wskazać najtrudniejszego rywala.']));set('video-note',note([`Dla zakresu ${activeRangeLabel()} pokrycie wideo wynosi ${prettyNum(agg.video.coverage_pct,1)}% i obejmuje ${agg.video.matches_with_video} z ${agg.video.matches_total} meczów.`,`To pozwala porównywać nie tylko jeden sezon, ale też całe pakiety typu same hale albo pełny rok.`]));set('recommendations-note',note([`Rekomendacje na dole nadal są planem działania pod awans, ale filtry pozwalają teraz sprawdzić, które problemy wracają w różnych blokach sezonów.`,`Dzięki temu można oddzielić problem strukturalny od jednorazowego gorszego sezonu.`]))}
    function statusHtml(status){return norm(status).includes('obecny')?'<span class="status obecny">obecny</span>':'<span class="status arch">archiwalny</span>'}
    function register(){
      table('legend-table',[{key:'short',label:'Skrót',render:r=>tip(r.short,r.short)},{key:'meaning',label:'Znaczenie'}],()=>LEGEND.map(([short,meaning])=>({short,meaning})),{season:false,defaultSort:'short',defaultDir:'asc'});
      table('concept-table',[{key:'term',label:'Pojęcie',render:r=>tip(r.term,r.term)},{key:'definition',label:'Co to znaczy'},{key:'why',label:'Jak to czytać'}],()=>CONCEPTS.map(([term,definition,why])=>({term,definition,why})),{season:false,video:false,defaultSort:'term',defaultDir:'asc'});
      table('hidden-table',[{key:'player_id',label:'ID'},{key:'name',label:'Zawodnik',render:r=>`<div class="identity-badges"><span>${esc(r.name)}</span><span class="tag gold">profil niepubliczny</span></div>`},{key:'event_date',label:'Mecz źródłowy',render:r=>formatDate(r.event_date),sort:r=>r.event_date},{key:'event_title',label:'Spotkanie'},{key:'event_link',label:'Link',render:r=>`<a href="${r.event_link}" target="_blank" rel="noreferrer">wydarzenie</a>`}],()=>REPORT.resolved_hidden_players,{season:false,video:false,defaultSort:'event_date',defaultDir:'desc',scroller:true});
      table('season-table',[{key:'season',label:'Sezon'},{key:'pos',label:'Poz.'},{key:'points',label:'Pkt'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'gd',label:'RB'},{key:'ppg',label:'PPG'}],()=>REPORT.season_rows,{season:false,defaultSort:'sid',defaultDir:'asc'});
      table('scorecard-table',[{key:'metric',label:'KPI'},{key:'current',label:'Bosch teraz'},{key:'target',label:'Target'},{key:'status',label:'Status',render:r=>`<span class="tag ${r.status==='mocne'?'teal':r.status==='blisko'?'orange':'red'}">${esc(r.status)}</span>`},{key:'note',label:'Komentarz'}],()=>scorecardRowsActive(),{season:false,defaultSort:'current'});
      table('peak-table',[{key:'metric',label:'Metryka'},{key:'current',label:'Aktywny zakres'},{key:'peak',label:'Peak sezon'},{key:'gap',label:'Luka'}],()=>peakComparisonRowsActive().map(([metric,current,peak])=>({metric,current,peak,gap:num(current)!==null&&num(peak)!==null?(num(peak)-num(current)).toFixed(2):`${current} → ${peak}`})),{season:false,video:false,defaultSort:'metric',defaultDir:'asc'});
      table('state-table',[{key:'season',label:'Sezon'},{key:'matches',label:'M'},{key:'first_for',label:'1. gol Bosch'},{key:'first_against',label:'1. gol rywal'},{key:'first_goal_share',label:'1. gol %'},{key:'ppg_when_scoring_first',label:'PPG po 1:0'},{key:'ppg_when_conceding_first',label:'PPG po 0:1'},{key:'points_dropped_from_leads',label:'Wypuszczone pkt'}],()=>REPORT.state_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('close-table',[{key:'season',label:'Sezon'},{key:'close_matches',label:'Mecze stykowe',labelHtml:tip('Mecze stykowe','Mecze stykowe')},{key:'close_wins',label:'W'},{key:'close_draws',label:'R'},{key:'close_losses',label:'P'},{key:'close_ppg',label:'PPG'},{key:'scored_4plus',label:'4+ strzelone'},{key:'conceded_3plus',label:'3+ stracone'}],()=>REPORT.close_game_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('continuity-table',[{key:'season',label:'Sezon'},{key:'roster',label:'Kadra'},{key:'returning',label:'Powracający'},{key:'newcomers',label:'Nowi'},{key:'departures',label:'Ubytki'},{key:'continuity',label:'Ciągłość',labelHtml:tip('Ciągłość','Ciągłość'),render:r=>r.continuity==null?'-':`${r.continuity}%`}],()=>REPORT.continuity_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('concentration-table',[{key:'season',label:'Sezon'},{key:'scorers',label:'Strzelcy'},{key:'roster',label:'Kadra'},{key:'top1_goal_share',label:'Top1 goli',render:r=>`${r.top1_goal_share}%`},{key:'top3_goal_share',label:'Top3 goli',render:r=>`${r.top3_goal_share}%`},{key:'top5_point_share',label:'Top5 G+A',render:r=>`${r.top5_point_share}%`}],()=>REPORT.concentration_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('surface-table',[{key:'label',label:'Powierzchnia'},{key:'seasons',label:'Sezony'},{key:'matches',label:'M'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>surfaceRowsActive(),{season:false,video:false,defaultSort:'ppg'});
      table('slot-all-table',[{key:'label',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.slot_split_all,{season:false,video:false,defaultSort:'label',defaultDir:'asc'});
      table('slot-current-table',[{key:'label',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.slot_split_current,{season:false,video:false,defaultSort:'label',defaultDir:'asc'});
      table('halftime-all-table',[{key:'state',label:'Stan'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.halftime_all,{season:false,video:false,defaultSort:'ppg'});
      table('halftime-current-table',[{key:'state',label:'Stan'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.halftime_current,{season:false,video:false,defaultSort:'ppg'});
      table('tier-current-table',[{key:'label',label:'Grupa'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.tier_split_current,{season:false,video:false,defaultSort:'ppg'});
      table('tier-peak-table',[{key:'label',label:'Grupa'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'ppg',label:'PPG'},{key:'gfpg',label:'Gole/m'},{key:'gapg',label:'Stracone/m'}],()=>REPORT.tier_split_peak,{season:false,video:false,defaultSort:'ppg'});
      table('peak-compare-table',[{key:'metric',label:'Metryka'},{key:'current',label:'Zakres'},{key:'peak',label:'Peak'},{key:'reading',label:'Interpretacja'}],()=>peakComparisonRowsActive().map(([metric,current,peak])=>({metric,current,peak,reading:num(current)!==null&&num(peak)!==null?(num(peak)-num(current)>0?`Dołożenia: ${(num(peak)-num(current)).toFixed(2)}`:'poziom utrzymany'):'miara jakościowa'})),{season:false,video:false,defaultSort:'metric',defaultDir:'asc'});
      table('apps-table',[{key:'name',label:'Zawodnik'},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'motm',label:'MVP'}],()=>REPORT.overall_apps,{season:false,defaultSort:'apps'});
      table('points-table',[{key:'name',label:'Zawodnik'},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'motm',label:'MVP'}],()=>REPORT.overall_points,{season:false,defaultSort:'points'});
      table('player-cards-table',[{key:'name',label:'Zawodnik'},{key:'status',label:'Status',render:r=>statusHtml(r.status)},{key:'apps',label:'M'},{key:'goals',label:'G'},{key:'assists',label:'A'},{key:'points',label:'G+A'},{key:'points_per_match',label:'G+A/M'},{key:'peak',label:'Peak'}],()=>REPORT.player_cards,{season:false,defaultSort:'points',filter:r=>state.status==='all'||norm(r.status).includes(norm(state.status))});
      table('partnership-table',[{key:'pair',label:'Duet'},{key:'matches',label:'M'},{key:'points',label:'Pkt'},{key:'ppg',label:'PPG'}],()=>REPORT.partnership_rows,{season:false,video:false,defaultSort:'ppg',scroller:true});
      table('h2h-table',[{key:'opponent',label:'Rywal'},{key:'matches',label:'M'},{key:'wins',label:'W'},{key:'draws',label:'R'},{key:'losses',label:'P'},{key:'goals',label:'Gole',render:r=>`${r.gf}:${r.ga}`},{key:'gd',label:'RB'},{key:'ppg',label:'PPG',render:r=>prettyNum(r.ppg,2)},{key:'seasons_label',label:'Sezony'}],()=>h2hRowsActive(),{season:false,defaultSort:'matches'});
      table('best-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon'},{key:'match',label:'Mecz'},{key:'score',label:'Wynik'},{key:'margin',label:'RB'}],()=>resultsRowsActive('best'),{season:false,defaultSort:'margin'});
      table('worst-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon'},{key:'match',label:'Mecz'},{key:'score',label:'Wynik'},{key:'margin',label:'RB'}],()=>resultsRowsActive('worst'),{season:false,defaultSort:'margin',defaultDir:'asc'});
      table('benchmark-table',[{key:'season_name',label:'Sezon'},{key:'bosch_ppg',label:'Bosch PPG',render:r=>(r.bosch_points/Math.max(1,r.bosch_matches)).toFixed(2),sort:r=>r.bosch_points/Math.max(1,r.bosch_matches)},{key:'second_ppg',label:'2. miejsce PPG',render:r=>(r.second_points/Math.max(1,r.second_matches)).toFixed(2),sort:r=>r.second_points/Math.max(1,r.second_matches)},{key:'gap',label:'Luka pkt',render:r=>r.second_points-r.bosch_points,sort:r=>r.second_points-r.bosch_points},{key:'second_name',label:'Drużyna progowa'}],()=>REPORT.benchmark,{defaultSort:'season_id',defaultDir:'asc'});
      table('video-season-table',[{key:'season',label:'Sezon'},{key:'matches_total',label:'Mecze'},{key:'matches_with_video',label:'Z materiałem'},{key:'coverage_pct',label:'Pokrycie %'},{key:'minutes',label:'Minuty'},{key:'full_matches',label:'Pełne 2 połowy'}],()=>VIDEO.season_rows,{defaultSort:'sid',defaultDir:'asc'});
      table('recommended-table',[{key:'reason',label:'Powód'},{key:'season',label:'Sezon'},{key:'date',label:'Data'},{key:'display_opponent',label:'Rywal'},{key:'score',label:'Wynik',render:r=>`${r.gf}:${r.ga}`},{key:'watch',label:'Linki',render:r=>r.links.map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)}</a>`).join('<br>')}],()=>VIDEO.recommended_rows.map(x=>({...x.match,reason:x.reason})),{defaultSort:'date'});
      table('matched-table',[{key:'date',label:'Data'},{key:'season',label:'Sezon'},{key:'display_opponent',label:'Rywal'},{key:'score',label:'Wynik',render:r=>`${r.gf}:${r.ga}`},{key:'coverage_type',label:'Pokrycie'},{key:'duration_minutes',label:'Minuty'},{key:'watch',label:'Linki',render:r=>r.links.map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)} | ${esc(l.channel_handle)}</a>`).join('<br>')}],()=>VIDEO.matched_rows,{defaultSort:'date'});
      table('match-log-table',[{key:'date',label:'Data',render:r=>formatDate(r.date),sort:r=>r.date},{key:'season',label:'Sezon'},{key:'match',label:'Mecz'},{key:'score',label:'Wynik',render:r=>`${r.gf}:${r.ga}`},{key:'result',label:'Rezultat',render:r=>resultBadge(r),sort:r=>r.gf-r.ga},{key:'halftime',label:'HT'},{key:'slot',label:'Slot',labelHtml:tip('Slot','Slot API')},{key:'coverage_type',label:'Wideo',render:r=>r.video_count?`<span class="tag ${norm(r.coverage_type).includes('pełne')||norm(r.coverage_type).includes('pelne')?'teal':'orange'}">${esc(r.coverage_type)}</span>`:'<span class="tag red">brak</span>'},{key:'video_count',label:'Segmenty'},{key:'event_link',label:'Linki',render:r=>{const event=`<a href="${r.event_link}" target="_blank" rel="noreferrer">mecz</a>`;const watch=r.links?.length?r.links.map(l=>`<a href="${l.url}" target="_blank" rel="noreferrer">${esc(l.segment)}</a>`).join('<br>'):'';return [event,watch].filter(Boolean).join('<br>')}}],()=>VIDEO.match_rows,{defaultSort:'date',defaultDir:'desc',scroller:true});
      table('channel-table',[{key:'channel_name',label:'Kanał'},{key:'channel_handle',label:'Handle'},{key:'videos',label:'Wideo'},{key:'matched',label:'Dopasowane'},{key:'unmatched',label:'Niedopasowane'},{key:'minutes',label:'Minuty'},{key:'first_date',label:'Pierwszy upload',render:r=>formatDate(r.first_date),sort:r=>r.first_date},{key:'last_date',label:'Ostatni upload',render:r=>formatDate(r.last_date),sort:r=>r.last_date}],()=>VIDEO.channel_summary_rows,{season:false,defaultSort:'matched',scroller:true});
      table('unmatched-table',[{key:'channel_name',label:'Kanał'},{key:'title',label:'Tytuł'},{key:'publish_date',label:'Data',render:r=>formatDate(r.publish_date),sort:r=>r.publish_date},{key:'duration_text',label:'Długość'},{key:'view_count',label:'Wyświetlenia'},{key:'url',label:'Link',render:r=>`<a href="${r.url}" target="_blank" rel="noreferrer">otwórz</a>`}],()=>VIDEO.unmatched_rows,{season:false,defaultSort:'publish_date',defaultDir:'desc',scroller:true});
    }
    function meta(){document.getElementById('season-meta').textContent=`Aktywny zakres: ${activeRangeLabel()}`}
    function refresh(){summary();seasonCards();currentPlayers();renderRecommendations();hero();bars('points-chart',REPORT.season_rows,'season','points','#1d4ed8');bars('ppg-chart',REPORT.season_rows,'season','ppg','#0f766e');bars('first-goal-chart',REPORT.state_rows,'season','first_goal_share','#0f766e','%');bars('video-chart',VIDEO.season_rows,'season','coverage_pct','#ea580c','%');distribution('timing-all-chart',REPORT.goal_timing_all,'#1d4ed8');distribution('timing-current-chart',REPORT.goal_timing_current,'#0f766e');comparisonChart();surfaceChart();renderNotes();meta();renderers.forEach(fn=>fn())}
    hero();bindControls();initTooltips();initToolbar();initResponsiveCharts();register();sync();refresh();
  </script>
</body>
</html>
"""


def build_site() -> Path:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    video = json.loads(VIDEO_PATH.read_text(encoding="utf-8"))
    html = TEMPLATE.replace("__REPORT_JSON__", json.dumps(report, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("__VIDEO_JSON__", json.dumps(video, ensure_ascii=False).replace("</", "<\\/"))
    OUT_PATH.write_text(html, encoding="utf-8")
    return OUT_PATH


if __name__ == "__main__":
    print(build_site())
