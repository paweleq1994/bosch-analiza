import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import export_workbook

from export_workbook import COLUMNS, build_workbook


class ExcelExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads(
            (ROOT / "docs/assets/data.json").read_text(encoding="utf-8")
        )
        cls.workbook = build_workbook(cls.db)

    def test_all_raw_sources_and_stat_sheets_are_present(self):
        expected = {"Informacje", *COLUMNS}
        self.assertEqual(set(self.workbook.sheetnames), expected)
        self.assertEqual(
            self.workbook["Zawodnicy"].max_row - 1,
            len(self.db["players"]),
        )
        self.assertEqual(
            self.workbook["Mecze"].max_row - 1,
            len(self.db["matches"]),
        )

    def test_public_plp_source_urls_are_clickable_in_excel(self):
        players = self.workbook["Zawodnicy"]
        moskal = next(
            row for row in list(players.iter_rows(min_row=2))
            if row[0].value == "1960"
        )
        self.assertEqual(moskal[9].value, 139)
        self.assertEqual(moskal[10].value, 31)
        self.assertEqual(moskal[11].value, 41)
        self.assertEqual(
            moskal[13].hyperlink.target,
            "https://podlaskaliga.pl/zawodnik/moskal-pawel/",
        )

    def test_derived_columns_use_excel_formulas_and_missing_values_are_blank(self):
        players = self.workbook["Zawodnicy"]
        self.assertEqual(players["F2"].data_type, "f")
        self.assertIn("ISNUMBER", players["F2"].value)
        self.assertEqual(self.workbook["Mecze"]["H2"].data_type, "f")
        self.assertEqual(self.workbook["Sezony"]["J2"].data_type, "f")
        self.assertTrue(self.workbook.calculation.fullCalcOnLoad)

    def test_canonical_player_id_is_exported_without_synthetic_duplicate(self):
        ids = [row[0].value for row in
               self.workbook["Zawodnicy"].iter_rows(min_row=2)]
        self.assertIn("1594", ids)
        self.assertNotIn("new-kakareko-kamil", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_boxscore_and_goal_rows_have_source_provenance(self):
        matches = self.workbook["Występy"]
        self.assertEqual(
            matches.max_row - 1,
            sum(len(m.get("player_performance") or []) for m in self.db["matches"]),
        )
        for sheet in (matches, self.workbook["Bramki"]):
            for row in sheet.iter_rows(min_row=2):
                self.assertTrue(
                    row[-1].value.startswith("https://podlaskaliga.pl/"),
                    f"Missing official source at row {row[0].row}",
                )

    def test_zero_unassigned_totals_do_not_mark_a_complete_player_as_incomplete(self):
        gaps = list(self.workbook["Braki danych"].iter_rows(min_row=2))
        self.assertFalse(any(row[0].value == "1960" for row in gaps))
        partial = next(row for row in gaps if row[0].value == "7270")
        self.assertEqual(partial[4].value, "TAK")
        allocated = next(row for row in gaps if row[0].value == "7271")
        self.assertEqual(allocated[4].value, "NIE")

    def test_windows_and_linux_line_endings_keep_the_same_workbook(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "data.json"
            destination = Path(folder) / "archive.xlsx"
            checksum = Path(folder) / "source.sha256"
            text = json.dumps(self.db, ensure_ascii=False) + "\n"
            source.write_bytes(text.encode("utf-8"))
            with patch.object(export_workbook, "SOURCE", source), patch.object(export_workbook, "DESTINATION", destination), patch.object(export_workbook, "CHECKSUM", checksum):
                export_workbook.main()
                expected_checksum = checksum.read_text()
                expected_workbook = destination.read_bytes()
                source.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
                with patch.object(export_workbook, "build_workbook", side_effect=AssertionError("Equivalent snapshot rebuilt")):
                    export_workbook.main()
                self.assertEqual(checksum.read_text(), expected_checksum)
                self.assertEqual(destination.read_bytes(), expected_workbook)

    def test_changed_exporter_rebuilds_even_when_data_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "data.json"
            destination = Path(folder) / "archive.xlsx"
            checksum = Path(folder) / "source.sha256"
            source.write_text(json.dumps(self.db), encoding="utf-8")
            with patch.object(export_workbook, "SOURCE", source), patch.object(export_workbook, "DESTINATION", destination), patch.object(export_workbook, "CHECKSUM", checksum):
                export_workbook.main()
                with patch.object(export_workbook, "exporter_signature", return_value="updated-exporter"):
                    export_workbook.main()
                check = export_workbook.load_workbook(destination, read_only=True)
                try:
                    self.assertEqual(check.properties.identifier, "updated-exporter")
                finally:
                    check.close()


if __name__ == "__main__":
    unittest.main()
