import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backfill_match_player_stats import backfill_seasons
from integrate_match_protocols import integrate_match_protocols


class GrowingArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        cls.index = json.loads((ROOT / "data/match_protocol_audit_index.json").read_text(encoding="utf-8"))
        cls.box_scores = json.loads((ROOT / "data/match_player_evidence.json").read_text(encoding="utf-8"))

    def test_114th_new_fixture_does_not_invalidate_113_historic_protocols(self):
        fixture = deepcopy(self.db["matches"][0])
        fixture["id"] = "future-new-match"
        fixture["date"] = "2027-01-01"
        fixture["event_link"] = "https://podlaskaliga.pl/wydarzenie/future-bosch-game/"
        fixture["gf"] = 0
        fixture["ga"] = 0
        matches = self.db["matches"] + [fixture]
        audit = integrate_match_protocols(deepcopy(self.db["players"]), deepcopy(matches), self.index)
        self.assertEqual(audit["audited_matches"], 113)

        report = backfill_seasons(deepcopy(self.db["players"]), matches, self.box_scores)
        self.assertEqual(report["verified_matches"], 113)

    def test_less_than_113_source_evidence_is_still_rejected(self):
        with self.assertRaises(ValueError):
            backfill_seasons(self.db["players"], self.db["matches"], {
                "matches": self.box_scores["matches"][:112]
            })


if __name__ == "__main__":
    unittest.main()
