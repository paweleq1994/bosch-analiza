from threading import Barrier
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sync_public_player_careers import refresh_public_careers


class BoundedFullCareerHTMLTests(unittest.TestCase):
    def test_parallel_requests_preserve_stable_snapshot(self):
        gate = Barrier(2, timeout=3)
        urls = [
            "https://podlaskaliga.pl/zawodnik/moskal-pawel/",
            "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
        ]
        calls = []

        def fetch(url):
            calls.append(url)
            gate.wait()
            return {"totals": {"apps": 139}, "season_rows": []}

        roster = [
            {"id": "1960", "name": "Moskal Paweł", "profile_url": urls[0]},
            {"id": "1594", "name": "Kakareko Kamil", "profile_url": urls[1]},
        ]
        previous = {
            "1960": {
                "totals": {"apps": 139}, "season_rows": [],
                "source_url": urls[0], "captured_at": "2026-01-01T00:00:00Z",
            }
        }
        players, failures = refresh_public_careers(
            roster, previous, get=fetch, workers=2
        )
        self.assertEqual(failures, {})
        self.assertCountEqual(calls, urls)
        self.assertEqual(players["1960"], previous["1960"])
        self.assertEqual(players["1594"]["totals"]["apps"], 139)

    def test_failed_plp_request_retains_previous_source_data(self):
        url = "https://podlaskaliga.pl/zawodnik/moskal-pawel/"
        previous = {
            "1960": {"totals": {"apps": 139}, "source_url": url}
        }

        def unavailable(_):
            raise TimeoutError("Temporarily inaccessible")

        players, failures = refresh_public_careers(
            [{"id": "1960", "name": "Moskal Paweł", "profile_url": url}],
            previous, get=unavailable, workers=2,
        )
        self.assertEqual(players, previous)
        self.assertIn("TimeoutError", failures["1960"])


if __name__ == "__main__":
    unittest.main()
