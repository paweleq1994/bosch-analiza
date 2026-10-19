# Stan wdrożenia kompendium Bosch — 19.10.2026

Ostatni sprawdzony main: `6fad4b1` (merge PR #60, po `e23c0bc` — synchronizacji #59).
185 testów Python i 14 frontendowych OK. Lokalny generator działa offline. Produkcyjny JSON, XLSX, trzy nowe obrazy, źródła sezonów i linki akcji zostały sprawdzone.
Pełna synchronizacja #60: `39268464180` **success**, 14:23–14:26 UTC — PLP, trzy kanały, profile, media, scouting, eksporty i publikacja.
Issue #33: **otwarte i zaktualizowane**, 15 wykonanych i 5 częściowych punktów (4, 5, 6, 14, 15). Projekt nadal ma nieukończony zakres danych opisany poniżej; nie nazywać go w 100% ukończonym.

## Wszystkie 20 punktów

| Punkt | Stan | Dowód i zakres pozostały |
|---|---|---|
| 1 | Wdrożone | #55, #56, #58: test istniejącego importu → sezon 2027, liga/tabela/ID, 114/115 meczów, liderzy, historia, walidator; bez utraty pierwotnych 113. Źródło nie ogłasza jeszcze kolejnego rzeczywistego sezonu. |
| 2 | Wdrożone | #36, #55, #59: nowe gole i minuty, samobóje, asysty, kartki, MVP. Dwie różne osoby mogą mieć samobója w tym samym meczu. Brak ID/minut lub sprzeczny wynik → pending z przyczyną. |
| 3 | Wdrożone | 13 dawnych ID rozwiązanych w #35; regresja nowego 99999 w #55: brak fikcyjnego profilu, jawny audyt i pending. |
| 4 | Częściowo — dane nadal niepewne | 33 różnice opisane zawodnik/sezon/źródło; 29 wyjaśnionych. #60 przypisał 4 z 7 pól historycznych do Superpucharu. Pozostają 4 porównania agregatów oraz 3 pola Gołąbeskiego bez potwierdzonego sezonu. |
| 5 | Częściowo — brak aktualnych źródeł | 34 pełniejsze kariery PLP, 11 niepełnych. REST 401, publiczny post 404, brak w sitemapach i all-time. Odnalezione stare kopie to częściowe źródła z datą, nie pełna kariera do dziś. |
| 6 | Częściowo — 18 portretów, 27 braków | #60: odzyskane zdjęcia Gołąbeskiego, Gorbacewicza, Sołowieja z pola zdjęcia profilu o zgodnym postid. Dalsze kopie mają placeholdery. Bez rozpoznawania osoby ze zdjęcia klubowego. |
| 7 | Wdrożone | #30; Pages z docs, rzeczywista kontrola produkcji po zmianach. |
| 8 | Wdrożone | #37: oficjalne team ID, aliasy historyczne, odrębne kluby o tej samej nazwie. |
| 9 | Wdrożone | Kakareko 1594 i alias new-kakareko-kamil, Rutkowski 7284/13060 scalony; Gabriel i Piotr Kuźma odrębni. |
| 10 | Wdrożone | #37, #58: pełne rankingi oddzielone od minimów, sezonowe G+A nie klasyfikuje minimów jako pełnych wyników; porównywarka ≥ i brak stopy z minimum. |
| 11 | Wdrożone | 113 szczegółowych protokołów i regresja wzrostu archiwum; stare protokoły bez zmian. |
| 12 | Wdrożone | 988 źródłowych występów, historia mecz po meczu i odnośniki PLP. |
| 13 | Wdrożone | #51, #60: źródła i zakresy pól, bezpośrednie linki do archiwalnych tabel sezonów. |
| 14 | Częściowo — pozostała identyfikacja | #57 poprawił błędny film Vesty; #59 odzyskał 7 transmisji PLP. 54/113 meczów z nagraniem, 59 bez; 9 materiałów do identyfikacji. Dodatkowy Superpuchar poza pokryciem ligowym. |
| 15 | Częściowo — pozostały przegląd materiału | 5 obejrzanych sekund akcji i klatki dowodowe; 162 gole w kolejce. Transkrypcja pomaga znaleźć fragment, nie zastępuje obejrzenia. Gola poza kadrem nie oznaczono jako observed_video_frame. |
| 16 | Wdrożone | #38: trendy sezonowe z prawidłowymi brakami danych. |
| 17 | Wdrożone | #29, #58: porównywarka, filtry sezonu i minima. |
| 18 | Wdrożone | #34, #58: forma, serie, czyste konta, minuty goli; 113 poprawnych HT: I połowa 130:94, II 163:135, stany HT/FT. Brak/sprzeczność HT wyłącza obliczenie. |
| 19 | Wdrożone | #30, #55, #58: dynamiczny najnowszy sezon, regresja następnego sezonu i chronologii hali. |
| 20 | Wdrożone i sprawdzone na produkcji | #54 i #58: poprawne test -s i staging raportów, XLSX normalizuje LF/CRLF i uwzględnia kod eksportera. CSV, 7 arkuszy XLSX, jakość i lineage działają. |

## Aktualne metryki

- 45 kanonicznych zawodników, 8 sezonów, 113 meczów ligowych i 113 zweryfikowanych protokołów.
- 293 bramki = 289 zawodników + 3 samobóje rywali + 1 administracyjna. 0 nierozliczonych. 6 samobójów Boscha na korzyść rywali.
- 988 występów; 0 nierozpoznanych ID w bieżącym backfillu.
- 34 pełniejsze publiczne kariery PLP, 11 niepełnych; Bosch i cała PLP pozostają osobnymi zakresami.
- 33 różnice źródeł, 29 wyjaśnionych, 4 nadal niepewne; 0 sprzeczności sezonowych z protokołami.
- 3 nieprzypisane pola u jednej osoby (wcześniej 7 u czterech): Gołąbeski 7270 — występy 2, żółte 1, czerwone 1.
- 18 potwierdzonych portretów, 27 braków (wcześniej 15/30).
- 120 materiałów wideo; 54 mecze z filmem, 59 bez (wcześniej 112 i 48/65; jedno błędne przypisanie cofnięto, następnie odzyskano 7 transmisji).
- 9 materiałów do identyfikacji, 3 odrzucone powiązania / materiały poza archiwum ligowym. Łącznie 12 bez meczu ligowego.
- 5 potwierdzonych odnośników do sekund obejrzanych akcji; 162 gole w kolejce. Kolejka wzrosła po odzyskaniu nowych transmisji, nie przez utratę zweryfikowanych linków.

## Nowe scalone PR-y i istotne commity

| PR | Zakres | Commit / merge |
|---|---|---|
| #54 | Kontrole publikacji, staging kolejki i triggery | 07bfa56 / 06d525a |
| #55 | Nowy sezon przez cały istniejący pipeline, ID, chronologia | aaded26 / d2b28ef |
| #56 | Sezonowe rozliczenie źródeł, ochrona bogatszych historycznych bilansów po prawdziwym sync | d688231 + 12d55c8 / 29694db |
| #57 | Cofnięcie błędnej Vesty, ręczne odrzucenia, 2 obejrzane akcje | 54323fc / 01b4e20 |
| #58 | Przenośny hash/cache XLSX, połowy, minima, walidator przyszłego wzrostu, README | 380cc5a / 1ae4571 |
| #59 | 7 transmisji PLP, osobny Superpuchar, 3 dalsze obejrzane akcje, przyszłe samobóje | 5266da2 / 83600b8 |
| #60 | 3 portrety i 4 pola przypisane dzięki Internet Archive; zachowanie niepełności kariery | 409f3ac / 6fad4b1 |

`f864f05` był commitem publikatora po #56, nie mergem. Synchronizacja `ea3c315` po #55 ujawniła obniżanie starych bilansów przez agregaty meczowe; #56 naprawił przyczynę i zachował pełny odczyt PLP. Synchronizacje po #56/#57 ujawniły konflikt binarnego XLSX; #58 usunął zbędną regenerację spowodowaną LF/CRLF. Pełne synchronizacje #58 i #59 już potwierdziły poprawkę.

## Testy i produkcja

- Python 3.12.14, openpyxl 3.1.5: 185 unittest OK; wszystkie 14 testów frontendowych Node OK.
- Wszystkie 10 generatorów/audytów offline, walidacje portalu/scoutingu, compileall, składnia 3 skryptów JS i diff check OK. Kolejny eksport: XLSX export unchanged.
- CI PR #60: 39268296739 success; CI main 39268464228 success; publikacja 39268464246 success; Pages 39268463698 success.
- Pełny sync #60: 39268464180 success. Zapis issue #33 potwierdzony ponownym odczytem publicznego API; 15 checkboxów wykonanych, 5 niewykonanych, stan open.
- Pełny sync #58: 39264014036 success; pełny sync #59: 39265848610 success, bot e23c0bc (tylko porządek w video_updates), Pages 39266277405 success.
- Produkcja po #60: JSON 45/8/113/120, 54 mecze z filmem, 18 portretów, 5 znaczników, 3 nieprzypisane pola. Publiczne nowe obrazy HTTP 200 i zgodne bajtowo z repozytorium. Archiwalne sezony i brak pełnej kariery widoczne w portalu.
- Publiczny XLSX HTTP 200, 100785 bajtów identycznych z commitem, 7 arkuszy, 46 wierszy Zawodnicy i 114 Mecze. SHA256 źródła: 13b9bce30ac25da50bae0468b436d3370623c5dc6b98cd9142d8f4efa3607627.
- Publiczne raporty w repozytorium HTTP 200. W przeglądarce sprawdzono sortowanie tabeli połów, źródło Superpucharu, galerię i brak błędów JavaScript na kontrolowanych widokach.

## Sprawdzone źródła i ograniczenia — nie powtarzać identycznych odczytów bez powodu

- PLP drużyna REST 6951: 12 sezonów (8 lig, 4 Superpuchary); ostatni mecz 17.10.2026 Juan Pablo 4:3 jest w snapshotcie. Brak kolejnego sezonu w tym odczycie.
- 26 sitemap, 4559 URL, 1187 URL zawodników: 0 nowych profili. All-time: 1837 zawodników. Brakujące aktualne pełne kariery: ID 10321, 10604, 7266, 7270, 7271, 7278, 7282, 7285, 7286, 8655, 8916. Wszystkie REST 401, publiczne adresy z ID 404.
- Internet Archive: CDX HTTP 200. Odczyt całego indeksu do 5000 URL przekroczył 35 s — to nie dowód braku kopii. Zawężone odczyty pełnych nazw zadziałały. Kopie postid 7270, 7271, 7278, 7285 zapisane jako źródła i fragmenty HTML. Oryginalne slugi 404.
- Gorbacewicz, Kossakowski i Sołowiej: Superpuchar 2022 potwierdza łącznie 3 występy i 1 asystę, które były już w sumach Boscha. Korekta przypisuje je do sezonu, nie dodaje drugi raz. Stare kopie nie ustanawiają aktualnej pełnej kariery.
- Gołąbeski: późniejsza kopia 14.04.2024 potwierdza 2+3 występy w istniejących sezonach halowych i zero Superpucharu 2023; nie wyjaśnia trzech pozostałych pól. Brak późniejszej kopii HTTP 200 w tym zapytaniu do 19.10.2026.
- Zdjęcia: poprzedni pełny audyt WordPress obejmował 91 mediów i 53 zapytania nazw. Archive ujawnił 3 prawdziwe pola portretu (postid + element zdjęcia), obrazy obejrzano. Dla 27 pozostałych: 15 dokładnych adresów, sprawdzone kopie mają placeholdery w dwóch szablonach PLP; 12 bez wyniku dokładnej nazwy. Inne aliasy pozostają możliwością, brak wyniku nie oznacza nieistnienia.
- Nierozstrzygnięte agregaty HTML/API: Piotr Kuźma 4577 (CEDC Polmos, nie Bosch) — Orlik 2024 występy 7/6 i Hala 2024/2025 11/10; Daniluk 2204 Lato 2021 2/1; Kakareko 1594 Lato 2021 występy 4/3 i gole 1/0. Zachowano pełną karierę HTML; różnic nie dodano do Boscha.
- Kanały YouTube: dwa stare oraz oficjalny UCd0p73Dp5Eya7c4tQ8EoLZA. Oficjalne transmisje 8255, 9486, 9805, 10145, 10990, 11397, 11798 powiązano po dokładnej dacie, drużynach i sezonie. Superpuchar 06.11.2022 jest poza archiwum ligowym. Wywiady nie są transmisjami meczów.
- Film Vesta hcfb9Ttmswo odrzucono jako mecz 7814: film ma boisko odkryte i datę 26.08.2023, protokół 26.02.2023 wskazuje halę VI LO, venue 109. Muzyczny 8SF7bbYDS30 również poza meczami. Nie odrzucać innych filmów na podstawie rekomendowanych miniaturek.
- Zweryfikowane akcje: mecz 7851 — Mateusz Jurkowicz 3′/7 s i 23′/13 s; mecz 10145 — Mateusz Jurkowicz 2′/488 s, Karolczuk 16′/1265 s, Rafał Jurkowicz 17′/1318 s. Klatki i opisy w reports/evidence oraz video_goal_evidence.json. Są to obejrzane fazy akcji; nie deklarują dokładnej klatki przecięcia linii przez piłkę. Zwycięski gol 10145 pozostaje w kolejce: przy komentarzu około 47:03 kamera pokazuje drugi koniec boiska.

## Następne zadania i zasady kontynuacji

1. Dokończyć przegląd 162 goli, 9 nieprzypisanych materiałów i dalszych źródeł dla 59 meczów bez nagrania. Nie zgadywać sekund z minut meczu ani nazwisk z twarzy.
2. Uzupełniać 11 karier, 27 portretów, 3 pola Gołąbeskiego i 4 porównania źródeł tylko po nowym dowodzie; nie powtarzać całego audytu źródeł z dzisiejszą datą.
3. Nowa sesja zaczyna od aktualnego main i tego pliku. Nie odbudowywać działających importerów, galerii, provenance ani analityki.
4. Brak wartości ≠ zero; minimum ≠ pełny bilans; Bosch ≠ cała PLP. Zachować 113 historycznych protokołów i ID/URL źródeł. Nie tworzyć fikcyjnych danych dla kompletności.

Repozytorium ma dostęp przez git push gałęzi. gh nie jest zainstalowane. Użytkownik zalogował zwykłą sesję GitHub w przeglądarce Codex; PR-y tworzono i scalano po zielonym CI przez UI. Automatyczna kontrola wcześniej odrzuciła odczyt tokenu z menedżera Git do osobnych żądań API; nie ponawiać. Systemowy Python 3.14 nie ma openpyxl, używany runtime 3.12 ma istniejącą zależność. Nie dodano nowych zależności. Błędy sandboxa przy zapisie raportów rozwiązano zatwierdzonym wykonaniem narzędzia, bez zmiany uprawnień projektu.
