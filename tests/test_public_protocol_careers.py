import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from public_protocol_careers import review_public_protocols


class PublicProtocolCareerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT / "data/source-evidence/public-career-protocol-review-20261019.json").read_text(encoding="utf-8"))

    def test_untagged_game_explains_golabeskis_remaining_appearance_and_yellow(self):
        rows = review_public_protocols(self.source)
        self.assertEqual(len(rows), 11)
        player = rows["7270"]
        self.assertEqual(player["totals"], {"apps": 13, "goals": 1, "assists": 1, "motm": 1, "yellow": 4, "red": 1})
        self.assertFalse(player["whole_career_verified"])
        game = next(g for g in player["matches"] if g["event_id"] == "10050")
        self.assertEqual(game["season_ids"], [])
        self.assertEqual((game["apps"], game["yellow"]), (1, 1))
        self.assertEqual(rows["7285"]["bosch_totals"]["apps"], 33)

    def test_incomplete_archive_wrong_team_and_duplicate_are_rejected(self):
        incomplete = copy.deepcopy(self.source)
        incomplete["unique_event_ids"] -= 1
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            review_public_protocols(incomplete)
        wrong = copy.deepcopy(self.source)
        wrong["records"][0]["teams"] = [999]
        with self.assertRaisesRegex(ValueError, "team mismatch"):
            review_public_protocols(wrong)
        duplicate = copy.deepcopy(self.source)
        duplicate["records"].append(duplicate["records"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            review_public_protocols(duplicate)
        both = copy.deepcopy(self.source)
        event = both["records"][0]
        team, stats = next(iter(event["performance"].items()))
        other = next(str(t) for t in event["teams"] if str(t) != team)
        event["performance"][other] = copy.deepcopy(stats)
        with self.assertRaisesRegex(ValueError, "both teams"):
            review_public_protocols(both)
