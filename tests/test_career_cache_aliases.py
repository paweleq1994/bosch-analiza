import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sync_public_player_careers import canonicalize_cached_careers


class HistoricalCareerCacheRegressionTests(unittest.TestCase):
    def test_obsolete_synthetic_profile_is_rekeyed_without_losing_its_source(self):
        career = {
            "source_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
            "totals": {"apps": 34, "goals": 11},
        }
        result = canonicalize_cached_careers(
            {"new-kakareko-kamil": career},
            [{"id": "1594", "aliases": ["new-kakareko-kamil"]}],
        )
        self.assertEqual(result, {"1594": career})

    def test_equal_duplicate_cache_entries_are_removed(self):
        career = {
            "source_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
            "totals": {"apps": 34, "goals": 11},
        }
        result = canonicalize_cached_careers(
            {"new-kakareko-kamil": career, "1594": career},
            [{"id": "1594", "aliases": ["new-kakareko-kamil"]}],
        )
        self.assertEqual(list(result), ["1594"])

    def test_conflicting_career_data_is_not_silently_deduplicated(self):
        with self.assertRaises(ValueError):
            canonicalize_cached_careers(
                {
                    "new-kakareko-kamil": {
                        "source_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
                        "totals": {"apps": 34},
                    },
                    "1594": {
                        "source_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
                        "totals": {"apps": 35},
                    },
                },
                [{"id": "1594", "aliases": ["new-kakareko-kamil"]}],
            )


if __name__ == "__main__":
    unittest.main()
