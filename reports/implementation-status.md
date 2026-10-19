# Stan wdrożenia kompendium Bosch — 19.10.2026

Ostatni sprawdzony main: `d54a9b35ed1dd04ed9ef79082c6cf953b59bb044`.
Repozytorium lokalne zaktualizowano przez fast-forward z `94402f0`; przed pracą było czyste.
Gałąź kontynuacji: `codex/fix-publication-and-complete-audit`.
Issue #33 jest otwarte i ma nieaktualne checkboxy; publiczne API potwierdziło brak otwartych PR-ów.

## Audyt przed implementacją

| Punkt | Stan na sprawdzonym main | Dowód | Pozostały zakres |
|---|---|---|---|
| 1 | Częściowo | `sync_plp.synchronize`, `test_sync_plp.py`, `test_archive_growth.py` | Test pełnego przejścia nowego sezonu; sprawdzić identyfikatory rozgrywek i kolejność sezonów |
| 2 | Wdrożony importer | `sync_new_goal_protocols.py`, `test_new_goal_protocols.py` | Sprawdzić razem z nowym sezonem, zachować pending zamiast zer |
| 3 | 13 ID odzyskanych | `match_player_identities.json`, `test_verified_match_identities.py` | Regresja wykrycia przyszłego nieznanego ID |
| 4 | Audyt działa; interpretacja częściowa | `source-reconciliation.md`: 33 różnice, 0 sprzeczności; `player-source-reconciliation.md` | Sprawdzić 7 nieprzypisanych pól u 4 zawodników; wyjaśnić różnice zakresów bez dopisywania statystyk |
| 5 | 34 pełne kariery, 11 niepełnych | `player-data-coverage.md`, `sync_public_player_careers.py` | Dodatkowe publiczne źródła; brak pełnej kariery zachować jako minimum |
| 6 | 15 zdjęć, 30 braków | `media_discovery.json`, `test_historic_team_photo_leads.py` | Sprawdzić dostępne metadane WordPress; zdjęcia klubowe pozostają kandydatami |
| 7 | Wdrożone | PR #30, Pages z `docs/` | Zweryfikować rzeczywiste wdrożenie po zmianach |
| 8 | Wdrożone | PR #37, `frontend_rivals_quality.cjs` | Brak wykazanego defektu |
| 9 | Wdrożone | ID 1594 i alias w `test_verified_match_identities.py` | Zachować odrębność Gabriela i Piotra Kuźmy |
| 10 | Wdrożone zasadniczo | `frontend_rivals_quality.cjs`, `frontend_records_sort.cjs` | Sprawdzić aktualnych liderów i brakujące wartości w porównywarce |
| 11 | Wdrożone | `frontend_match_boxscores.cjs`, `test_full_match_protocols.py` | Zachować 113 historycznych protokołów |
| 12 | Wdrożone | `frontend_match_boxscores.cjs`: 988 występów | Brak wykazanego defektu |
| 13 | Wdrożone | PR #51, `frontend_source_provenance.cjs` | Sprawdzić rzeczywiste wyjątki zakresu |
| 14 | Częściowo | `video-coverage.md`: 112 filmów, 48/113 meczów | Zweryfikować 10 nieprzypisanych materiałów; 65 meczów bez nagrania |
| 15 | Mechanizm wdrożony; brak zweryfikowanych sekund | PR #53, `video_goal_evidence.py`, `frontend_video_goal_timestamps.cjs` | 158 goli wymaga analizy materiału; nie wyznaczać sekund z minut PLP |
| 16 | Wdrożone | PR #38, `frontend_player_trends.cjs` | Brak wykazanego defektu |
| 17 | Wdrożone | PR #29, `frontend_match_boxscores.cjs` | Sprawdzić semantykę kompletności w nowych sezonach |
| 18 | Częściowo | PR #34, `frontend_historical_form.cjs` | Analiza połów wyłącznie z oficjalnego HT |
| 19 | Wdrożone zasadniczo | PR #30, `home()` i `frontend_all_tables_sort.cjs` | Regresja sezonu po 2026 |
| 20 | Defekt publikacji potwierdzony | `publish-downloads.yml`; run 39252079054 = failure | `test -s` z dwoma plikami; brak `git add` kolejki goli; dokumentacja i CI |

## Ponownie przeliczone metryki

- 45 zawodników, 8 sezonów, 113 meczów i 113 zweryfikowanych protokołów.
- 293 bramki drużyny, 0 nierozliczonych; 6 samobójów Boscha.
- 988 występów w protokołach; 0 nierozpoznanych ID w bieżącym backfillu.
- 34 pełniejsze publiczne kariery PLP, 11 niepełnych; 33 różnice HTML/API/widok i 0 sezonowych sprzeczności.
- 15 potwierdzonych zdjęć, 30 braków.
- 112 filmów; 48 meczów z filmem, 65 bez; 10 materiałów nieprzypisanych.
- 0 potwierdzonych znaczników goli; 158 goli w kolejce.

## Testy bazowe i odtworzenie błędu

- Python 3.12.14 z runtime Codex, openpyxl 3.1.5: **155 testów unittest OK**.
- Wszystkie **14 testów frontendowych Node OK**; składnia 3 skryptów JS OK.
- Generator offline i `validate_portal.py` OK; XLSX nie wymaga przebudowy.
- Audyty źródeł, różnic, filmów i timestampów przeliczone; metryki zgodne z powyższymi.
- Bash odtwarza `binary operator expected` dla `test -s reports/player-source-reconciliation.md reports/video-goal-review-queue.md`.
- Systemowy Python 3.14 nie ma openpyxl; nie jest używany do końcowej walidacji.
- Sandbox lokalnie blokuje zapis części istniejących raportów i pycache; pełne generowanie wymaga wykonania z uprawnieniami zatwierdzonymi przez narzędzie. To ograniczenie środowiska, nie defekt projektu.

## Źródła sprawdzone i blokery

- Publiczne API GitHub: issue #33 otwarte, 0 otwartych PR-ów; workflow 39252079054 zakończony błędem.
- PLP homepage dostępna przez narzędzie WWW; obecny oficjalny sezon Orlik 2026. Trzeba sprawdzić nowo opublikowane wyniki z 17.10 względem snapshotu.
- Stary audyt sitemap ma 5 błędów połączenia HTTP 0. Nie dowodzi nieistnienia profili.
- Przeglądarka Codex jest wylogowana z GitHub; poproszono użytkownika o zwykłe logowanie, bez przekazywania tokenu.
- Automatyczna kontrola odrzuciła odczyt tokenu z menedżera Git do osobnych żądań API; nie ponawiać tego mechanizmu.

## Następne działanie

Poprawka P0 gotowa: osobna kontrola każdego raportu, zapis kolejki timestampów w commicie i brakujące triggery publikacji. Dwie nowe regresje wykonują Bash oraz rzeczywiste `git add` w tymczasowym repozytorium. **157 testów Python, 14 testów frontendowych, wszystkie generatory i audyty offline, walidacje portalu/scoutingu, compileall i składnia JS OK**. Archiwum bez zmian. Pełny przebieg poza sandboxem zakończony poprawnie.

Po opublikowaniu gałęzi: otworzyć PR, sprawdzić CI i realny przebieg publikacji po merge. Równolegle dostępne lokalnie: test integracji nowego sezonu, rozliczenie pozostałych danych i ograniczone próby źródłowe. Nie powtarzać wdrożonych importerów ani mechanizmu timestampów.

## Nowe PR-y i wdrożenia

Poprawka P0 lokalnie gotowa i przetestowana; brak PR/merge/deploymentu do czasu dostępu do zalogowanej sesji GitHub.
