import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CLI = ROOT / "scripts" / "loopctl.py"


class LoopCtlTest(unittest.TestCase):
    def invoke(self, root, *args, ok=True):
        result = subprocess.run(["python3", str(CLI), "--project-root", str(root), *args], text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_complete_status_and_deferred_backlog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.invoke(root, "init", "--intent", "fixture")
            self.invoke(root, "plan", "--evidence", "charter")
            self.invoke(root, "run", "--evidence", "plan")
            self.invoke(root, "review", "--evidence", "run-evidence")
            state_path = root / ".loop-engine/state.json"; before = state_path.read_bytes()
            status = self.invoke(root, "status")
            self.assertEqual(before, state_path.read_bytes())
            self.assertEqual(json.loads(status.stdout)["current_loop"], "project-review")
            deferred = self.invoke(root, "defer", "--impact", "low", "--rationale", "later", "--owner", "team", "--revisit-trigger", "next-release")
            self.assertEqual(json.loads(deferred.stdout)["outcome"], "DEFERRED_BACKLOG")

    def test_malformed_and_approval_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(self.invoke(root, "init", "--intent", "", ok=False).returncode, 2)
            self.invoke(root, "init", "--intent", "fixture")
            blocked = self.invoke(root, "request-approval", "--category", "external_irreversible", "--action", "publish", "--impact", "public", "--alternatives", "none", "--decision", "approve")
            self.assertEqual(json.loads(blocked.stdout)["outcome"], "BLOCKED")

    def test_init_auto_accepts_alias_and_rejects_ambiguity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "intend.md").write_text("fixture", encoding="utf-8")
            initialized = self.invoke(root, "init-auto")
            self.assertEqual(json.loads(initialized.stdout)["input"]["source_ref"], "intend.md")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "intent.md").write_text("fixture", encoding="utf-8")
            (root / "intend.md").write_text("fixture", encoding="utf-8")
            result = self.invoke(root, "init-auto", ok=False)
            self.assertEqual(result.returncode, 2)

    def test_intent_file_stays_inside_project_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root.parent / "outside-intent.md"
            outside.write_text("fixture", encoding="utf-8")
            try:
                result = self.invoke(root, "init", "--intent-file", str(outside), ok=False)
                self.assertEqual(result.returncode, 2)
            finally:
                outside.unlink()

    def test_init_auto_never_overwrites_existing_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "intent.md").write_text("fixture", encoding="utf-8")
            self.invoke(root, "init-auto")
            before = (root / ".loop-engine/state.json").read_bytes()
            result = self.invoke(root, "init-auto", ok=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual((root / ".loop-engine/state.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
