import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_portal
from reconcile_player_history import apply_archived_seasons, archived_bosch_seasons, breakdown_coverage


class ArchivedPlayerSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_portal.main()
        database = json.loads((ROOT / "docs" / "assets" / "data.json").read_text(encoding="utf-8"))
        cls.players = {str(player["id"]): player for player in database["players"]}
        cls.audit = {str(row["sid"]): row for row in database["analysis"]["player_goal_coverage"]}

    def season(self, player_id, season_id):
        player = self.players[str(player_id)]
        return next(record for record in player["season_history"] if str(record["sid"]) == str(season_id))

    def test_golab_eski_archived_goals_appear_in_season_and_career_summary(self):
        player = self.players["7270"]
        season = self.season("7270", "139")

        self.assertEqual(player["name"], "Gołąbeski Piotr")
        self.assertEqual((player["apps"], player["goals"], player["assists"]), (13, 1, 1))
        self.assertEqual((season["goals"], season["assists"]), (1, 1))
        self.assertEqual(season["apps"], 6)
        self.assertEqual(season["origin"], "archived_peak")
        self.assertIsNone(self.season("7270", "120")["goals"])
        self.assertEqual(player["season_coverage"]["unassigned"]["apps"], 2)
        self.assertEqual(player["season_coverage"]["unassigned"]["goals"], 0)

    def test_recovers_four_full_archive_players_without_rest_access(self):
        expected = {
            "7285": (11, 10, 3),
            "7282": (3, 1, 1),
            "7271": (6, 0, 2),
            "7278": (2, 0, 0),
        }

        for player_id, totals in expected.items():
            with self.subTest(player_id=player_id):
                season = self.season(player_id, "125")

                self.assertEqual(
                    (season["apps"], season["goals"], season["assists"]),
                    totals,
                )
                self.assertEqual(season["origin"], "plp_archived_season")

        hala = self.season("7285", "120")
        self.assertEqual((hala["goals"], hala["assists"]), (10, 7))
        self.assertEqual(hala["apps"], 13)
        self.assertEqual(hala["origin"], "archived_peak")

    def test_unassigned_totals_are_not_invented_as_specific_season_stats(self):
        player = self.players["7285"]
        self.assertEqual((player["apps"], player["goals"], player["assists"]), (32, 22, 13))
        self.assertEqual(player["season_coverage"]["unassigned"]["goals"], 0)
        self.assertEqual(player["season_coverage"]["unassigned"]["assists"], 0)

        unknown = self.season("7285", "139")
        self.assertEqual(unknown["apps"], 7)
        self.assertEqual(unknown["goals"], 2)
        self.assertEqual(unknown["assists"], 3)

    def test_sports_press_verification_still_takes_priority(self):
        moskal = self.season("1960", "125")
        self.assertEqual((moskal["apps"], moskal["goals"], moskal["assists"]), (14, 3, 5))
        self.assertEqual(self.players["1960"]["season_coverage"]["unassigned"]["goals"], 0)
        self.assertEqual(self.players["7275"]["goals"], 30)

    def test_recovered_goals_reduce_unattributed_scoring_without_duplication(self):
        self.assertEqual(self.audit["120"]["unattributed_goals"], 0)
        self.assertEqual(self.audit["125"]["unattributed_goals"], 0)
        self.assertEqual(self.audit["139"]["unattributed_goals"], 0)
        self.assertEqual(sum(row["unattributed_goals"] for row in self.audit.values()), 0)
        self.assertEqual(sum(row["administrative_goals"] for row in self.audit.values()), 1)
        self.assertEqual(sum(row["opponent_own_goals"] for row in self.audit.values()), 3)

    def test_every_player_has_reconcilable_season_coverage(self):
        for player in self.players.values():
            with self.subTest(name=player["name"]):
                seasonal_rows = player["season_history"]
                coverage = player["season_coverage"]

                for field in ("apps", "goals", "assists", "motm"):
                    known = sum(
                        row[field]
                        for row in seasonal_rows
                        if type(row.get(field)) is int
                    )

                    self.assertEqual(coverage["by_season"][field], known)

                    if type(player.get(field)) is int:
                        self.assertEqual(
                            known + coverage["unassigned"][field],
                            player[field],
                        )

    def test_rejects_wrong_team_and_preserves_more_authoritative_stats(self):
        wrong_team = {
            "player_rows": [
                {
                    "player_id": 7270,
                    "sid": 139,
                    "team_id": 999,
                    "team_name": "Inna drużyna",
                    "apps": 14,
                    "goals": 40,
                    "assists": 10,
                }
            ]
        }
        self.assertEqual(archived_bosch_seasons(wrong_team, {"7270"}), {})

        player = {
            "id": "7270",
            "peak": "Orlik 2024: 1G + 1A",
            "goals": 1,
            "assists": 1,
            "apps": 13,
            "season_stats": {"139": {"apps": 7, "goals": 0, "assists": 0}},
        }
        apply_archived_seasons(player, {}, [{"id": "139", "name": "Orlik 2024"}])
        self.assertEqual(player["season_stats"]["139"]["goals"], 0)

    def test_archive_coverage_keeps_unknowns_distinct_from_zero(self):
        player = {
            "id": "100",
            "apps": 6,
            "goals": 1,
            "assists": 1,
            "motm": 0,
            "yellow": 0,
            "red": 0,
            "season_history": [
                {
                    "sid": "120",
                    "name": "Hala 2022",
                    "apps": None,
                    "goals": None,
                    "assists": None,
                },
            ],
        }
        coverage = breakdown_coverage(player)
        self.assertEqual(coverage["unassigned"]["apps"], 6)
        self.assertEqual(coverage["unassigned"]["goals"], 1)
        self.assertTrue(coverage["partial"])


if __name__ == "__main__":
    unittest.main()
