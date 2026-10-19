import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from public_protocol_careers import review_public_protocols, reconstruct_confirmed_bosch_career
from sync_public_player_careers import parse_career_html


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

    def test_only_identity_bound_club_confirmation_lifts_fully_reconciled_minimum(self):
        review = review_public_protocols(self.source)["7270"]
        totals = review["totals"]
        player = {"id": "7270", "name": "Gołąbeski Piotr", **totals, "public_protocol_review": review,
                  "season_coverage": {"by_season": dict(totals), "unassigned": dict.fromkeys(totals, 0)}}
        confirmation = json.loads((ROOT / "data/source-evidence/bosch-only-career-scope-20261019.json").read_text("utf-8"))
        self.assertFalse(reconstruct_confirmed_bosch_career(player, {}))
        self.assertNotIn("career_totals", player)
        wrong_name = copy.deepcopy(confirmation)
        wrong_name["players"]["7270"]["name"] = "Gołąbeski Adam"
        with self.assertRaisesRegex(ValueError, "scope confirmation"):
            reconstruct_confirmed_bosch_career(player, wrong_name)
        for change in ("foreign_team", "unassigned", "inconsistent_sum", "future_match", "incomplete_bosch_archive"):
            broken = copy.deepcopy(player)
            if change == "foreign_team":
                broken["public_protocol_review"]["matches"][0]["team_id"] = "123"
            elif change == "unassigned":
                broken["season_coverage"]["unassigned"]["apps"] = 1
            elif change == "future_match":
                broken["public_protocol_review"]["matches"][0]["date"] = "2027-01-01"
            elif change == "incomplete_bosch_archive":
                broken["public_protocol_review"]["bosch_protocol_coverage_verified"] = False
            else:
                broken["apps"] += 1
            with self.subTest(change=change):
                self.assertFalse(reconstruct_confirmed_bosch_career(broken, confirmation))
                self.assertNotIn("career_totals", broken)
                self.assertIn("reconstruction_pending", broken["public_protocol_review"])
        self.assertTrue(reconstruct_confirmed_bosch_career(player, confirmation))
        self.assertEqual(player["career_totals"]["apps"], 13)
        self.assertTrue(player["career_totals"]["reconstructed"])
        self.assertNotIn("source_url", player["career_totals"])
        self.assertFalse(player["stats_minimum"])

    def test_old_and_new_archive_templates_use_semantic_stat_columns(self):
        before = ["name", "punktacjakanadyjska", "goals", "assists", "pikarzmeczu", "top", "samobje", "appearances", "yellowcards", "redcards", "gpg", "apg"]
        after = ["name", "appearances", "punktacjakanadyjska", "goals", "assists", "pikarzmeczu", "top", "samobje", "yellowcards", "redcards", "gpg", "apg"]
        values = {"appearances": "6", "goals": "2", "assists": "1", "pikarzmeczu": "0", "yellowcards": "0", "redcards": "0"}
        for columns in (before, after):
            def row(label):
                return "<tr>" + "".join(f'<td class="data-{c}">{label if c == "name" else values.get(c, "0")}</td>' for c in columns) + "</tr>"
            html = '<body class="postid-7282"><table class="player-league">' + row("Orlik 2023") + row("Suma") + "</table></body>"
            parsed = parse_career_html(html, "7282")
            self.assertEqual(parsed["totals"], {"apps": 6, "goals": 2, "assists": 1, "motm": 0, "yellow": 0, "red": 0})
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                parse_career_html(html, "8500")
