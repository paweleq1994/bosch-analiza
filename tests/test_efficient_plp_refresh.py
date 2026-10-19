import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sync_player_seasons import refresh_both


class EfficientPLPProfileRefreshTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fetch(player_id):
            self.calls.append(player_id)
            if player_id == "99999":
                raise TimeoutError("Source unavailable")
            return {
                "statistics": {
                    "league": {
                        "120": {
                            "team": '<a href="https://podlaskaliga.pl/druzyna/bosch-service-tech-car/">Bosch</a>',
                            "name": "Hala 2022",
                            "appearances": "5",
                            "goals": "2",
                            "assists": "1",
                            "pikarzmeczu": "0",
                            "yellowcards": "0",
                            "redcards": "0",
                        }
                    }
                }
            }

        self.fetch = fetch

    def test_profiles_are_fetched_only_once_for_both_statistics_sources(self):
        seasons, careers, warnings = refresh_both(
            ["1960", "1594"], {}, {}, fetch=self.fetch, workers=2
        )
        self.assertCountEqual(self.calls, ["1960", "1594"])
        self.assertEqual(seasons["1960"]["120"]["apps"], 5)
        self.assertEqual(careers["1960"]["apps"], 5)
        self.assertEqual(careers["1594"]["goals"], 2)
        self.assertEqual(warnings, [])

    def test_api_failure_preserves_previous_snapshot_and_is_reported(self):
        historical = {"99999": {"120": {"apps": 3}}}
        careers = {"99999": {"apps": 7}}
        results, saved, warnings = refresh_both(
            ["99999"], historical, careers, fetch=self.fetch, workers=1
        )
        self.assertEqual(results, historical)
        self.assertEqual(saved, careers)
        self.assertEqual(len(warnings), 1)
        self.assertIn("TimeoutError", warnings[0])


if __name__ == "__main__":
    unittest.main()
