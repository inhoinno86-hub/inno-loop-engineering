import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "init_project_loop.py"


class InitTests(unittest.TestCase):
    def run_cli(self, root, *extra):
        return subprocess.run(["python3", str(SCRIPT), "--project-root", str(root), "--project-id", "sample-project", *extra], text=True, capture_output=True)

    def test_fresh_initialization_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(len(data["created"]), 5)
            self.assertEqual(json.loads((Path(tmp) / ".project-loop/state.json").read_text())["project_id"], "sample-project")

    def test_second_run_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.run_cli(tmp)
            charter = Path(tmp) / "docs/project/CHARTER.md"
            charter.write_text("user content\n")
            result = self.run_cli(tmp)
            self.assertEqual(charter.read_text(), "user content\n")
            self.assertIn("docs/project/CHARTER.md", json.loads(result.stdout)["preserved"])

    def test_explicit_overwrite_replaces_only_managed_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_cli(root)
            unrelated = root / "keep.txt"
            unrelated.write_text("keep")
            result = self.run_cli(root, "--overwrite")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(unrelated.read_text(), "keep")
            self.assertEqual(len(json.loads(result.stdout)["replaced"]), 5)

    def test_invalid_project_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(["python3", str(SCRIPT), "--project-root", tmp, "--project-id", "Bad ID"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(tmp) / ".project-loop").exists())


if __name__ == "__main__":
    unittest.main()
