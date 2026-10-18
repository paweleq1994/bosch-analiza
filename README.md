# Bosch Service Tech-Car — Kompendium

W pełni statyczny serwis drużyny z historią spotkań PLP, sezonami, zawodnikami, profilami, head-to-head, analizą, rekordami i nagraniami YouTube.

**Strona:** https://paweleq1994.github.io/bosch-analiza/

## Co jest dostępne

- Start — najnowszy sezon, forma i liderzy.
- Sezony — osiem sezonów w tym Orlik 2026, podsumowania, statystyki i wyniki.
- Mecze — 113 ligowych spotkań ze szczegółami i przypisanymi nagraniami.
- Zawodnicy — profile, dostępne statystyki sezonowe oraz archiwum występów.
- Rywale — bezpośrednie bilanse i historia spotkań.
- Analizy — PPG, skuteczność, defensywa, benchmarking awansu, przedsezonowy scouting.
- Wideo — 79 nagrań z archiwum i dalsza synchronizacja znanych kanałów.
- Rekordy — najlepsze wyniki i historyczne osiągnięcia.
- Wyszukiwarka i ciemny/jasny motyw.

Stara, obszerna strona zachowana jest w [docs/archive.html](docs/archive.html). Raport szczegółowy Orlika 2026: [docs/orlik-2026.html](docs/orlik-2026.html).

## Architektura i koszt

Statyczna strona HTML/CSS/JS publikowana przez GitHub Pages z folderu `docs/`. Dane powstają z wersjonowanych źródeł JSON. Nie ma backendu, płatnego hostingu ani konieczności posiadania klucza YouTube API. Workflow GitHub Actions może codziennie odczytywać PLP i Atom/RSS YouTube z listy znanych kanałów.

## Generowanie lokalnie

```bash
python src/build_portal.py
python src/validate_portal.py
```

## Synchronizacja automatyczna

Workflow [sync.yml](.github/workflows/sync.yml) działa codziennie i jest dostępny do ręcznego uruchomienia w zakładce Actions. Synchronizuje PLP i znane kanały YouTube, przelicza portal, waliduje i publikuje zmiany poprzez commit do gałęzi głównej.

```bash
python src/sync_plp.py
python src/sync_videos.py
python src/build_portal.py
python src/validate_portal.py
```

Kanały w `data/video_channels.json` można definiować po trwałym `channel_id` albo `handle`. Preferowany jest trwały identyfikator. Znane kanały: `@martawnuszynska9993` i `@piotrgoabeski3337`. Jeśli źródło jest niedostępne, skrypt zostawia poprzednie dane; problem jest zgłaszany w logu. Materiały nie są pobierane jako pliki — używane są linki YouTube.

Aby ręcznie przypisać film, dopisz jego ID do `data/video_updates.json` w sekcji `manual_bindings`, np.:

```json
{
  "videos": [],
  "manual_bindings": {
    "hcfb9Ttmswo": { "match_id": "7814", "segment": "mecz" }
  }
}
```

Zmiany w `manual_bindings` mają pierwszeństwo nad automatyką. Po zmianach uruchom generator (lub workflow).

## Jakość danych

Archiwalne dane pochodzą z marca 2026, a sezon Orlik 2026 z października 2026. Dane z marca nie są przedstawiane jako sumy uwzględniające Orlik 2026. Lista liderów Orlika 2026 nie jest pełną kadrą; brakujące statystyki są oznaczane jako nieznane, zamiast zerowane. Historyczne dane o partnerstwach i przebiegu spotkań pozostają w archiwalnej wersji strony.

Automatyczna synchronizacja PLP obsługuje nowe sezony tylko wtedy, gdy liczba meczów oraz bramki zgadzają się z oficjalną tabelą, aby nie publikować błędów. Synchronizacja YouTube wykorzystuje tytuły z rywalem i wynikiem do jednoznacznych przypisań; pozostałe filmy trafiają do weryfikacji.

## Struktura

- `src/build_portal.py` — generator źródła danych dla nowego portalu.
- `src/sync_plp.py` — konserwatywny import danych nowych sezonów.
- `src/sync_videos.py` — codzienny odczyt RSS/Atom wybranych kanałów.
- `src/validate_portal.py` — kontrola spójności wyników.
- `docs/index.html`, `docs/assets/app.js`, `docs/assets/style.css` — nowy frontend.
- `docs/assets/data.json` — wygenerowana baza statyczna.
- `docs/archive.html` — pełna dotychczasowa strona analityczna.
- `data/*` — źródła i historyczne dane.
