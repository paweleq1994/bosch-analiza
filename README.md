# Kompendium Wiedzy o Bosch Service Tech-Car

Interaktywny serwis statyczny zbudowany z danych Podlaskiej Ligi Piłkarskiej i publicznego materiału wideo.

## Start po klonie

```powershell
cd bosch-analiza
```

## Struktura repo

- `src/build_site.py` - generator strony
- `data/bosch_service_tech_car_data_v3.json` - główna baza raportowa
- `data/bosch_service_tech_car_video_library_v3.json` - baza materiałów wideo
- `docs/index.html` - gotowa strona pod GitHub Pages

## Jak przebudować stronę

```powershell
python src/build_site.py
```

Po przebudowie aktualna wersja strony zapisuje się do `docs/index.html`.

## GitHub Pages

1. Wrzuć to repo na GitHub.
2. W `Settings -> Pages` ustaw publikację z gałęzi `main`.
3. Wybierz folder `/docs`.
4. Po każdym update danych uruchom `python src/build_site.py`, a potem zacommituj zmienione `data/`, `src/` i `docs/index.html`.

## Co rozwijać dalej

- aktualizacja danych w `data/`
- poprawki szablonu i logiki w `src/build_site.py`
- publikacja gotowej wersji przez `docs/index.html`
