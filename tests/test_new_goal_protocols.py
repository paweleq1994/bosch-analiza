import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sync_new_goal_protocols import verified_protocol, extend, extend_own_goal_evidence


class FuturePLPGoalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.official_history = json.loads(
            (ROOT / "data/match_protocol_audit_index.json").read_text(encoding="utf-8")
        )

    def setUp(self):
        self.fixture = {
            "id": "16555",
            "event_id": "16555",
            "sid": "future-league",
            "date": "2027-04-15",
            "opponent": "Nowy Rywal",
            "gf": 2,
            "ga": 1,
            "event_link": "https://podlaskaliga.pl/wydarzenie/new-bosch-rival/",
        }
        self.source = {
            "id": 16555,
            "date": "2027-04-15T18:00:00",
            "link": self.fixture["event_link"],
            "teams": [6951, 3],
            "results": {"6951": {"goals": 2}, "3": {"goals": 1}},
            "performance": {
                "6951": {"1594": {
                    "goals": "2 (3', 23')",
                    "samobje": "",
                }},
                "3": {"15000": {"goals": "1 (28')", "samobje": ""}},
            },
        }
        self.roster = {
            "1594": {
                "resolved_name": "Kakareko Kamil",
                "profile_url": "https://podlaskaliga.pl/zawodnik/kamil-kakarenko/",
            }
        }

    def test_new_goal_protocol_is_sourced_and_exactly_reconciled(self):
        protocol = verified_protocol(self.fixture, self.source, self.roster)
        self.assertEqual(protocol["official_team_goals"], 2)
        self.assertEqual(protocol["protocol_player_goals"], 2)
        self.assertEqual(protocol["scorers"][0]["goal_minutes"], ["3", "23"])
        self.assertEqual(protocol["scorers"][0]["player_id"], "1594")
        self.assertEqual(protocol["unreadable_goal_markers"], 0)
        self.assertEqual(protocol["audit_origin"], "plp_event_api_verified")

    def test_new_fixture_is_appended_without_changing_113_verified_records(self):
        updated, audit = extend(
            self.official_history,
            [self.fixture],
            self.roster,
            fetch=lambda _: self.source,
        )
        self.assertEqual(len(updated["matches"]), 114)
        self.assertEqual(updated["matches"][:113], self.official_history["matches"])
        self.assertEqual(audit["newly_verified_match_ids"], ["16555"])
        self.assertEqual(audit["pending"], [])

    def test_unconfirmed_minute_is_pending_and_does_not_corrupt_archive(self):
        self.source["performance"]["6951"]["1594"]["goals"] = "2"
        updated, audit = extend(
            self.official_history,
            [self.fixture],
            self.roster,
            fetch=lambda _: self.source,
        )
        self.assertEqual(updated["matches"], self.official_history["matches"])
        self.assertEqual(len(audit["pending"]), 1)
        self.assertIn("Missing official scoring minutes", audit["pending"][0]["reason"])

    def test_unknown_player_identity_is_pending_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "Unknown official goal scorer"):
            verified_protocol(self.fixture, self.source, {})

    def test_score_mismatch_is_never_recorded_as_a_goal(self):
        self.source["results"]["6951"]["goals"] = 3
        with self.assertRaisesRegex(ValueError, "Official score"):
            verified_protocol(self.fixture, self.source, self.roster)

    def own_goal(self):
        self.source["performance"]["6951"]["1594"]["samobje"] = "1 (28')"
        self.source["performance"]["3"]["15000"]["goals"] = "0"

    def test_known_own_goal_with_minutes_is_verified_and_published_idempotently(self):
        self.own_goal()
        protocol = verified_protocol(self.fixture, self.source, self.roster)
        self.assertEqual(protocol["bosch_own_goals"], 1)
        self.assertEqual(protocol["protocol_player_goals"], 2)
        previous = {"events": [{"match_id": "7839", "player_id": "1960", "goals": 1}]}
        updated = extend_own_goal_evidence(previous, {"matches": [protocol]})
        self.assertEqual(updated["events"][:1], previous["events"])
        self.assertEqual(updated["events"][-1]["minutes"], ["28"])
        self.assertEqual(updated["events"][-1]["source_url"], self.fixture["event_link"])
        self.assertEqual(extend_own_goal_evidence(updated, {"matches": [protocol]}), updated)

    def test_unknown_own_goal_scorer_remains_pending(self):
        self.own_goal()
        self.source["performance"]["6951"]["99999"] = {"samobje": "1 (29')"}
        _, audit = extend(self.official_history, [self.fixture], self.roster, lambda _: self.source)
        self.assertIn("Unknown official own-goal scorer ID 99999", audit["pending"][0]["reason"])

    def test_own_goal_without_minutes_remains_pending(self):
        self.own_goal()
        self.source["performance"]["6951"]["1594"]["samobje"] = "1"
        with self.assertRaisesRegex(ValueError, "Missing official own-goal minutes"):
            verified_protocol(self.fixture, self.source, self.roster)

    def test_inconsistent_conceded_score_does_not_validate_own_goal(self):
        self.own_goal()
        self.source["performance"]["3"]["15000"]["goals"] = "1 (28')"
        with self.assertRaisesRegex(ValueError, "Conceded goals do not reconcile"):
            verified_protocol(self.fixture, self.source, self.roster)


if __name__ == "__main__":
    unittest.main()
