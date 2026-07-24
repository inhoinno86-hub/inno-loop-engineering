import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[3]


class LoopCtlTest(unittest.TestCase):
    def invoke(self, root, *args, ok=True):
        result = subprocess.run(["python3", "-m", "loop_engine.cli", "--project-root", str(root), *args], cwd=ROOT, text=True, capture_output=True)
        if ok: self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def evidence(self, root, loop, iteration):
        run_id = json.loads(self.invoke(root, "status").stdout)["run_id"]
        for name in ("ouroboros-interview", "superpowers-brainstorming", "superpowers-writing-plans"):
            path = root / ".loop-engine" / "runs" / run_id / "artifacts" / loop / f"iteration-{iteration}" / f"{name}.md"
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name, encoding="utf-8")
            self.invoke(root, "record-integration", "--loop", loop, "--name", name, "--status", "USED", "--artifact", str(path.relative_to(root)))

    def test_cli_rejects_unvalidated_lifecycle_and_keeps_registry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "intent.md").write_text("intent", encoding="utf-8")
            self.invoke(root, "init-auto", "--full-lifecycle")
            rejected = self.invoke(root, "plan", "--evidence", "init", ok=False)
            self.assertIn("validated init outputs", rejected.stdout)
            self.invoke(root, "registry", "add", "--agent-id", "a", "--depth", "0", "--scope", "test")
            self.assertEqual(json.loads(self.invoke(root, "heartbeat", "status").stdout)["stale_agent_ids"], [])

    def test_help_and_unavailable_integration_block(self):
        result = subprocess.run(["python3", "-m", "loop_engine.cli", "--help"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0); self.assertIn("record-quality-gate", result.stdout); self.assertIn("complete-init", result.stdout)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root / "intent.md").write_text("intent", encoding="utf-8"); self.invoke(root,"init-auto")
            self.invoke(root,"record-integration","--loop","project-init","--name","ouroboros-interview","--status","UNAVAILABLE","--detail","fixture")
            self.assertEqual(json.loads(self.invoke(root,"status").stdout)["outcome"], "BLOCKED")

    def test_explicit_project_local_input_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "asdf.md").write_text("alternate input", encoding="utf-8")
            state = json.loads(self.invoke(root, "init", "--intent-file", "asdf.md").stdout)
            self.assertEqual(state["input"]["source_ref"], "asdf.md")
            self.assertEqual(self.invoke(root, "init", "--intent-file", "../outside.md", ok=False).returncode, 2)

    def test_runs_list_select_and_explicit_parallel_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "one.md").write_text("one", encoding="utf-8"); (root / "two.md").write_text("two", encoding="utf-8")
            first = json.loads(self.invoke(root, "init", "--intent-file", "one.md").stdout)
            self.assertEqual(self.invoke(root, "init", "--intent-file", "two.md", ok=False).returncode, 2)
            second = json.loads(self.invoke(root, "init", "--intent-file", "two.md", "--new-lifecycle").stdout)
            runs = json.loads(self.invoke(root, "runs", "list").stdout)["runs"]
            self.assertEqual(len(runs), 2)
            self.assertEqual(json.loads(self.invoke(root, "runs", "select", "--run-id", first["run_id"]).stdout)["run_id"], first["run_id"])
            self.invoke(root, "runs", "lease", "--holder", "test")
            self.assertEqual(json.loads(self.invoke(root, "runs", "release-lease", "--holder", "test").stdout)["released"], True)
