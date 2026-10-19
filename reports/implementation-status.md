# Stan wdrożenia kompendium Bosch — 19.10.2026

Ostatni sprawdzony main: `363dc44` (eksport po merge PR #57 `01b4e20`). PR #56 scalono jako `29694db`; `f864f05` był późniejszym commitem publikatora, nie mergem.
Repozytorium lokalne zaktualizowano przez fast-forward z `94402f0`; przed pracą było czyste.
Gałąź kontynuacji: `codex/publishing-idempotence-halves-and-status`.
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
| 10 | Wdrożone, dodatkowa poprawka w bieżącym PR | Rankingi sezonowe wykluczają minima nawet przy liczbach całkowitych; porównywarka pokazuje ≥ i nie liczy stopy z minimum | Testy lidera przyszłego sezonu i niepełnego Gorbacewicza OK |
| 11 | Wdrożone | `frontend_match_boxscores.cjs`, `test_full_match_protocols.py` | Zachować 113 historycznych protokołów |
| 12 | Wdrożone | `frontend_match_boxscores.cjs`: 988 występów | Brak wykazanego defektu |
| 13 | Wdrożone | PR #51, `frontend_source_provenance.cjs` | Sprawdzić rzeczywiste wyjątki zakresu |
| 14 | Częściowo, skorygowane błędne powiązanie | `video-coverage.md`: 112 rekordów, 47/113 meczów; Vesta i materiał muzyczny mają uzasadnienie odrzucenia | 9 materiałów oczekuje identyfikacji, 66 meczów bez przypisanego nagrania; samo podobieństwo tytułu nie wystarcza |
| 15 | 2 obejrzane akcje z potwierdzonym czasem odtwarzacza | `video_goal_evidence.json`, klatki w `reports/evidence/`; mecz 7851, gole Jurkowicza 3′ i 23′ | 154 pozostałe gole wymagają dalszego oglądania i powiązania; bez zgadywania z minut PLP |
| 16 | Wdrożone | PR #38, `frontend_player_trends.cjs` | Brak wykazanego defektu |
| 17 | Wdrożone | PR #29, `frontend_match_boxscores.cjs` | Sprawdzić semantykę kompletności w nowych sezonach |
| 18 | Gotowe w bieżącym PR | 113 potwierdzonych HT: I połowa 130:94, II 163:135; stany do przerwy vs wynik końcowy | Brak lub sprzeczne HT wyłączane z obliczeń; test regresyjny |
| 19 | Wdrożone dla przyszłego sezonu | PR #55; lider Orlik 2027; chronologia Hala 2027/2028 | Brak wykazanego defektu |
| 20 | Dalsza przyczyna wyścigu XLSX naprawiona w bieżącym PR | Hash normalizuje CRLF/LF i uwzględnia kod eksportera; ponowny eksport nie zmienia pliku | Wymagany pełny zielony sync po merge; README zaktualizowane |

## Ponownie przeliczone metryki

- 45 zawodników, 8 sezonów, 113 meczów i 113 zweryfikowanych protokołów.
- 293 bramki drużyny, 0 nierozliczonych; 6 samobójów Boscha.
- 988 występów w protokołach; 0 nierozpoznanych ID w bieżącym backfillu.
- 34 pełniejsze publiczne kariery PLP, 11 niepełnych; 33 różnice HTML/API/widok i 0 sezonowych sprzeczności.
- 29 porównań źródeł wyjaśnionych (26 Superpuchary, 2 profile Rutkowskiego, 1 Grabowski/protokół 9486); 4 wymagają dalszej weryfikacji źródła.
- 15 potwierdzonych zdjęć, 30 braków.
- 112 rekordów wideo; **47** meczów z filmem, **66** bez; 9 materiałów do identyfikacji, 2 odrzucone powiązania / materiały spoza meczów (łącznie 11 bez meczu).
- **2** potwierdzone odnośniki do obejrzanej sekundy akcji bramkowej; **154** gole w kolejce. Kolejka zmalała o 2 obejrzane akcje i 2 gole, których jedyny film nie przedstawia właściwego spotkania.

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
- Synchronizacja po #55: run 39258031384 opublikował aktualne źródła jako `ea3c315`.
- **PR #56 — scalony**, zmiany `d688231` i `12d55c8`, merge `29694db`. Pełny najnowszy odczyt PLP został zachowany, a błędnie obniżone bilanse przywrócone. Przed merge: **166 testów Python i 14 frontendowych OK**. CI main 39260004028, publikacja 39260003518 i Pages 39260036786: success.
- **PR #57 — scalony**, commit `54323fc`, merge `01b4e20`. CI PR 39261382924, CI main 39261976656, publikacja 39261976694 i Pages 39262007112: success. Przed merge: **169 testów Python, 14 frontendowych OK**.
- Synchronizacje 39260003626 i 39261976651 ujawniły konflikt binarnego XLSX podczas rebase z równoległym eksportem. Przyczyną zbędnej regeneracji był różny hash tekstu CRLF na Windows i LF w Actions. Bieżąca poprawka normalizuje tekst i sprawdza również wersję kodu eksportera; nie przebudowuje architektury publikacji.

## Multimedia — dowody i pozostałe ograniczenia

- Film `hcfb9Ttmswo` pokazuje odkryte boisko, podczas gdy oficjalny mecz 7814 ma venue 109 (hala VI LO). Cofnięto to powiązanie; źródłowego archiwum nie usunięto.
- Wykryto i poprawiono błąd generatora: ręczne odrzucenie zmieniało indeks filmu, lecz pozostawiało oryginalny link w meczu. Regresja sprawdza obie reprezentacje i opis przeglądu. Dopasowanie pojedynczego kandydata uwzględnia teraz także sprzeczną datę publikacji.
- Materiał `8SF7bbYDS30` ma tytuł występu muzycznego; jest jawnie oznaczony jako spoza meczów Boscha, z zachowaniem źródła.
- Obejrzano klipy `izWNgjy1TN0` (0:1) i `MTwXQ9jcfTg` (1:2), porównując halę, datę publikacji, sekwencję wyniku i protokół 7851. Linki 7 s i 13 s zaczynają się w obejrzanej fazie kończącej akcję. Tożsamość strzelca wynika z kolejności goli i protokołu, bez rozpoznawania twarzy. Klatki dowodowe zachowane.
- Dalsze klipy nie otrzymały timestampu przy niejednoznacznym lub zasłoniętym obrazie. Sama automatyczna transkrypcja (np. `QXRjrPldpi0`) nie identyfikuje jednoznacznie strzelca ani sekundy gola. Pozostałe 154 pozycje wymagają dalszego przeglądu, nie są ukończone.
- Kontrolnie obejrzany `1nxZX2GWpIo` pokazuje prawidłowo halę VI LO; nie odrzucać innych materiałów tylko dlatego, że rekomendowany obok film pokazuje boisko.

## Weryfikacja po pełnej synchronizacji PLP

Synchronizacja #55 opublikowała commit `ea3c315`, wypełniając historyczne agregaty meczowe. Pełne testy ujawniły zastępowanie bogatszych starych bilansów tymi agregatami (m.in. Gołąbeski 13→11 występów i utrata aliasu Kakareki). PR #56 poprawił przyczynę: historyczne, nierosnące sezony nadal przechodzą istniejącą ścieżkę archiwum/profili/protokołów; dla graczy bez pełnego archiwum dodawane są tylko nowe, niezależne dane, z zachowaniem statusu minimum. Testy obejmują częściowy bilans oraz dodanie meczu do istniejącego sezonu. Konflikt raportów rozwiązano przez przeliczenie z najnowszych źródeł.

## Bieżący PR — eksport, połowy, minima i przyszły wzrost

- **175 testów Python, 14 frontendowych OK**, wszystkie 10 generatorów/audytów offline, walidacje, compileall, składnia 3 skryptów JS, diff check OK.
- Walidator dopuszcza wzrost historycznych bilansów i 16. mecz Orlika 2026, nadal odrzuca utratę bazowych rekordów oraz goli/występów Jurkowicza.
- XLSX: kolejne wywołanie `XLSX export unchanged`; regresje LF→CRLF oraz zmiana kodu eksportera. Poprawiony fałszywy status nieprzypisanych zer w arkuszu braków.
- Frontend: analiza połów i stanów HT/FT na 113 poprawnych źródłach, dynamiczne etykiety nowego sezonu, minima poza pełnymi rankingami G+A, porównywarka ≥/nieznane.
- Następny krok: merge po CI, pełny sync bez konfliktu, sprawdzenie publicznych pobrań i aktualizacja issue #33. Trwa przegląd oficjalnego kanału YouTube PLP `UCd0p73Dp5Eya7c4tQ8EoLZA` pod kątem materiałów spoza dwóch dotychczasowych kanałów.
