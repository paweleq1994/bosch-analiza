import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceSyncPublishingTests(unittest.TestCase):
    def test_generated_source_artefacts_are_always_staged(self):
        workflow = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
        self.assertIn("git add -A -- data docs/assets docs/downloads docs/media reports", workflow)
        self.assertIn("if git diff --cached --quiet", workflow)
        self.assertIn("git fetch origin main", workflow)
        self.assertIn("git rebase origin/main", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertIn("python src/export_workbook.py", workflow)
        self.assertIn("python src/audit_video_coverage.py", workflow)
        self.assertNotIn("git diff --quiet -- data/video_updates", workflow)

    def test_scheduled_job_has_time_bounds(self):
        workflow = (ROOT / ".github/workflows/sync.yml").read_text(encoding="utf-8")
        self.assertIn("timeout-minutes: 28", workflow)
        self.assertIn("cancel-in-progress: true", workflow)


if __name__ == "__main__":
    unittest.main()
