# Stan wdrożenia kompendium Bosch — 19.10.2026

Ostatni sprawdzony main: `d2b28ef9800d64f6b04c44198e719b348aa4f7dd` (merge PR #55).
Repozytorium lokalne zaktualizowano przez fast-forward z `94402f0`; przed pracą było czyste.
Gałąź kontynuacji: `codex/fix-publication-and-complete-audit`.
Issue #33 jest otwarte i ma nieaktualne checkboxy; publiczne API potwierdziło brak otwartych PR-ów.

## Audyt przed implementacją

| Punkt | Stan na sprawdzonym main | Dowód | Pozostały zakres |
|---|---|---|---|
| 1 | Wdrożone i przetestowane | PR #55, `test_future_season_pipeline.py`: 9/10 sezonów, 114/115 meczów, test liderów Node | Bieżący oficjalny endpoint nie ogłasza nowszego sezonu |
| 2 | Wdrożony importer | `sync_new_goal_protocols.py`, `test_new_goal_protocols.py` | Sprawdzić razem z nowym sezonem, zachować pending zamiast zer |
| 3 | Wdrożone + regresja przyszłych ID | `test_future_season_pipeline.py` | Nieznany ID 99999 trafia do audytu, protokół pending; brak fikcyjnego profilu |
| 4 | Rozliczone 29/33 porównań źródeł | `source-reconciliation.md`: 26 zakresów Superpucharu, 2 scalone ID, 1 występ potwierdzony protokołem | 4 różnice agregatów (5 pól sezonowych) bez dowodu przyczyny; 7 nieprzypisanych pól u 4 osób pozostaje bez publicznej tabeli |
| 5 | Ograniczenie źródłowe: 34 pełne, 11 niepełnych | `source_access_audit.json`: wszystkie 11 ID REST 401, publiczny post 404; brak w 1187 URL zawodników i all-time 1837 | Bez potwierdzonego archiwum dawnych klubów nie można uznać minimum za całą karierę |
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
| 19 | Wdrożone dla przyszłego sezonu | PR #55; lider Orlik 2027; chronologia Hala 2027/2028 | Brak wykazanego defektu |
| 20 | Publikacja naprawiona i wdrożona | PR #54; run 39257253261 = success | Dokumentacja i końcowy audyt |

## Ponownie przeliczone metryki

- 45 zawodników, 8 sezonów, 113 meczów i 113 zweryfikowanych protokołów.
- 293 bramki drużyny, 0 nierozliczonych; 6 samobójów Boscha.
- 988 występów w protokołach; 0 nierozpoznanych ID w bieżącym backfillu.
- 34 pełniejsze publiczne kariery PLP, 11 niepełnych; 33 różnice HTML/API/widok i 0 sezonowych sprzeczności.
- 29 porównań źródeł wyjaśnionych (26 Superpuchary, 2 profile Rutkowskiego, 1 Grabowski/protokół 9486); 4 wymagają dalszej weryfikacji źródła.
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
- PLP homepage i zespół REST 6951 dostępne; ostatni mecz 17.10 (Juan Pablo 4:3) jest już w snapshotcie. Lista 12 sezonów drużyny obejmuje 8 ligowych i 4 Superpuchary; brak nowszego sezonu na tym endpointcie.
- Powtórny audyt istniejącym crawlerem: 26 sitemap, 4559 URL, 0 nowych profili, 11 nadal niepotwierdzonych. Sitemapy WordPress dostępne HTTP 200; alternatywne `sitemap_index.xml` i `player-sitemap.xml` zwracają 404.
- Użytkownik zalogował zwykłą sesję GitHub; tworzenie i scalanie PR przez UI jest dostępne.
- Każde z 11 brakujących ID: REST **401**, publiczny adres WordPress z ID **404**. Żadnego z tych ID nie ma w oficjalnej liście all-time 1837. Wyniki z datą i URL zapisane w `data/source_access_audit.json`.
- 4 pozostałe różnice agregatów: Kuźma Piotr 4577 — występy Orlik 2024 7/6 i Hala 2024/2025 11/10 (CEDC Polmos, nie Bosch); Daniluk 2204 — Lato 2021 2/1; Kakareko 1594 — Lato 2021 mecze 4/3 i gole 1/0. Zachowano HTML jako całą karierę, bez dodawania różnic do Boscha.
- 7 nieprzypisanych pól historycznych (Gorbacewicz, Gołąbeski, Kossakowski, Sołowiej) nie ma nowych publicznych dowodów sezonu; nie dopasowywać ich przez odejmowanie minimów od agregatu.
- Automatyczna kontrola odrzuciła odczyt tokenu z menedżera Git do osobnych żądań API; nie ponawiać tego mechanizmu.

## Następne działanie

Poprawka P0 gotowa: osobna kontrola każdego raportu, zapis kolejki timestampów w commicie i brakujące triggery publikacji. Dwie nowe regresje wykonują Bash oraz rzeczywiste `git add` w tymczasowym repozytorium. **157 testów Python, 14 testów frontendowych, wszystkie generatory i audyty offline, walidacje portalu/scoutingu, compileall i składnia JS OK**. Archiwum bez zmian. Pełny przebieg poza sandboxem zakończony poprawnie.

PR #55 wdrożony. Rozszerzony istniejący audyt rozlicza teraz 33 różnice według sezonu, źródła, zakresu i potwierdzonych aliasów; nie modyfikuje statystyk zawodników. Po wdrożeniu tego audytu naprawić potwierdzone błędne przypisanie filmu Vesta `hcfb9Ttmswo` do hali (oficjalne wydarzenie 7814, hala VI LO; oglądana klatka pokazuje boisko odkryte), sprawdzić odrzucanie ręcznych przypisań, dokończyć HT i README.

## Nowe PR-y i wdrożenia

- **PR #54 — scalony**, commit `07bfa56`, merge `06d525a`.
- CI PR: run 39256972857 success; CI main 39257253186 success.
- Naprawiona publikacja XLSX/raportów: **39257253261 success**.
- GitHub Pages: **39257252401 success**.
- **PR #55 — scalony**, commit `aaded26`, merge `d2b28ef`.
- CI PR 39257687591 success; CI main 39258031399 success; publikacja 39258031372 success; Pages 39258030661 success.
- Synchronizacja po #55: run 39258031384 trwa; wynik wymaga końcowego sprawdzenia.

## Weryfikacja po pełnej synchronizacji PLP

Synchronizacja #55 opublikowała commit `ea3c315`, wypełniając historyczne agregaty meczowe. Pełne testy ujawniły zastępowanie bogatszych starych bilansów tymi agregatami (m.in. Gołąbeski 13→11 występów i utrata aliasu Kakareki). Poprawiono przyczynę: historyczne, nierosnące sezony nadal przechodzą istniejącą ścieżkę archiwum/profili/protokołów; dla graczy bez pełnego archiwum dodawane są tylko nowe, niezależne dane, z zachowaniem statusu minimum. Nowe testy obejmują częściowy bilans oraz dodanie meczu do istniejącego sezonu. Konflikt wygenerowanych raportów rozwiązano przez ponowne przeliczenie z najnowszych źródeł. Przed merge #56 wymagane ponowne pełne CI.
