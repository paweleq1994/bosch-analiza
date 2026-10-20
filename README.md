# Bosch Service Tech-Car — Kompendium

Statyczne archiwum drużyny: oficjalne protokoły PLP, historia zawodników, analiza wyników i nagrania.

**[Portal](https://paweleq1994.github.io/bosch-analiza/)** · **[Excel](https://paweleq1994.github.io/bosch-analiza/downloads/bosch-kompendium.xlsx)** · **[Stan wszystkich 20 punktów](reports/implementation-status.md)**

## Zweryfikowany snapshot — 19.10.2026

| Zakres | Stan |
|---|---|
| Liga | 8 sezonów, 113 meczów i 113 protokołów |
| Bramki | 293 bramki drużyny, 0 nierozliczonych, 6 samobójów Boscha |
| Zawodnicy | 46 kanonicznych profili, 988 występów w protokołach |
| Cała kariera PLP | 35 publicznych bilansów HTML i 11 rekonstrukcji z protokołów PLP oraz potwierdzenia gry wyłącznie w Boschu |
| Portrety | 18 potwierdzonych, 28 brakujących |
| Wideo | 120 rekordów źródłowych, 116 widocznych; 53 mecze z nagraniem, 60 bez przypisanego filmu |
| Weryfikacja materiałów | 3 prawdopodobne nagrania turnieju PLP do identyfikacji, 4 odrzucone powiązania, 4 filmy turnieju poza PLP pomijane |
| Odnośniki czasowe | 10 obejrzanych akcji i 5 oznaczonych komentarzy gola z oficjalnych napisów; 149 goli w kolejce |
| Różnice źródeł | 34 porównania, wszystkie wyjaśnione protokołami lub zakresem rozgrywek; 0 sprzeczności sezonowych z protokołami |

Aktualne liczby po kolejnych synchronizacjach są w [panelu jakości](https://paweleq1994.github.io/bosch-analiza/#/quality) i raportach. Pierwotne 113 meczów to chroniona baza historyczna; archiwum może rosnąć.

## Funkcje

- Wyniki i sezony, rywale według oficjalnych ID i historycznych nazw.
- Składy, strzelcy, minuty, asysty, kartki, MVP oraz historia zawodnika mecz po meczu.
- Osobne statystyki Boscha i całej kariery PLP, źródła oraz oznaczenia kompletności.
- Porównywarka zawodników, wykresy sezonowe i rankingi oddzielające wyniki niepełne.
- Serie, forma, czyste konta, minuty goli oraz obie połowy z oficjalnych wyników HT.
- Sortowanie tabel; XLSX z 7 arkuszami i linkami źródłowymi. Eksport CSV usunięty.
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

**Bosch, cała kariera PLP i minimum z protokołów to różne zakresy.** Moskal ma w tym snapshotcie 109 występów Boscha, razem z potwierdzonymi Superpucharami, i 139 całej kariery PLP. Superpuchary są uzgadniane z publicznym HTML oraz jednoznacznym przypisaniem klubu w tym samym sezonie; występów innych drużyn nie dopisujemy do Boscha.

Nieznane wartości pozostają nieznane; zero wymaga dowodu. Zdjęcia drużynowe nie są portretami. Gabriel Kuźma i Piotr Kuźma są odrębnymi osobami. Zachowano alias Kakareki i scalone profile Rutkowskiego.

Audyt 26 sitemap i 4559 adresów nie odnalazł nowych profili. Wszystkie 11 brakujących ID zwróciło REST 401 i publiczny adres WordPress 404; nie ma ich również na oficjalnej liście all-time. To ograniczenie aktualnych źródeł, a nie dowód braku dawnych występów. [Datowane dowody](data/source_access_audit.json). Sam ten audyt nie odzyskał kolejnych portretów.

Internet Archive udostępnił dawne profile o zgodnych ID. Odzyskano 3 portrety oraz wpisy Superpucharu 2022 Gorbacewicza, Kossakowskiego i Sołowieja. Późniejszy przegląd wszystkich 2415 publicznych protokołów odnalazł brakujący występ i żółtą kartkę Gołąbeskiego w meczu 10050 oraz dodatkowy występ Sołowieja w barażu 7882. Oba wydarzenia nie mają w PLP oznaczenia sezonu: historia pokazuje je osobno, z datą i źródłem. Nie zwiększają archiwum 113 meczów ligowych. Dla 11 niedostępnych profili zapisano liczby z protokołów w `data/source-evidence/public-career-protocol-review-20261019.json`. Użytkownik potwierdził 19.10.2026, że cała jedenastka grała w PLP wyłącznie w Boschu (`data/source-evidence/bosch-only-career-scope-20261019.json`). Po uzgodnieniu wszystkich sześciu pól z historią drużyny portal i XLSX pokazują te kariery jako rekonstrukcje: 79 występów w 44 protokołach. Liczby pochodzą z PLP, zakres klubowy z potwierdzenia użytkownika. Aktualne profile nadal są niedostępne. Brak potwierdzenia zakresu, nowa data po jego udzieleniu lub niezgodne sumy zachowują status minimum. Nowe kopie Web Archive potwierdziły m.in. 6M Markowskiego, 5M Kossakowskiego i 32M Sołowieja; osobny baraż wyjaśnia 33. występ Sołowieja. [Wyciągi archiwalnych tabel](data/source-evidence/archived-career-tables-20261019.json). Nadal brakuje 28 portretów. Sprawdzone kopie pozostałych profili zawierają placeholdery; dodatkowy przegląd artykułów PLP nie dostarczył nowego portretu z potwierdzoną tożsamością.

Kanały są w `data/video_channels.json`: `@martawnuszynska9993`, `@piotrgoabeski3337` oraz oficjalna PLP `UCd0p73Dp5Eya7c4tQ8EoLZA`. Ostatni kanał jest odczytywany z zakładki transmisji i filtrowany do tytułów Boscha. Siedem odnalezionych transmisji z lat 2023–2025 przypisano po porównaniu dokładnej daty i drużyn z PLP; osobna transmisja Superpucharu nie zwiększa pokrycia 113 meczów ligowych. Workflow odczytuje metadane przez istniejący `yt-dlp`; synchronizacja nie pobiera plików filmów. Ręczne `manual_bindings` w `data/video_updates.json` mają pierwszeństwo. `match_id: null` odrzuca stare powiązanie również w meczu, z zachowaniem `review_reason` i `reviewed_at`.

Użytkownik potwierdził, że dwa filmy z Olimpem oraz nagrania z Kolegami z Boiska i Medgalem pokazują turniej poza PLP. Są pomijane w widoku, kolejce identyfikacji i automatycznym dopasowywaniu, a surowe rekordy pozostają w źródłach. Rambo, Krokus i Prestige zachowano jako prawdopodobny turniej PLP / Superpuchar, z jawną niepewnością i bez przypisania do ligi. Wypowiedź nie ustala konkretnej edycji, daty meczu ani protokołu. Dowód klasyfikacji: `data/source-evidence/user-video-classification-20261019.json`.

Odnośnik czasowy wymaga wpisu w `data/video_goal_evidence.json`: meczu, zawodnika, minuty PLP, filmu, zweryfikowanej sekundy, metody, recenzenta i daty. Opis przeglądu wyjaśnia powiązanie; klatki są w `reports/evidence/`. Dziesięć odnośników wskazuje obejrzaną akcję, a pięć jest wyraźnie oznaczonych jako komentarz gola z automatycznych napisów oficjalnej transmisji. Komentarz nie potwierdza czytelnego obrazu piłki w bramce. Minuta 21 meczu nie oznacza 21:00 filmu. Dalsze 149 goli w meczach z nagraniem wymaga przeglądu. Cztery inne gole utraciły błędnie przypisany film i wróciły do braków nagrań; nie oznacza to ich weryfikacji. Filmy „1” i „2” przypisano do Wiary Piasta II z 01.07.2023 po jednoznacznym potwierdzeniu użytkownika; nie ustala to jeszcze sekundy gola.

Przegląd dat i obejrzanych boisk poprawił stare powiązania: dwie połowy OSMAR z 23.11.2024 należą do hali 10990, pierwsza połowa CEDC Polmos z 10.09.2023 do 8373 (HT 2:0), a CF Bojary z 26.08.2023 nie może pokazywać hali z lutego 2024. Dowody są w `data/source-evidence/video-fixture-review-20261019.json`. Generator i walidator odrzucają film opublikowany przed meczem, z jednodniową tolerancją stref czasowych.

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

Szczegóły bieżącej rekonstrukcji: [11 karier, Web Archive i pełny zakres crawlu](reports/career-reconstruction-20261019.md). Crawl odczytał 7456 różnych adresów HTML, w tym wszystkie 4559 adresów wymienionych w mapach witryny.
