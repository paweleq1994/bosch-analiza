# Bosch Service Tech-Car — Kompendium

Statyczne archiwum drużyny: oficjalne protokoły PLP, historia zawodników, analiza wyników i nagrania.

**[Portal](https://paweleq1994.github.io/bosch-analiza/)** · **[Excel](https://paweleq1994.github.io/bosch-analiza/downloads/bosch-kompendium.xlsx)** · **[Stan wszystkich 20 punktów](reports/implementation-status.md)**

## Zweryfikowany snapshot — 19.10.2026

| Zakres | Stan |
|---|---|
| Liga | 8 sezonów, 113 meczów i 113 protokołów |
| Bramki | 293 bramki drużyny, 0 nierozliczonych, 6 samobójów Boscha |
| Zawodnicy | 45 kanonicznych profili, 988 występów w protokołach |
| Cała kariera PLP | 34 publiczne bilanse, 11 niepełnych archiwów |
| Portrety | 18 potwierdzonych, 27 brakujących |
| Wideo | 120 rekordów; 54 mecze z nagraniem, 59 bez przypisanego filmu |
| Weryfikacja materiałów | 9 do identyfikacji, 3 odrzucone powiązania / materiały poza archiwum ligowym |
| Odnośniki czasowe | 5 obejrzanych akcji; 162 gole w kolejce po odnalezieniu dalszych transmisji |
| Różnice źródeł | 33 porównania: 29 wyjaśnionych, 4 wymagające dalszej weryfikacji; 0 sprzeczności sezonowych z protokołami |

Aktualne liczby po kolejnych synchronizacjach są w [panelu jakości](https://paweleq1994.github.io/bosch-analiza/#/quality) i raportach. Pierwotne 113 meczów to chroniona baza historyczna; archiwum może rosnąć.

## Funkcje

- Wyniki i sezony, rywale według oficjalnych ID i historycznych nazw.
- Składy, strzelcy, minuty, asysty, kartki, MVP oraz historia zawodnika mecz po meczu.
- Osobne statystyki Boscha i całej kariery PLP, źródła oraz oznaczenia kompletności.
- Porównywarka zawodników, wykresy sezonowe i rankingi oddzielające wyniki niepełne.
- Serie, forma, czyste konta, minuty goli oraz obie połowy z oficjalnych wyników HT.
- Sortowanie i CSV tabel; XLSX z 7 arkuszami i linkami źródłowymi.
- YouTube, jawne powody odrzucenia powiązań i odnośniki do obejrzanych akcji.

[Dawna strona](docs/archive.html), [Orlik 2026](docs/orlik-2026.html) i [scouting](docs/scouting.html) pozostają dostępne.

## Generowanie i testy offline

Python 3.12, Node.js oraz istniejąca zależność eksportera:

```bash
python -m pip install "openpyxl==3.1.5"
python -m unittest discover -s tests -v
python src/build_portal.py
python src/validate_portal.py
python src/export_workbook.py
python src/audit_player_coverage.py
python src/audit_stat_sources.py
python src/audit_source_reconciliation.py
python src/audit_video_coverage.py
python src/video_goal_evidence.py
python -m compileall -q src
node --check docs/assets/app.js
node --check docs/assets/scouting.js
node --check docs/assets/table-sort.js
for test_file in tests/frontend_*.cjs; do node "$test_file" || exit 1; done
```

Ostatnią pętlę w PowerShell zastępuje:

```powershell
Get-ChildItem tests/frontend_*.cjs | ForEach-Object {
    node $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Nieudany test: $_" }
}
```

Generator używa wersjonowanych plików `data/` i działa bez dostępu do PLP lub YouTube. Testy nowych sezonów obejmują istniejący import, protokoły, historię, sumy, generator i walidator publikacji. Nie trzeba uruchamiać scraperów do testów offline.

## Automatyczna synchronizacja i publikacja

- [Bosch data sync](.github/workflows/sync.yml): **co godzinę, w 17. minucie UTC**, po wskazanych zmianach na `main` lub ręcznie. Odświeża PLP, protokoły, profile, media, metadane YouTube, scouting, portal, XLSX i raporty. Limit: 28 minut.
- [Publish verified Bosch downloads](.github/workflows/publish-downloads.yml): niezależna publikacja XLSX i raportów z zapisanego snapshotu, bez oczekiwania na scraping. Kolejka goli jest sprawdzana i dodawana do commita.
- [Validate Bosch portal](.github/workflows/validate.yml): testy Python/Node i generowanie offline dla PR-ów oraz `main`.
- [Audit public PLP sitemaps](.github/workflows/plp-sitemap.yml): poniedziałki 05:23 UTC oraz ręcznie; zapisuje udane odczyty i konkretne błędy źródeł.

Nowy sezon jest przyjmowany po uzgodnieniu meczów, bramek i punktów z oficjalną tabelą. Niepełny protokół trafia z przyczyną do `data/pending_goal_protocols.json`. Błąd źródła zachowuje poprzedni snapshot. Eksport XLSX normalizuje końce linii i pamięta kod eksportera: identyczne dane na Windows i Linux nie powodują zbędnych commitów binarnych. GitHub Pages publikuje `docs/`; portal nie ma backendu ani płatnego hostingu.

## Zasady i ograniczenia źródeł

**Bosch, cała kariera PLP i minimum z protokołów to różne zakresy.** Moskal ma w tym snapshotcie 105 występów Boscha i 139 całej kariery PLP. Różnicy obejmującej inne kluby i rozgrywki nie dopisujemy do Boscha.

Nieznane wartości pozostają nieznane; zero wymaga dowodu. Zdjęcia drużynowe nie są portretami. Gabriel Kuźma i Piotr Kuźma są odrębnymi osobami. Zachowano alias Kakareki i scalone profile Rutkowskiego.

Audyt 26 sitemap i 4559 adresów nie odnalazł nowych profili. Wszystkie 11 brakujących ID zwróciło REST 401 i publiczny adres WordPress 404; nie ma ich również na oficjalnej liście all-time. To ograniczenie aktualnych źródeł, a nie dowód braku dawnych występów. [Datowane dowody](data/source_access_audit.json). Sam ten audyt nie odzyskał kolejnych portretów.

Internet Archive udostępnił dawne profile o zgodnych ID. Odzyskano 3 portrety oraz wpisy Superpucharu 2022 Gorbacewicza, Kossakowskiego i Sołowieja, wyjaśniające 4 z 7 nieprzypisanych pól bez zwiększania sum zawodników. Pozostają 3 pola Gołąbeskiego bez potwierdzonego sezonu. Zdjęć nadal brakuje 27 osobom. Spośród 27 pozostałych profili 15 miało adres znaleziony po pełnym imieniu i nazwisku w CDX; sprawdzone kopie zawierają placeholdery w dwóch szablonach PLP. Pozostałe 12 nie miało takiego wyniku, co nie dowodzi braku kopii pod innym aliasem. Daty kopii, kolumny tabel, ID i źródła zapisano w audycie; historycznych kopii nie traktujemy jako pełnej kariery do dziś.

Kanały są w `data/video_channels.json`: `@martawnuszynska9993`, `@piotrgoabeski3337` oraz oficjalna PLP `UCd0p73Dp5Eya7c4tQ8EoLZA`. Ostatni kanał jest odczytywany z zakładki transmisji i filtrowany do tytułów Boscha. Siedem odnalezionych transmisji z lat 2023–2025 przypisano po porównaniu dokładnej daty i drużyn z PLP; osobna transmisja Superpucharu nie zwiększa pokrycia 113 meczów ligowych. Workflow odczytuje metadane przez istniejący `yt-dlp`; synchronizacja nie pobiera plików filmów. Ręczne `manual_bindings` w `data/video_updates.json` mają pierwszeństwo. `match_id: null` odrzuca stare powiązanie również w meczu, z zachowaniem `review_reason` i `reviewed_at`.

Odnośnik czasowy wymaga wpisu w `data/video_goal_evidence.json`: meczu, zawodnika, minuty PLP, filmu, obejrzanej sekundy, metody, recenzenta i daty. Opis przeglądu wyjaśnia powiązanie; klatki są w `reports/evidence/`. Minuta 21 meczu nie oznacza 21:00 filmu. Dalsze 154 gole wymagają przeglądu i nie są oznaczone jako ukończone.

## Raporty i kod

- [Stan prac i wszystkie 20 punktów](reports/implementation-status.md)
- [Kompletność zawodników](reports/player-data-coverage.md)
- [Protokoły i statystyki](reports/player-source-reconciliation.md)
- [HTML / REST / scalone tożsamości](reports/source-reconciliation.md)
- [Sitemapy](reports/plp-source-crawl.md)
- [Pokrycie filmami](reports/video-coverage.md)
- [Obejrzane akcje i kolejka goli](reports/video-goal-review-queue.md)
- `src/build_portal.py`, `src/validate_portal.py` — generator i kontrola spójności.
- `src/sync_plp.py`, `src/collect_match_player_evidence.py`, `src/sync_new_goal_protocols.py` — sezony i protokoły.
- `src/sync_player_seasons.py`, `src/sync_public_player_careers.py` — osobne dane sezonowe i HTML całej kariery.
- `src/export_workbook.py` — XLSX z tego samego snapshotu co portal.
- `docs/assets/data.json`, `docs/assets/app.js`, `docs/assets/style.css` — dane i interfejs.
