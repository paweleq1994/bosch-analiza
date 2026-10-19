# Stan wdrożenia kompendium Bosch — 19.10.2026

Ostatni sprawdzony main: `1ae4571` (merge PR #58). Pełny sync 39264014036 zakończony sukcesem, bez nowych zmian źródeł. PR #56 scalono jako `29694db`; `f864f05` był późniejszym commitem publikatora, nie mergem.
Repozytorium lokalne zaktualizowano przez fast-forward z `94402f0`; przed pracą było czyste.
Gałąź kontynuacji: `codex/official-video-archive-and-new-own-goals`.
Issue #33 jest otwarte i ma nieaktualne checkboxy; publiczne API potwierdziło brak otwartych PR-ów.

## Audyt przed implementacją

| Punkt | Stan na sprawdzonym main | Dowód | Pozostały zakres |
|---|---|---|---|
| 1 | Wdrożone i przetestowane | PR #55, `test_future_season_pipeline.py`: 9/10 sezonów, 114/115 meczów, test liderów Node | Bieżący oficjalny endpoint nie ogłasza nowszego sezonu |
| 2 | Wdrożony, uzupełniony brak samobójów w bieżącym PR | Nowy sezon z dwoma strzelcami samobójczymi, minutami i źródłami przechodzi do portalu bez zmiany historycznych 113 | Nieznane ID, brak minut lub sprzeczny bilans straconych → pending z przyczyną |
| 3 | Wdrożone + regresja przyszłych ID | `test_future_season_pipeline.py` | Nieznany ID 99999 trafia do audytu, protokół pending; brak fikcyjnego profilu |
| 4 | Rozliczone 29/33 porównań źródeł | `source-reconciliation.md`: 26 zakresów Superpucharu, 2 scalone ID, 1 występ potwierdzony protokołem | 4 różnice agregatów (5 pól sezonowych) bez dowodu przyczyny; 7 nieprzypisanych pól u 4 osób pozostaje bez publicznej tabeli |
| 5 | Ograniczenie źródłowe: 34 pełne, 11 niepełnych | `source_access_audit.json`: wszystkie 11 ID REST 401, publiczny post 404; brak w 1187 URL zawodników i all-time 1837 | Bez potwierdzonego archiwum dawnych klubów nie można uznać minimum za całą karierę |
| 6 | 15 zdjęć, 30 braków | `media_discovery.json`, `test_historic_team_photo_leads.py` | Sprawdzić dostępne metadane WordPress; zdjęcia klubowe pozostają kandydatami |
| 7 | Wdrożone | PR #30, Pages z `docs/` | Zweryfikować rzeczywiste wdrożenie po zmianach |
| 8 | Wdrożone | PR #37, `frontend_rivals_quality.cjs` | Brak wykazanego defektu |
| 9 | Wdrożone | ID 1594 i alias w `test_verified_match_identities.py` | Zachować odrębność Gabriela i Piotra Kuźmy |
| 10 | Wdrożone, PR #58 | Rankingi sezonowe wykluczają minima nawet przy liczbach całkowitych; porównywarka pokazuje ≥ i nie liczy stopy z minimum | Testy lidera przyszłego sezonu i niepełnego Gorbacewicza OK |
| 11 | Wdrożone | `frontend_match_boxscores.cjs`, `test_full_match_protocols.py` | Zachować 113 historycznych protokołów |
| 12 | Wdrożone | `frontend_match_boxscores.cjs`: 988 występów | Brak wykazanego defektu |
| 13 | Wdrożone | PR #51, `frontend_source_provenance.cjs` | Sprawdzić rzeczywiste wyjątki zakresu |
| 14 | Częściowo; 7 kolejnych meczów odzyskanych z oficjalnego kanału PLP | `video-coverage.md`: 120 rekordów, 54/113 meczów; 7 transmisji przypisanych po dokładnej dacie, parze drużyn i sezonie | 9 materiałów oczekuje identyfikacji, 59 meczów bez przypisanego nagrania; dodatkowy Superpuchar jawnie poza archiwum ligowym |
| 15 | 5 obejrzanych akcji z potwierdzonym czasem odtwarzacza | `video_goal_evidence.json`, klatki w `reports/evidence/`; 7851 (3′ i 23′) oraz 10145 (2′, 16′, 17′) | 162 pozostałe gole w dostępnych nagraniach wymagają dalszego oglądania i powiązania; kolejka wzrosła po odzyskaniu transmisji |
| 16 | Wdrożone | PR #38, `frontend_player_trends.cjs` | Brak wykazanego defektu |
| 17 | Wdrożone | PR #29, `frontend_match_boxscores.cjs` | Sprawdzić semantykę kompletności w nowych sezonach |
| 18 | Wdrożone, PR #58 | 113 potwierdzonych HT: I połowa 130:94, II 163:135; stany do przerwy vs wynik końcowy | Brak lub sprzeczne HT wyłączane z obliczeń; test regresyjny |
| 19 | Wdrożone dla przyszłego sezonu | PR #55; lider Orlik 2027; chronologia Hala 2027/2028 | Brak wykazanego defektu |
| 20 | Wdrożone, PR #54 i #58; pełny sync success | Hash normalizuje CRLF/LF i uwzględnia kod eksportera; sync 39264014036, publikacja 39264013991, Pages 39264013114 success | README zaktualizowane; końcowa kontrola po nowym imporcie filmów |

## Ponownie przeliczone metryki

- 45 zawodników, 8 sezonów, 113 meczów i 113 zweryfikowanych protokołów.
- 293 bramki drużyny, 0 nierozliczonych; 6 samobójów Boscha.
- 988 występów w protokołach; 0 nierozpoznanych ID w bieżącym backfillu.
- 34 pełniejsze publiczne kariery PLP, 11 niepełnych; 33 różnice HTML/API/widok i 0 sezonowych sprzeczności.
- 29 porównań źródeł wyjaśnionych (26 Superpuchary, 2 profile Rutkowskiego, 1 Grabowski/protokół 9486); 4 wymagają dalszej weryfikacji źródła.
- 15 potwierdzonych zdjęć, 30 braków.
- 120 rekordów wideo; **54** mecze z filmem, **59** bez; 9 materiałów do identyfikacji, 3 powiązania odrzucone / poza zakresem ligowym (łącznie 12 bez meczu ligowego).
- **5** potwierdzonych odnośników do obejrzanej sekundy akcji bramkowej; **162** gole w kolejce. Kolejka uwzględnia już siedem odzyskanych transmisji; wzrost kolejki nie oznacza utraty zweryfikowanych linków.

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

Scalić bieżący PR po CI, sprawdzić pełną synchronizację trzech kanałów, publiczne pobranie XLSX i wdrożony portal, a następnie zaktualizować issue #33. Dalsza weryfikacja goli wymaga oglądania konkretnych akcji; nie nazywać tej pracy ukończoną ani nie wpisywać sekund z samych minut protokołu.

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
- **PR #58 — scalony**, commit `380cc5a`, merge `1ae4571`. CI PR 39263872856, CI main 39264014026, publikacja 39264013991, Pages 39264013114 i pełny sync 39264014036: **success**. Przed merge: **175 testów Python, 14 frontendowych OK**.
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

## Bieżąca zmiana po #58 — odzyskane transmisje i przyszłe samobóje

- Oficjalny link YouTube na stronie PLP prowadzi do kanału `UCd0p73Dp5Eya7c4tQ8EoLZA` (340 materiałów). Wyszukiwanie kanału Bosch ujawniło 7 transmisji ligowych i 1 Superpucharu. Wszystkie dokładne daty i długości odczytano z odtwarzacza/opisu. Przypisania i dowody są w `data/video_updates.json`; kanał dodany do istniejącego synchronizatora, zakładka `streams`, filtr Bosch. Bez nowej zależności.
- Nowe mecze z filmem: 8255, 9486, 9805, 10145, 10990, 11397, 11798. Superpuchar z 06.11.2022 nie zwiększa archiwum ligowego. Wywiady MVP i Turbo Podlasiak nie są traktowane jako transmisje meczów.
- Uzupełniono istniejący importer o samobóje z oficjalnego ID, nazwiska, minut i uzgodnionego bilansu straconych; istniejący plik dowodowy jest rozszerzany idempotentnie. Dwie różne osoby mogą strzelić samobója w tym samym meczu. Nieznane ID/brak minut/sprzeczny wynik pozostają pending.
- **182 testy Python i 14 frontendowych OK**. Oryginalne 113 rekordów niezmienione, 293 gole, 6 samobójów, 988 występów. Status końcowych workflow wymaga sprawdzenia po merge.
- Dodatkowe 3 obejrzane akcje w transmisji 10145: 488 s (Jurkowicz Mateusz, PLP 2′), 1265 s (Karolczuk, 16′), 1318 s (Jurkowicz Rafał, 17′). Klatki i opis relacji komentarz/wynik/PLP zapisane. Sekundy oznaczają obejrzaną fazę akcji, nie deklarację dokładnej klatki przekroczenia linii. Bramka na 4:3 pozostaje bez linku: komentarz podaje gola około 47:03, ale sprawdzony kadr 47:04 pokazuje drugi koniec boiska. Sama transkrypcja nie wystarcza do metody `observed_video_frame`.
