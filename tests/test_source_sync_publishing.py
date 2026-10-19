import unittest
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceSyncPublishingTests(unittest.TestCase):
    def publication_commands(self):
        workflow = (ROOT / ".github/workflows/publish-downloads.yml").read_text(encoding="utf-8")
        return [line.strip() for line in workflow.splitlines()]

    def test_each_published_file_is_checked_separately(self):
        checks = [shlex.split(line) for line in self.publication_commands()
                  if line.startswith("test -s ")]
        expected = {
            "docs/downloads/bosch-kompendium.xlsx",
            "reports/video-goal-review-queue.md",
            "reports/video-coverage.md",
            "reports/player-source-reconciliation.md",
            "reports/player-data-coverage.md",
        }
        self.assertEqual({args[2] for args in checks}, expected)
        for args in checks:
            self.assertEqual(len(args), 3, f"test -s accepts one file: {args}")

        bash = shutil.which("bash")
        # Windows may expose WSL's launcher instead of an installed Bash shell.
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.exists():
            bash = str(git_bash)
        if not bash:
            self.skipTest("Bash is required to execute GitHub's file checks")
        with tempfile.TemporaryDirectory() as folder:
            for name in expected:
                target = Path(folder) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("verified artifact", encoding="utf-8")
            for args in checks:
                command = shlex.join(args)
                result = subprocess.run([bash, "-c", command], cwd=folder, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                (Path(folder) / args[2]).write_text("", encoding="utf-8")
                result = subprocess.run([bash, "-c", command], cwd=folder, capture_output=True)
                self.assertNotEqual(result.returncode, 0, f"Empty artifact accepted: {args[2]}")

    def test_publication_stages_every_generated_report_including_goal_queue(self):
        commands = [shlex.split(line) for line in self.publication_commands()
                    if line.startswith("git add ")]
        expected = {
            "docs/downloads/bosch-kompendium.xlsx",
            "docs/downloads/bosch-kompendium.source.sha256",
            "reports/video-coverage.md",
            "reports/player-data-coverage.md",
            "reports/player-source-reconciliation.md",
            "reports/video-goal-review-queue.md",
        }
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(["git", "init", "-q", folder], check=True, capture_output=True)
            for name in expected:
                target = Path(folder) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("verified artifact", encoding="utf-8")
            for args in commands:
                subprocess.run(args, cwd=folder, check=True, capture_output=True)
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"], cwd=folder,
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
            self.assertEqual(set(staged), expected)

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
