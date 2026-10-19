import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from integrate_verified_match_players import (
    attach_verified_identities,
    minimum_match_totals,
)

EXPECTED = {
    "1594": "Kakareko Kamil",
    "2203": "Bayer Emilian",
    "7223": "Grabowski Jakub (GK)",
    "7266": "Bazyluk Jakub",
    "7286": "Uściłowski Krzysztof",
    "8655": "Kuźma Gabriel",
    "8916": "Wądołowski Sebastian",
    "10321": "Ciborowski Julian",
    "10603": "Roszkowski Patryk",
    "10604": "Śmiłowski Michał",
    "11895": "Czudzinowicz Jakub (GK)",
    "12285": "Rollauer Patryk",
    "13194": "Karpowicz Kamil",
}


class VerifiedIdentityIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(
            (ROOT / "data/match_player_identities.json").read_text(encoding="utf-8")
        )
        cls.event_source = json.loads(
            (ROOT / "data/match_player_evidence.json").read_text(encoding="utf-8")
        )

    def test_all_originally_unmapped_players_have_source_provenance(self):
        for player_id, name in EXPECTED.items():
            with self.subTest(player_id=player_id):
                record = self.source["players"].get(player_id)
                self.assertIsNotNone(record)
                self.assertEqual(record["name"], name)
                self.assertTrue(record["verified"])
                self.assertTrue(record["evidence_urls"])
                self.assertTrue(all(
                    url.startswith("https://podlaskaliga.pl/wydarzenie/")
                    for url in record["evidence_urls"]
                ))

    def test_synthetic_kakareko_is_promoted_without_duplicate(self):
        players = [{"id": "new-kakareko-kamil", "name": "Kakareko Kamil",
                    "orlik2026": {"apps": 6, "goals": 2}}]
        audit = attach_verified_identities(players, self.source, self.event_source)
        names = [p for p in players if p["name"] == "Kakareko Kamil"]
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0]["id"], "1594")
        self.assertIn("new-kakareko-kamil", names[0]["aliases"])
        self.assertEqual(names[0]["orlik2026"]["apps"], 6)
        self.assertIn(
            {"old_id": "new-kakareko-kamil", "id": "1594"},
            audit["promoted_aliases"],
        )

    def test_new_players_are_not_treated_as_zero_before_match_aggregation(self):
        players = []
        audit = attach_verified_identities(players, self.source, self.event_source)
        self.assertGreaterEqual(len(audit["created_ids"]), 13)
        newcomer = next(p for p in players if p["id"] == "10321")
        self.assertIsNone(newcomer["apps"])
        self.assertTrue(newcomer["stats_minimum"])
        minimum_match_totals(players, self.event_source)
        self.assertEqual(newcomer["apps"], 4)
        self.assertEqual(newcomer["assists"], 1)

    def test_complete_generated_portal_has_one_profile_per_verified_identity(self):
        from build_portal import main
        main()
        database = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )
        roster = {str(player["id"]): player for player in database["players"]}
        for player_id, name in EXPECTED.items():
            with self.subTest(player_id=player_id):
                self.assertIn(player_id, roster)
                self.assertEqual(roster[player_id]["name"], name)
                self.assertTrue(roster[player_id].get("verified_identity_source"))
        self.assertNotIn("new-kakareko-kamil", roster)
        self.assertIn("new-kakareko-kamil", roster["1594"]["aliases"])
        self.assertEqual(
            database["analysis"]["match_player_backfill"]["unmatched_player_ids"],
            [],
        )
        self.assertEqual(
            sum(x["unattributed_goals"]
                for x in database["analysis"]["player_goal_coverage"]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
