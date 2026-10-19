# Stan kompendium Bosch — 19.10.2026

Ostatni potwierdzony main: `c1cae88` (PR #62 i pełna synchronizacja dat). PR #63 zawiera pozostałe opisane poprawki i siódmy potwierdzony fragment gola. GitHub opóźnia start aktualnych kontroli: starsze przebiegi pokazują Starting job bez kroków, ostatnie czekają w kolejce. Scalenie i publikacja #63 pozostają zależne od zielonego CI dla jego rzeczywistego head.

196 testów Python i 14 testów frontendowych przeszło lokalnie. Wszystkie 10 generatorów/audytów offline, walidacje, składnia JS, compileall i diff check OK. Nie nazywać projektu ukończonym: 15 punktów wykonanych, 5 częściowych.

## Wszystkie 20 punktów

| Punkt | Stan | Dowód / zakres pozostały |
|---|---|---|
| 1 | Wdrożone | #55, #56, #58: nowy sezon 2027 przez istniejący pipeline, ID ligi/tabeli, wzrost do 114/115 meczów bez utraty pierwszych 113. #62: osobne zgłoszenia kadry z zerem, właściwa liga i historia niezależna od aktualnego klubu. |
| 2 | Wdrożone | Nowe gole, minuty, samobóje, asysty, MVP i kartki; nieznane ID/minuty/sprzeczności trafiają do pending. #62: bezpośrednie czerwone oraz wykluczenia po 2 ŻK są rozdzielone. |
| 3 | Wdrożone | 13 starych ID odzyskanych; regresja nowego nieznanego ID bez fikcyjnego profilu; bieżący backfill bez nierozpoznanych ID. |
| 4 | Częściowo | 34 porównania HTML/API/widoku mają dowody wyjaśnienia. Pozostają tylko 1 występ i 1 ŻK Gołąbeskiego bez sezonu. Jego sumy nie zostały zwiększone przy przypisaniu Superpucharu. |
| 5 | Częściowo — ograniczenie źródeł | 35 publicznych bilansów, w tym Zalewski jawnie uzupełniony niezależnym protokołem; 11 całych karier niepotwierdzonych. REST 401, posty z ID 404, brak aktualnych profili w sitemapach/all-time. Stare kopie nie dają kariery do dziś. |
| 6 | Częściowo — ograniczenie źródeł | 18 potwierdzonych portretów, 28 braków przy 46 osobach. #60 odzyskał 3 prawdziwe portrety; dalsze kopie mają placeholdery. Nowy odczyt attachment parent dla 11 niedostępnych profili: 0 publicznych mediów. |
| 7 | Wdrożone | Pages z docs, rzeczywista kontrola produkcji i publikacji. |
| 8 | Wdrożone | Oficjalne team ID, aliasy nazw, odrębne kluby o tej samej nazwie. |
| 9 | Wdrożone | Kakareko 1594 z dawnym aliasem; Rutkowski 7284/13060 scalony; dwaj Kuźmowie pozostają odrębni. |
| 10 | Wdrożone | Pełne rankingi oddzielone od minimów, G+A i stopy nie udają pełnych wyników przy brakach. |
| 11 | Wdrożone | 113 szczegółowych protokołów ligowych i kontrola przyszłego wzrostu. |
| 12 | Wdrożone | 988 źródłowych występów, historia i linki do meczów. Dodatkowe protokoły Superpucharu nie powiększają archiwum ligowego. |
| 13 | Wdrożone | Źródła pól, Bosch osobno od całej PLP. Jeden oficjalny link w całym profilu, odrębne źródła rzeczywistych uzupełnień i meczów. |
| 14 | Częściowo | 120 filmów, 54/113 mecze z nagraniem, 59 bez, 9 materiałów do identyfikacji. Wszystkie filmy mają datę; odzyskane prawdziwe daty 30 filmów z 2026. Nowy odczyt 59 stron wydarzeń: 59 HTTP200 i zgodnych postid, 0 osadzonych YouTube. Brak osadzenia nie dowodzi braku filmu gdzie indziej. |
| 15 | Częściowo — przegląd wideo | 7 potwierdzonych fragmentów akcji, kadry i notatki źródłowe; 160 goli nadal wymaga weryfikacji. Brak klatki lub nieczytelny przebieg nie upoważnia do zgadywania sekundy. |
| 16 | Wdrożone | Sezonowe wykresy z prawidłowymi brakami danych. |
| 17 | Wdrożone | Porównywarka sezonowa, oznaczenie minimów. |
| 18 | Wdrożone | Serie, forma, czyste konta, minuty goli. 113 poprawnych HT: I połowa 130:94, II 163:135; brak/sprzeczność HT wyłącza obliczenie. |
| 19 | Wdrożone | Dynamiczny najnowszy sezon i chronologia hali; test nowego sezonu. |
| 20 | Wdrożone | XLSX, 7 arkuszy, raporty i panel jakości. CSV usunięty na życzenie użytkownika. Hash danych niezależny od CRLF/LF, cache obejmuje kod eksportera. |

## Dane i poprawki użytkownika

- 46 kanonicznych osób, 8 sezonów, 113 meczów i protokołów ligowych; 988 występów, 0 nierozpoznanych ID.
- 293 bramki = 289 zawodników + 3 samobóje rywali + 1 administracyjna; 0 nierozliczonych. 6 samobójów Boscha na korzyść rywali.
- 35 publicznych bilansów kariery, 11 niepełnych; 18 portretów, 28 braków.
- 34 porównania źródeł: 26 zakresów Superpucharu, 5 wyjaśnień protokołami i wierszami, 2 scalone ID, 1 niezależny protokół Zalewskiego. 0 sprzeczności sezonowych. Dane innych klubów nie zwiększają Boscha.
- Gołąbeski 7270: nadal 13M/4ŻK/1CK. Protokół 10790 przypisuje znany występ i czerwoną w 24′ do Superpucharu 2024. Zostały 1M i 1ŻK bez sezonu. Kariera nadal niepełna.
- Zalewski 12288: Orlik 2025 0M, Superpuchar 2025 1M (protokół 12363). Publiczne HTML i REST mają 0, pomijając puchar. Surowe źródło zachowane, portal pokazuje 1 z jawnym uzupełnieniem. Regresja chroni przed podwojeniem, gdy PLP doda puchar pod inną nazwą.
- Orlik 2026: pięciu znanych zgłoszonych bez występów — Dołżyk, Mateusz Jurkowicz, Kadłubowski, Karpiński i Żak. Widoczni w filtrze graczy i na stronie sezonu. Nie są dopisywani do protokołów jako grający.
- Czerwone w PLP to bezpośrednie kartki. W 113 protokołach są 4 takie czerwone i 7 odrębnych wykluczeń po 2 ŻK. Dwie żółte z różnych meczów nie tworzą wykluczenia. Widoki i XLSX rozdzielają te pola.
- CSV usunięty; oficjalny profil linkowany jednokrotnie; etykiety nawigacji, w tym Zdjęcia PLP, zawijają się bez ucinania. Daty w danych i sortowaniu są ISO, znane filmy otrzymują odświeżone metadane, brak limitu 120 widocznych filmów i 300 pozycji kanału.

## PR-y i sprawdzone uruchomienia

- #54–#61: publikacja, nowe sezony, ochrona bilansów, źródła, XLSX/połowy/minima, 7 transmisji PLP, 3 portrety i archiwalny Superpuchar; szczegóły w historii Git i wcześniejszych PR.
- #62: merge `4731070`; kadra z zerem, daty, CSV, źródła, nawigacja i kartki. CI PR `39275094656`, CI main `39275575114`, publikacja `39275575120`, Pages `39275328107` — success.
- Pełny sync po #62 `39275733253` — success; bot `c1cae88`. Prawdziwe daty 30 filmów z 2026, wszystkie 120 rekordów mają datę. Pages `39276461012` — success. Produkcyjny JSON 46/113/120 i 30 dat z 2026 potwierdzony także w przeglądarce.
- #63: 24 źródłowe protokoły innych klubów, wyjaśnienia różnic, dwa Superpuchary, szósty fragment gola, pełna lista zgłoszonych bez występów na stronie sezonu i jeden link w całym profilu. 196 Python + 14 frontend OK lokalnie. CI oczekuje na runner; stare nieudane kontrole z formatem dat nie dotyczą poprawionego testu.
- Siódmy fragment gola jest w tym samym PR z kadrem HD i przechodzi walidator istniejącego mechanizmu.

## Sprawdzone źródła — nie powtarzać całych odczytów bez nowej przesłanki

- PLP 6951: 8 sezonów ligowych i 4 Superpuchary; 113 meczów ligowych. Pierwszych 113 nie zmieniono, przyszłe sezony mogą rozszerzać archiwum.
- 26 sitemap, 4559 URL, 1187 URL graczy oraz all-time 1837 osób. Brakujące pełne kariery: 10321, 10604, 7266, 7270, 7271, 7278, 7282, 7285, 7286, 8655, 8916. REST 401 i posty z ID 404.
- Internet Archive: kopie 7270, 7271, 7278, 7285 potwierdzone po postid. Superpuchar 2022 przypisuje 4 wcześniejsze pola, 3 rzeczywiste portrety odzyskane. Dalsze dokładne kopie mają placeholdery; brak wyniku pełnej nazwy nie dowodzi braku innych aliasów.
- WordPress: wcześniejszy pełny audyt 91 mediów / 53 nazw; nowy bezpośredni parent dla 11 niedostępnych profili daje 0 mediów. Nowy 12288 również bez featured/parent portretu. Nie identyfikować osoby ze zdjęcia klubowego.
- Kariery: pełne protokoły sezonów 139 (211 wydarzeń), 141 (197) i 104 (65). Zdarzenia 10748, 11748, 3994, 3992 mają pustą listę leagues; sumy z ligą zgadzają się z REST, wszystkie z HTML. Wyciąg 24 występów w career_competition_evidence.json, bez ingerencji w Bosch.
- Superpuchary: pięć wydarzeń Boscha w sezonach 119/127/140/145; protokoły 10790 i 12363 zapisane jako JSON źródłowy. Dodatkowy odczyt całych sezonów 120/125/126 nie znalazł kolejnego wpisu Gołąbeskiego poza znanymi protokołami.
- YouTube: dwa kanały prywatnych autorów i oficjalny PLP UCd0p73Dp5Eya7c4tQ8EoLZA. 59 oficjalnych stron wydarzeń bez filmu: zgodne ID, brak YouTube. Filmy „1”/„2”, daty 2/3.07.2023, mają tylko kandydackie powiązanie z Wiarą Piasta II; pytanie do użytkownika, bez przypisania na podstawie samej daty/strojów.
- Akcje z klatkami: 7851 — Mateusz Jurkowicz 3′/7s i 23′/13s, Markowski 29′/9s; 10145 — Mateusz Jurkowicz 2′/488s, Karolczuk 16′/1265s, Rafał Jurkowicz 17′/1318s; orlik26-1 — Karolczuk 23′/145s, opublikowana wersja ZOOM 200%, ponownie sprawdzona w HD. Są to obejrzane fazy akcji, nie deklaracje dokładnej klatki przecięcia linii.
- Aptel 9805 i Vesta 11397 bez transkrypcji; fragment Aptelu 1490–1515s nie dał pewnego gola. W 10145 wygrywający gol 39′ przy komentarzu około 47:03 jest poza kadrem. Nie zamieniać komentarza w observed_video_frame.

## Następne zadania

1. Dokończyć przegląd 160 goli i identyfikację 9 materiałów; szukać nowych dowodów nagrań dla 59 spotkań.
2. Uzupełniać 11 karier, 28 portretów i dwa pola Gołąbeskiego tylko po nowym dowodzie. Brak danych nie jest zerem, minimum nie jest pełnym bilansem, Bosch nie jest całą PLP.
3. Kończyć scalanie/publikację wyłącznie po zielonym CI dla faktycznego head. Issue #33 pozostaje otwarte dla punktów 4, 5, 6, 14, 15.

Repo ma uwierzytelniony git push oraz sesję GitHub w przeglądarce. Brak gh. Nie odczytywać tokenów z credential helpera: wcześniej odrzucił to auto-review. Lokalna instalacja istniejącego yt-dlp też została odrzucona; nie ponawiano, metadane skutecznie odświeżył istniejący workflow. Python 3.12 z cache Codex ma openpyxl; systemowy 3.14 go nie ma. Nie dodano nowych zależności. Zapis sandboxa czasem wymaga zatwierdzonego wykonania narzędzia.
