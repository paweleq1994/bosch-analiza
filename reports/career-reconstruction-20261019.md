# Rekonstrukcja 11 karier PLP — 19.10.2026

11 aktualnych publicznych profili pozostaje niedostępnych. Kariery odtworzono z liczb w oficjalnych protokołach PLP oraz nowego potwierdzenia użytkownika, że wszystkie wskazane osoby grały w PLP wyłącznie w Boschu. To rekonstrukcje z jawnym źródłem zakresu klubowego, odrębne od 35 dostępnych publicznych bilansów HTML.

## Podstawa rekonstrukcji

- Użytkownik, 19.10.2026: „oni grali tylko w boschu”. [Potwierdzenie z przypisaniem 11 ID](../data/source-evidence/bosch-only-career-scope-20261019.json).
- Pełna publiczna kolekcja SportsPress: **2415 wydarzeń na 25 stronach**. Wszystkie **120 wydarzeń Boscha** mają dane występów: 113 ligowych, 5 Superpucharu i 2 bez oznaczenia sezonu. Łącznie 1045 występów Boscha, 0 nieznanych ID po kanonizacji tożsamości.
- Dla wskazanej jedenastki: **79 występów w 44 protokołach**. Każde z sześciu pól zgadza się z rozliczeniem historii Boscha, bez wartości nieprzypisanych. [Protokoły i kompletność przeglądu](../data/source-evidence/public-career-protocol-review-20261019.json).
- Bez potwierdzenia zakresu klubowego, pełnego przeglądu Boscha lub zgodnych sum system zachowuje minimum. Nowe mecze poza datą potwierdzenia wymagają ponownego uzgodnienia. Żaden brak danych nie został zastąpiony fikcyjnym zerem.

| Zawodnik | M | G | A | MVP | ŻK | CK bezp. |
|---|---:|---:|---:|---:|---:|---:|
| Bazyluk Jakub | 1 | 0 | 0 | 0 | 1 | 0 |
| Ciborowski Julian | 4 | 0 | 1 | 0 | 0 | 0 |
| Gorbacewicz Emil | 10 | 0 | 3 | 0 | 2 | 0 |
| Gołąbeski Piotr | 13 | 1 | 1 | 1 | 4 | 1 |
| Kossakowski Maciej | 5 | 0 | 0 | 0 | 0 | 0 |
| Kuźma Gabriel | 3 | 0 | 0 | 0 | 0 | 0 |
| Markowski Damian | 6 | 2 | 1 | 0 | 0 | 0 |
| Sołowiej Tomasz | 33 | 22 | 13 | 3 | 1 | 0 |
| Uściłowski Krzysztof | 2 | 0 | 0 | 0 | 0 | 0 |
| Wądołowski Sebastian | 1 | 0 | 0 | 0 | 0 | 0 |
| Śmiłowski Michał | 1 | 0 | 0 | 0 | 0 | 0 |

## Web Archive

Dodatkowo odczytano sześć kopii tabel kariery o potwierdzonym WordPress post ID. Każda kopia pozostaje osobnym historycznym faktem; nie sumujemy kolejnych kopii tej samej kariery. Starsze szablony mają inną kolejność kolumn, dlatego parser używa nazw klas pól. Sprawdzono także 35 bieżących publicznych profili: 0 błędów parsera i 0 różnic względem wersjonowanych surowych bilansów HTML.

| ID | Kopia | M | G | A | MVP | ŻK | CK bezp. |
|---|---|---:|---:|---:|---:|---:|---:|
| 7285 | [20250811043649](https://web.archive.org/web/20250811043649id_/https://podlaskaliga.pl/zawodnik/solowiej-tomasz/) | 32 | 22 | 13 | 3 | 1 | 0 |
| 7282 | [20230607191158](https://web.archive.org/web/20230607191158id_/https://podlaskaliga.pl/zawodnik/markowski-damian/) | 4 | 1 | 1 | 0 | 0 | 0 |
| 7282 | [20240622093014](https://web.archive.org/web/20240622093014id_/https://podlaskaliga.pl/zawodnik/markowski-damian/) | 6 | 2 | 1 | 0 | 0 | 0 |
| 7278 | [20230607132012](https://web.archive.org/web/20230607132012id_/https://podlaskaliga.pl/zawodnik/kossakowski-maciej/) | 5 | 0 | 0 | 0 | 0 | 0 |
| 10604 | [20241009070621](https://web.archive.org/web/20241009070621id_/https://podlaskaliga.pl/zawodnik/smilowski-michal/) | 1 | 0 | 0 | 0 | 0 | 0 |
| 8916 | [20241203144739](https://web.archive.org/web/20241203144739id_/https://podlaskaliga.pl/zawodnik/wadolowski-sebastian/) | 0 | 0 | 0 | 0 | 0 | 0 |

- Sołowiej: HTML 32M; oficjalny baraż 7882 dodaje 1M, razem 33M. Nie nadano mu fikcyjnego sezonu.
- Wądołowski: kopia HTML pomija znany występ Orlik 2024 (10145), więc jej 0 nie zastępuje udokumentowanego 1M.
- „Markowski Damian Jakub” ma inne ID 8500 i nie został połączony z Damianem Markowskim 7282.
- Kolejne zapytania availability dla Ciborowskiego, Bazyluka, Uściłowskiego i Kuźmy otrzymały HTTP 429. Nie jest to dowód braku kopii. [Datowane wyciągi i ograniczenia](../data/source-evidence/archived-career-tables-20261019.json).

## Zakres crawlu publicznego PLP

- **7456 różnych adresów HTML**, w tym HTML wszystkich 2415 wydarzeń odczytanych wcześniej przez API.
- **26 sprawdzonych map XML, 4559 wymienionych adresów; każdy adres sitemap odczytany**.
- HTTP stron HTML: `{'200': 7456}`; kolejka pozostała: **0**, limit nieosiągnięty, 0 obciętych odpowiedzi.
- **168/168 publicznych list SportsPress**: brak tych 11 identyfikatorów. To kontrola identyfikatorów, nie nazw — wiersze API nie zawierają nazwisk. [Audyt kolekcji list](../data/source-evidence/public-career-list-review-20261019.json).
- Lista all-time: 1187 linków do profili, brak dokładnych nazw jedenastki; osoby o podobnych nazwiskach zachowano jako odrębne.
- Odczytano także 25 indeksów tagów/autorów z map XML; nie wniosły nowego nieodczytanego adresu treści. Dalsza paginacja indeksów tagów/autorów/kategorii pozostawała poza enumeracją; adresy treści z ich stron wejściowych były już odczytane. Pominięto również warianty query-string, pliki mediów, kanały feed oraz administrację/logowanie.
- Nowe publiczne profile o jednym z 11 dokładnych post ID: **0**. Same wzmianki w artykułach lub protokołach nie dowodzą istnienia odrębnego profilu.

[Pełny manifest URL, statusów i SHA-256 odpowiedzi](../data/source-evidence/public-career-source-crawl-20261019.json). Publiczny crawl nie obejmuje usuniętych/prywatnych stron ani niedostępnych kopii Web Archive; rekonstrukcja korzysta dodatkowo z jawnego potwierdzenia użytkownika.

## Weryfikacja i publikowane zakresy

207 testów Python, 14 testów frontendowych, generatory i walidacje portalu/XLSX/raportów. Portal oraz XLSX rozdzielają źródło liczb i potwierdzenie zakresu klubowego. Chronione 113 meczów ligowych, 988 występów i 293 gole pozostają bez zmian. Plik XLSX zachowuje 7 arkuszy.
