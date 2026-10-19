# Stan kompendium Bosch — 19.10.2026

PR #64 scalony jako `0d8598bee3437b89d432ebab1ccbdfba89dff5fe` po zielonym rzeczywistym checku `118186058259` (CI `39289476437`). CI main `39289756507`, publikacja XLSX `39289757043` i Pages `39289756398` zakończone sukcesem. Produkcyjny JSON potwierdził 46 osób, 113 meczów, 15 odnośników, 11 minimów karier, rozliczone pola Gołąbeskiego i 33 występy Sołowieja; pobrany XLSX ma 7 arkuszy i źródło 10050. Bieżąca rewizja koryguje cztery dalsze błędne powiązania filmów. Publikację konkretnego commita potwierdzamy osobno w issue #33 po CI i kontroli portalu oraz XLSX.

201 testów Python i 14 testów frontendowych przeszło lokalnie. Wszystkie 10 generatorów/audytów offline, walidacje, składnia JS, compileall i diff check OK. Nie nazywać projektu ukończonym: 16 punktów wykonanych, 4 częściowe. Status odnosi się do danych i funkcji tej rewizji; nie jest deklaracją odzyskania brakujących źródeł.

## Wszystkie 20 punktów

| Punkt | Stan | Dowód / zakres pozostały |
|---|---|---|
| 1 | Wdrożone | #55, #56, #58: nowy sezon 2027 przez istniejący pipeline, ID ligi/tabeli, wzrost do 114/115 meczów bez utraty pierwszych 113. #62: osobne zgłoszenia kadry z zerem, właściwa liga i historia niezależna od aktualnego klubu. |
| 2 | Wdrożone | Nowe gole, minuty, samobóje, asysty, MVP i kartki; nieznane ID/minuty/sprzeczności trafiają do pending. #62: bezpośrednie czerwone oraz wykluczenia po 2 ŻK są rozdzielone. |
| 3 | Wdrożone | 13 starych ID odzyskanych; regresja nowego nieznanego ID bez fikcyjnego profilu; bieżący backfill bez nierozpoznanych ID. |
| 4 | Wykonane — jawne ograniczenie źródła | 34 porównania HTML/API/widoku wyjaśnione. Pozostałe 1M i 1ŻK Gołąbeskiego znaleziono w protokole 10050; PLP nie oznaczyła sezonu. Osobny wiersz z datą i źródłem rozlicza znane sumy bez wymyślania sezonu ani zwiększania 13M/4ŻK/1CK. |
| 5 | Częściowo — ograniczenie źródeł | 35 publicznych bilansów, 11 całych karier niepotwierdzonych. Dla wszystkich 11 odtworzono minimum z przeglądu 2415 publicznych wydarzeń: 44 protokoły, 79 występów. Portal i XLSX pokazują zakres i źródła. Nieznane inne ID oraz usunięte wydarzenia wykluczają deklarację pełnej kariery. |
| 6 | Częściowo — ograniczenie źródeł | 18 potwierdzonych portretów, 28 braków przy 46 osobach. #60 odzyskał 3 prawdziwe portrety; dalsze kopie mają placeholdery. Dodatkowe wyszukiwanie artykułów po nazwiskach: pełne imię i nazwisko Daniluka w 4 artykułach, sprawdzone grafiki przedstawiają koszulki bez twarzy. Brak nowego potwierdzonego portretu; zapytanie Żak ograniczone do pierwszych 100 wyników. |
| 7 | Wdrożone | Pages z docs, rzeczywista kontrola produkcji i publikacji. |
| 8 | Wdrożone | Oficjalne team ID, aliasy nazw, odrębne kluby o tej samej nazwie. |
| 9 | Wdrożone | Kakareko 1594 z dawnym aliasem; Rutkowski 7284/13060 scalony; dwaj Kuźmowie pozostają odrębni. |
| 10 | Wdrożone | Pełne rankingi oddzielone od minimów, G+A i stopy nie udają pełnych wyników przy brakach. |
| 11 | Wdrożone | 113 szczegółowych protokołów ligowych i kontrola przyszłego wzrostu. |
| 12 | Wdrożone | 988 źródłowych występów, historia i linki do meczów. Dodatkowe protokoły Superpucharu nie powiększają archiwum ligowego. |
| 13 | Wdrożone | Źródła pól, Bosch osobno od całej PLP. Jeden oficjalny link w całym profilu, odrębne źródła rzeczywistych uzupełnień i meczów. |
| 14 | Częściowo | 120 filmów, 53/113 meczów z nagraniem, 60 bez, 7 materiałów do identyfikacji i 4 odrzucone powiązania. Po potwierdzeniu użytkownika dwa filmy przypisano do 8295. Kontrola dat i boisk usunęła fałszywe pokrycie 8276/9721 oraz poprawiła części OSMAR/CEDC. Wszystkie filmy mają datę, w tym 30 z 2026. Odczyt 59 wcześniejszych stron bez filmu: zgodne ID, brak YouTube; to nie dowód braku filmu gdzie indziej. |
| 15 | Częściowo — przegląd wideo | 10 obejrzanych akcji i 5 oznaczonych komentarzy gola z automatycznych napisów; 149 goli w meczach z filmem w kolejce, w tym 8295. Cztery gole z poprzedniej kolejki wróciły do braków nagrania po odrzuceniu błędnych powiązań, nie zostały zweryfikowane. Wszystkie 5 goli Boscha w 7851 ma obejrzane fragmenty. |
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
- Gołąbeski 7270: nadal 13M/4ŻK/1CK. Protokół 10790 przypisuje znany występ i czerwoną w 24′ do Superpucharu 2024. Protokół 10050, Bosch–Mają Rozmach 23.03.2024, wyjaśnia pozostałe 1M i 1ŻK. Brak sezonu w źródle jest widoczny w osobnym wierszu. Wszystkie znane pola rozliczone, cała kariera nadal niepełna.
- Sołowiej 7285: publiczny baraż 7882 z 26.03.2023 podnosi potwierdzone minimum Boscha z 32 do 33 występów. Pozostałe liczby bez zmian, brak sezonu oznaczony w historii. Surowy dawny bilans zachowany, nie dopisano meczu do 113 ligowych.
- Zalewski 12288: Orlik 2025 0M, Superpuchar 2025 1M (protokół 12363). Publiczne HTML i REST mają 0, pomijając puchar. Surowe źródło zachowane, portal pokazuje 1 z jawnym uzupełnieniem. Regresja chroni przed podwojeniem, gdy PLP doda puchar pod inną nazwą.
- Orlik 2026: pięciu znanych zgłoszonych bez występów — Dołżyk, Mateusz Jurkowicz, Kadłubowski, Karpiński i Żak. Widoczni w filtrze graczy i na stronie sezonu. Nie są dopisywani do protokołów jako grający.
- Czerwone w PLP to bezpośrednie kartki. W 113 protokołach są 4 takie czerwone i 7 odrębnych wykluczeń po 2 ŻK. Dwie żółte z różnych meczów nie tworzą wykluczenia. Widoki i XLSX rozdzielają te pola.
- CSV usunięty; oficjalny profil linkowany jednokrotnie; etykiety nawigacji, w tym Zdjęcia PLP, zawijają się bez ucinania. Daty w danych i sortowaniu są ISO, znane filmy otrzymują odświeżone metadane, brak limitu 120 widocznych filmów i 300 pozycji kanału.

## PR-y i sprawdzone uruchomienia

- #54–#61: publikacja, nowe sezony, ochrona bilansów, źródła, XLSX/połowy/minima, 7 transmisji PLP, 3 portrety i archiwalny Superpuchar; szczegóły w historii Git i wcześniejszych PR.
- #62: merge `4731070`; kadra z zerem, daty, CSV, źródła, nawigacja i kartki. CI PR `39275094656`, CI main `39275575114`, publikacja `39275575120`, Pages `39275328107` — success.
- Pełny sync po #62 `39275733253` — success; bot `c1cae88`. Prawdziwe daty 30 filmów z 2026, wszystkie 120 rekordów mają datę. Pages `39276461012` — success. Produkcyjny JSON 46/113/120 i 30 dat z 2026 potwierdzony także w przeglądarce.
- #63: 24 źródłowe protokoły innych klubów, wyjaśnienia różnic, dwa Superpuchary, osiem fragmentów goli, pełna lista zgłoszonych bez występów na stronie sezonu i jeden link w całym profilu. Scalony po rzeczywistym zielonym checku; CI main `39287584259` i publikacja XLSX `39287584217` success. Zapisano zrzut potwierdzenia scalenia.
- Rewizja public-protocol-recovery: 199 Python + 14 frontend OK. Chroniona baza nadal 113/293/988; znane pola statystyk wszystkich graczy bez nierozliczonych reszt. 11 minimów karier, 15 odnośników, brak nowych zależności.
- Rewizja video-fixture-audit: 201 Python + 14 frontend OK. OSMAR RkV8q7Vfy4g/uby5J-1mtDs przeniesione z 8276 do 10990; CEDC bQ3De8L7mnA z 11095 do 8373; CF Bojary Qc0s7ZjnInM odpięte od 9721. Pokrycie po usunięciu fałszywych wpisów 53/113. Nowa wspólna kontrola chroni także stare i ręczne powiązania przed publikacją filmu wcześniejszego niż mecz.
- Użytkownik potwierdził 6vsemMiGuPk i Kh4IuHMwcPQ jako Bosch–Wiara Piasta II 01.07.2023 (8295, 1:0). Powiązania mają kategorię user_confirmed_fixture i jawną notatkę; neutralne etykiety Nagranie 1/2, bez niepotwierdzonej połowy. Pokrycie wzrosło do 55 meczów; zostało 7 nierozpoznanych filmów. Gol 29′ Sołowieja dopisany do kolejki przeglądu, bez odnośnika czasowego.

- Sprawdzenie produkcji wykazało nowy JSON przy zachowanym w przeglądarce starym skrypcie. Adres app.js w index.html otrzymał wersję 20261019-protocols, aby po publikacji wczytać interfejs nowych minimów i komentarzy.

## Sprawdzone źródła — nie powtarzać całych odczytów bez nowej przesłanki

- PLP 6951: 8 sezonów ligowych i 4 Superpuchary; 113 meczów ligowych. Pierwszych 113 nie zmieniono, przyszłe sezony mogą rozszerzać archiwum.
- 26 sitemap, 4559 URL, 1187 URL graczy oraz all-time 1837 osób. Brakujące pełne kariery: 10321, 10604, 7266, 7270, 7271, 7278, 7282, 7285, 7286, 8655, 8916. REST 401 i posty z ID 404.
- Internet Archive: kopie 7270, 7271, 7278, 7285 potwierdzone po postid. Superpuchar 2022 przypisuje 4 wcześniejsze pola, 3 rzeczywiste portrety odzyskane. Dalsze dokładne kopie mają placeholdery; brak wyniku pełnej nazwy nie dowodzi braku innych aliasów.
- WordPress: wcześniejszy pełny audyt 91 mediów / 53 nazw; nowy bezpośredni parent dla 11 niedostępnych profili daje 0 mediów. Nowy 12288 również bez featured/parent portretu. Nie identyfikować osoby ze zdjęcia klubowego.
- Kariery: pełne protokoły sezonów 139 (211 wydarzeń), 141 (197) i 104 (65). Zdarzenia 10748, 11748, 3994, 3992 mają pustą listę leagues; sumy z ligą zgadzają się z REST, wszystkie z HTML. Wyciąg 24 występów w career_competition_evidence.json, bez ingerencji w Bosch.
- Superpuchary: pięć wydarzeń Boscha w sezonach 119/127/140/145; protokoły 10790 i 12363 zapisane jako JSON źródłowy. Dodatkowy odczyt całych sezonów 120/125/126 nie znalazł kolejnego wpisu Gołąbeskiego poza znanymi protokołami.
- Pełne publiczne API wydarzeń: 2415 różnych ID na 25 stronach, od 15.05.2021 do 18.10.2026. Wyciąg 44 protokołów 11 graczy zapisany w `data/source-evidence/public-career-protocol-review-20261019.json`. Surowe protokoły 10050 i 7882 mają puste seasons/leagues. Dodatkowe artykuły z marca 2024 nie dają jednoznacznego oznaczenia sezonu 10050, więc go nie przypisano.
- Artykuły i portrety: `data/source-evidence/news-portrait-review-20261019.json`; pełne nazwiska wymagane obok siebie, wyniki zawierające osobno imię i nazwisko odrzucone. Grafiki TOP5/TOP6 z koszulkami nie są portretami Daniluka. Brak wyniku wyszukiwania nie jest dowodem, że zdjęcie nie istnieje.
- YouTube: dwa kanały prywatnych autorów i oficjalny PLP UCd0p73Dp5Eya7c4tQ8EoLZA. Odczyt pierwotnej listy 59 oficjalnych stron wydarzeń bez filmu: zgodne ID, brak YouTube. Użytkownik następnie potwierdził filmy „1”/„2”, daty 2/3.07.2023, jako Wiarę Piasta II 01.07.2023. Zmniejsza to bieżącą listę braków do 58 spotkań.
- Późniejszy audyt filmów: `data/source-evidence/video-fixture-review-20261019.json` i 4 kadry boisk. OSMAR 23.11.2024 to hala VI LO (10990, venue 109), nie Orlik 27.05.2023 (8276, venue 67). CF Bojary 26.08.2023 pokazuje boisko odkryte i poprzedza halę 9721 z 10.02.2024. CEDC 10.09.2023 ma HT 2:0 zgodne z 8373 i drugą częścią 5:1, nie późniejszą halą 11095. Po tych korektach bieżąca lista braków to 60 spotkań; poprzednie 58 obejmowało dwa fałszywe przypisania.
- Akcje z klatkami: 7851 — Mateusz Jurkowicz 3′/7s i 23′/13s, Sołowiej 26′/8s, Markowski 29′/9s; 10145 — Mateusz Jurkowicz 2′/488s, Karolczuk 16′/1265s, Rafał Jurkowicz 17′/1318s; orlik26-1 — Karolczuk 23′/145s, opublikowana wersja ZOOM 200%, ponownie sprawdzona w HD. Są to obejrzane fazy akcji, nie deklaracje dokładnej klatki przecięcia linii.
- Dodatkowe obejrzane akcje: 10990 Karolczuk 27′ / s3iMR88rCKE 1826s oraz 7851 Sołowiej 24′ / QXRjrPldpi0 14s. Kadry i opis przebiegu zapisane w reports/evidence. Usunięto limit czterech filmów w kolejce przeglądu, który ukrywał ten krótki fragment.
- Aptel 9805 i Vesta 11397 bez transkrypcji; fragment Aptelu 1490–1515s nie dał pewnego gola. W 10145 gol 39′ przy komentarzu 47:03 jest poza kadrem: odnośnik ma metodę broadcast_commentary_captions i etykietę YouTube — komentarz, nigdy observed_video_frame.
- Pozostałe komentarze: 8255 Sołowiej 11′/1126s i 35′/2831s oraz Karolczuk 37′/2949s, PWnZ2yifLNI; 11798 Karpiński 32′/2482s, 8mVCFD11ZGo. Zapisano krótkie fragmenty automatycznych napisów z sekundą, URL i ograniczeniami; nie są dowodem czytelnego obrazu gola. Walidator wymaga oficjalnej transmisji i zgodnej sekundy.

## Następne zadania

1. Dokończyć przegląd 149 goli w meczach z filmem i identyfikację 7 materiałów; szukać nowych dowodów nagrań dla 60 spotkań. Użytkownik otrzymał linki Olimp (2), Koledzy z Boiska, Medgal, Rambo, Krokus i Prestige; klasyfikacja oczekuje na jego informację. Odpięty CF Bojary również wymaga ustalenia rzeczywistego spotkania, choć błędne przypisanie do 9721 zostało jednoznacznie odrzucone.
2. Uzupełniać 11 całych karier i 28 portretów wyłącznie po nowym dowodzie. Minima z 2415 protokołów już odtworzono. Brak danych nie jest zerem, minimum nie jest pełnym bilansem, Bosch nie jest całą PLP.
3. Kończyć scalanie/publikację wyłącznie po zielonym CI dla faktycznego head. Issue #33 pozostaje otwarte dla punktów 5, 6, 14, 15; protokoły bez oznaczenia sezonu mają jawne ograniczenie źródła.

Repo ma uwierzytelniony git push oraz sesję GitHub w przeglądarce. Brak gh. Nie odczytywać tokenów z credential helpera: wcześniej odrzucił to auto-review. Lokalna instalacja istniejącego yt-dlp też została odrzucona; nie ponawiano, metadane skutecznie odświeżył istniejący workflow. Python 3.12 z cache Codex ma openpyxl; systemowy 3.14 go nie ma. Nie dodano nowych zależności. Zapis sandboxa czasem wymaga zatwierdzonego wykonania narzędzia.
