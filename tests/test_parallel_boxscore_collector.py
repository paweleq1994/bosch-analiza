from threading import Barrier
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collect_match_player_evidence import collect_matches


class ParallelVerifiedMatchCollectorTests(unittest.TestCase):
    def test_fetches_in_parallel_while_preserving_deterministic_fixture_order(self):
        matches = [
            {
                "id": value,
                "event_id": value,
                "sid": "120",
                "date": date,
                "event_link": f"https://podlaskaliga.pl/wydarzenie/test-{value}/",
            }
            for value, date in [("101", "2022-11-02"), ("100", "2022-11-01")]
        ]
        meet = Barrier(2, timeout=3)
        calls = []

        def fetch(event_id):
            calls.append(event_id)
            meet.wait()
            match = next(item for item in matches if item["event_id"] == event_id)
            return {
                "id": int(event_id), "date": match["date"] + "T12:00:00",
                "link": match["event_link"], "teams": [6951, 73],
                "performance": {
                    "6951": {"1594": {"status": "lineup", "assists": "1"}},
                },
            }

        collected, errors = collect_matches(
            matches, {"matches": []}, fetch=fetch, workers=2,
        )
        self.assertEqual(errors, [])
        self.assertCountEqual(calls, ["100", "101"])
        self.assertEqual(
            [record["match_id"] for record in collected["matches"]],
            ["100", "101"],
        )

    def test_unavailable_new_event_preserves_other_sources(self):
        matches = [
            {
                "id": value,
                "event_id": value,
                "sid": "120",
                "date": "2022-11-01",
                "event_link": f"https://podlaskaliga.pl/wydarzenie/test-{value}/",
            }
            for value in ("100", "101")
        ]

        def fetch(event_id):
            if event_id == "101":
                raise TimeoutError("Public PLP unavailable")
            return {
                "id": 100, "date": "2022-11-01",
                "link": matches[0]["event_link"], "teams": [6951, 73],
                "performance": {"6951": {"1594": {"status": "lineup"}}},
            }

        collected, errors = collect_matches(
            matches, {"matches": []}, fetch=fetch, workers=2,
        )
        self.assertEqual(
            [record["match_id"] for record in collected["matches"]], ["100"]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("101: TimeoutError", errors[0])


if __name__ == "__main__":
    unittest.main()
