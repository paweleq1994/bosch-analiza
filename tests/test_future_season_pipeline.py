"""Exercise a new official season through the existing import/build pipeline."""
import json
import sys
import tempfile
import runpy
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_portal
import sync_plp
from collect_match_player_evidence import collect_matches
from sync_new_goal_protocols import extend


class FutureSeasonPipelineTests(unittest.TestCase):
    def validate_portal(self, db):
        with patch.object(Path, "read_text", return_value=json.dumps(db)):
            runpy.run_path(str(ROOT / "src/validate_portal.py"))

    def setUp(self):
        self.read = build_portal.load
        self.database = json.loads((ROOT / "docs/assets/data.json").read_text(encoding="utf-8"))
        self.profiles = self.read("player_profile_map.json")
        self.index = self.read("match_protocol_audit_index.json")
        self.event = {
            "id": 20001, "date": "2027-04-15T18:00:00",
            "link": "https://podlaskaliga.pl/wydarzenie/bosch-future-rival/",
            "title": {"rendered": "Bosch Service Tech-Car vs Nowy Rywal"},
            "teams": [6951, 3], "leagues": [510], "seasons": [170],
            "results": {"6951": {"goals": "2", "firsthalf": "1"},
                        "3": {"goals": "1", "firsthalf": "0"}},
            "performance": {
                "6951": {"1960": {"status": "lineup", "goals": "2 (3', 23')",
                                    "assists": "0", "pikarzmeczu": "1",
                                    "yellowcards": "1", "redcards": "0"}},
                "3": {"15000": {"goals": "1 (28')"}},
            },
        }
        self.tables = [{"id": 20002, "title": {"rendered": "I Liga – Orlik 2027"},
                        "slug": "i-liga-orlik-2027", "leagues": [510], "seasons": [170],
                        "data": {"6951": {"pos": "1", "pkt": "3", "m": "1", "w": "1",
                                          "r": "0", "p": "0", "g": "2", "s": "1"}}}]

    def import_new_season(self):
        previous = self.read("league_updates.json")
        with patch.object(sync_plp, "date_today", return_value="2027-04-16"):
            payload, valid, errors = sync_plp.synchronize(
                {"seasons": [170]}, lambda _: self.tables, lambda _: [self.event],
                previous, self.database["seasons"], self.database["matches"], self.profiles,
            )
        self.assertFalse(errors)
        self.assertEqual(len(valid), 1)
        fixture = next(m for m in payload["matches"] if m["id"] == "20001")
        return payload, fixture

    def build(self, replacements):
        def load(name, default=None):
            return deepcopy(replacements[name] if name in replacements else self.read(name, default))

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.json"
            with patch.object(build_portal, "load", side_effect=load), patch.object(build_portal, "OUTPUT", target):
                build_portal.main()
            return json.loads(target.read_text(encoding="utf-8"))

    def test_new_season_reaches_protocols_player_history_and_portal_without_archive_loss(self):
        league, fixture = self.import_new_season()
        new_evidence, errors = collect_matches([fixture], self.index, fetch=lambda _: self.event)
        self.assertFalse(errors)
        index, pending = extend(self.index, [fixture], self.profiles, fetch=lambda _: self.event)
        self.assertFalse(pending["pending"])
        self.assertEqual(index["matches"][:113], self.index["matches"])
        evidence = self.read("match_player_evidence.json")
        evidence["matches"].extend(new_evidence["matches"])
        db = self.build({"league_updates.json": league, "match_protocol_audit_index.json": index,
                         "match_player_evidence.json": evidence})
        self.assertEqual(len(db["seasons"]), 9)
        self.assertEqual(len(db["matches"]), 114)
        self.assertEqual(db["seasons"][-1]["id"], "170")
        self.assertEqual(db["seasons"][-1]["league_ids"], ["510"])
        match = next(m for m in db["matches"] if m["id"] == "20001")
        self.assertTrue(match["goal_protocol"]["verified"])
        self.assertEqual(match["halftime"], "1:0")
        stats = next(p for p in db["players"] if p["id"] == "1960")["season_stats"]["170"]
        self.assertEqual((stats["apps"], stats["goals"], stats["assists"], stats["motm"], stats["yellow"]), (1, 2, 0, 1, 1))
        for old in self.database["matches"]:
            new = next(m for m in db["matches"] if m["id"] == old["id"])
            self.assertEqual(new["goal_protocol"], old["goal_protocol"])
        repeated, _, _ = sync_plp.synchronize(
            {"seasons": []}, lambda _: [], lambda _: [], league, db["seasons"], db["matches"], self.profiles,
        )
        self.assertEqual(repeated, league)

    def test_later_indoor_season_is_latest_even_when_source_rows_arrive_first(self):
        league, fixture = self.import_new_season()
        indoor = {**league["season_rows"][-1], "id": "171", "plp_id": "171", "name": "Hala 2027/2028",
                  "points": 1, "wins": 0, "draws": 1, "losses": 0, "gf": 0, "ga": 0}
        league["season_rows"].insert(0, indoor)
        league["matches"].append({**fixture, "id": "20003", "event_id": "20003", "sid": "171",
                                  "date": "2027-11-01", "season": indoor["name"], "gf": 0, "ga": 0})
        db = self.build({"league_updates.json": league})
        self.assertEqual(db["seasons"][-1]["id"], "171")

    def test_new_season_preserves_older_partial_player_balance_and_aliases(self):
        self.event["performance"]["6951"]["7271"] = self.event["performance"]["6951"].pop("1960")
        league, fixture = self.import_new_season()
        evidence = self.read("match_player_evidence.json")
        added, _ = collect_matches([fixture], self.index, fetch=lambda _: self.event)
        evidence["matches"].extend(added["matches"])
        index, pending = extend(self.index, [fixture], self.profiles, fetch=lambda _: self.event)
        # Private identity is already proven by the source-linked resolver.
        if pending["pending"]:
            profiles = {**self.profiles, "7271": {"resolved_name": "Gorbacewicz Emil"}}
            index, pending = extend(self.index, [fixture], profiles, fetch=lambda _: self.event)
        db = self.build({"league_updates.json": league, "match_player_evidence.json": evidence,
                         "match_protocol_audit_index.json": index})
        player = next(p for p in db["players"] if p["id"] == "7271")
        old = next(p for p in self.database["players"] if p["id"] == "7271")
        self.assertEqual(player["apps"], old["apps"] + 1)
        self.assertEqual(player["goals"], old["goals"] + 2)
        self.assertIsNone(player["bosch_totals"])
        self.assertTrue(player["stats_minimum"])
        kakareko = next(p for p in db["players"] if p["id"] == "1594")
        self.assertIn("new-kakareko-kamil", kakareko["aliases"])

    def test_publication_validator_accepts_a_historic_player_in_a_new_season(self):
        self.event["performance"]["6951"]["7275"] = self.event["performance"]["6951"].pop("1960")
        league, fixture = self.import_new_season()
        evidence = self.read("match_player_evidence.json")
        added, _ = collect_matches([fixture], self.index, fetch=lambda _: self.event)
        evidence["matches"].extend(added["matches"])
        index, pending = extend(self.index, [fixture], self.profiles, fetch=lambda _: self.event)
        self.assertFalse(pending["pending"])
        db = self.build({"league_updates.json": league, "match_player_evidence.json": evidence,
                         "match_protocol_audit_index.json": index})
        self.validate_portal(db)

    def test_publication_validator_accepts_next_match_without_requiring_its_video(self):
        db = deepcopy(self.database)
        match = deepcopy(db["matches"][-1])
        match.update(id="orlik26-16", date="2026-10-24", opponent="Nowy rywal", gf=0, ga=0, videos=[])
        match.pop("goal_protocol", None)
        match.pop("protocol", None)
        db["matches"].append(match)
        season = next(s for s in db["seasons"] if s["id"] == "orlik-2026")
        season["matches"] += 1
        season["points"] += 1
        season["draws"] += 1
        coverage = next(r for r in db["analysis"]["player_goal_coverage"] if r["sid"] == "orlik-2026")
        coverage["pending_match_count"] = 1
        coverage["pending_match_ids"] = ["orlik26-16"]
        self.validate_portal(db)

    def test_publication_validator_still_rejects_lost_historical_player_balance(self):
        db = deepcopy(self.database)
        player = next(p for p in db["players"] if p["id"] == "7275")
        player["apps"] = 68
        with self.assertRaisesRegex(AssertionError, "Historical PLP Supercup"):
            self.validate_portal(db)

    def test_future_unknown_player_is_reported_and_goal_protocol_remains_pending(self):
        self.event["performance"]["6951"]["99999"] = self.event["performance"]["6951"].pop("1960")
        league, fixture = self.import_new_season()
        index, pending = extend(self.index, [fixture], self.profiles, fetch=lambda _: self.event)
        self.assertEqual(index, self.index)
        self.assertIn("Unknown official goal scorer ID 99999", pending["pending"][0]["reason"])
        evidence = self.read("match_player_evidence.json")
        added, _ = collect_matches([fixture], self.index, fetch=lambda _: self.event)
        evidence["matches"].extend(added["matches"])
        db = self.build({"league_updates.json": league, "match_player_evidence.json": evidence})
        self.assertIn("99999", db["analysis"]["match_player_backfill"]["unmatched_player_ids"])
        self.assertNotIn("99999", {p["id"] for p in db["players"]})
        self.assertFalse(next(m for m in db["matches"] if m["id"] == "20001").get("goal_protocol", {}).get("verified", False))
        coverage = next(r for r in db["analysis"]["player_goal_coverage"] if r["sid"] == "170")
        self.assertEqual(coverage["pending_match_goals"], 2)

    def test_added_match_in_existing_season_keeps_partial_older_totals(self):
        league, fixture = self.import_new_season()
        league["season_rows"] = [s for s in league["season_rows"] if s["id"] != "170"]
        season = next(s for s in league["season_rows"] if s["id"] == "125")
        for field, value in (("matches", 1), ("wins", 1), ("points", 3), ("gf", 2), ("ga", 1)):
            season[field] += value
        fixture.update(sid="125", plp_season_id="125", season=season["name"], date="2023-10-28")
        self.event["date"] = "2023-10-28T18:00:00"
        self.event["performance"]["6951"]["7271"] = self.event["performance"]["6951"].pop("1960")
        league["player_seasons"] = [r for r in league["player_seasons"] if r["sid"] != "170"]
        stats = next(r for r in league["player_seasons"] if r["sid"] == "125" and r["id"] == "7271")
        stats.update(apps=stats["apps"] + 1, goals=stats["goals"] + 2,
                     motm=stats["motm"] + 1, yellow=stats["yellow"] + 1)
        evidence = self.read("match_player_evidence.json")
        added, _ = collect_matches([fixture], self.index, fetch=lambda _: self.event)
        evidence["matches"].extend(added["matches"])
        profiles = {**self.profiles, "7271": {"resolved_name": "Gorbacewicz Emil"}}
        index, pending = extend(self.index, [fixture], profiles, fetch=lambda _: self.event)
        self.assertFalse(pending["pending"])
        db = self.build({"league_updates.json": league, "match_player_evidence.json": evidence,
                         "match_protocol_audit_index.json": index})
        player = next(p for p in db["players"] if p["id"] == "7271")
        self.assertEqual((player["apps"], player["goals"]), (11, 2))
        self.assertIsNone(player["bosch_totals"])


if __name__ == "__main__":
    unittest.main()
