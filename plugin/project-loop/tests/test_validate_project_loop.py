import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
INIT = ROOT / "scripts/init_project_loop.py"
VALIDATE = ROOT / "scripts/validate_project_loop.py"


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["python3", str(INIT), "--project-root", str(self.root), "--project-id", "sample-project"], check=True, capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def state(self):
        return json.loads((self.root / ".project-loop/state.json").read_text())

    def command(self, *args):
        return subprocess.run(["python3", str(VALIDATE), *args, "--project-root", str(self.root)], text=True, capture_output=True)

    def approve(self, relative):
        path = self.root / relative
        path.write_text(path.read_text() + "\n- 2026-07-16: APPROVED - artifact - User\n")

    def move(self, target, approval=None, *extra):
        args = ["transition", "--to", target]
        if approval:
            args += ["--approval-ref", approval]
        args += list(extra)
        return self.command(*args)

    def advance_to_roadmap(self):
        for target, doc in [("CHARTER_APPROVED", "docs/project/CHARTER.md"), ("DESIGN_APPROVED", "docs/project/DESIGN.md"), ("ROADMAP_APPROVED", "docs/project/ROADMAP.md")]:
            self.approve(doc)
            result = self.move(target, doc, *(["--active-milestone", "m1"] if target == "ROADMAP_APPROVED" else []))
            self.assertEqual(result.returncode, 0, result.stderr)

    def make_plan(self):
        text = "\n".join(["# Plan", "## Planning Metadata", "- Planning artifact: PLAN-2026-07-16-sample.md", "- Planning mode: Superpowers", "- Superpowers planning: enabled", "- Superpowers execution: enabled", "- Superpowers brainstorming: used", "- Ouroboros interview: disabled / not used", "## Progress Log", "## Decision Log", "- 2026-07-16: APPROVED - plan - User", "## Rollback Plan"])
        path = self.root / "PLAN-2026-07-16-sample.md"
        path.write_text(text)
        return path

    def advance_to_executing(self):
        self.advance_to_roadmap()
        plan = self.make_plan()
        result = self.move("PLAN_APPROVED", plan.name, "--active-plan", plan.name, "--superpowers-execution", "enabled")
        self.assertEqual(result.returncode, 0, result.stderr)
        digest = hashlib.sha256(plan.read_bytes()).hexdigest()
        prompt = self.root / "to-do-prompts/main.md"
        prompt.parent.mkdir()
        prompt.write_text(f"Active plan: {plan.name}\nPlan SHA-256: {digest}\n")
        self.assertEqual(self.move("PROMPTS_READY").returncode, 0)
        self.assertEqual(self.move("EXECUTING").returncode, 0)

    def test_fresh_state_validates(self):
        self.assertEqual(self.command("validate").returncode, 0)

    def test_unknown_schema_fails(self):
        data = self.state(); data["schema_version"] = 99
        (self.root / ".project-loop/state.json").write_text(json.dumps(data))
        self.assertEqual(self.command("validate").returncode, 2)

    def test_illegal_transition_does_not_mutate(self):
        before = (self.root / ".project-loop/state.json").read_bytes()
        result = self.move("COMPLETE")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / ".project-loop/state.json").read_bytes(), before)

    def test_approval_requires_decision_log_evidence(self):
        self.assertEqual(self.move("CHARTER_APPROVED", "docs/project/CHARTER.md").returncode, 2)
        self.approve("docs/project/CHARTER.md")
        self.assertEqual(self.move("CHARTER_APPROVED", "docs/project/CHARTER.md").returncode, 0)

    def test_prompt_digest_is_enforced(self):
        self.advance_to_roadmap(); plan = self.make_plan()
        self.assertEqual(self.move("PLAN_APPROVED", plan.name, "--active-plan", plan.name).returncode, 0)
        prompt = self.root / "to-do-prompts/main.md"; prompt.parent.mkdir(); prompt.write_text(f"Active plan: {plan.name}\nPlan SHA-256: wrong\n")
        self.assertEqual(self.move("PROMPTS_READY").returncode, 2)

    def test_third_identical_failure_blocks(self):
        self.advance_to_executing()
        for index in range(3):
            result = self.move("REWORK", None, "--failure-command", "pytest /tmp/a", "--failure-class", "exit-1", "--failure-id", "AssertionError")
            self.assertEqual(result.returncode, 0, result.stderr)
            if index < 2:
                self.assertEqual(self.move("EXECUTING").returncode, 0)
        self.assertEqual(self.state()["state"], "BLOCKED")

    def test_complete_requires_evidence_and_checked_dod(self):
        self.advance_to_executing(); self.assertEqual(self.move("VERIFYING").returncode, 0)
        roadmap = self.root / "docs/project/ROADMAP.md"
        roadmap.write_text(roadmap.read_text() + "\n- [ ] verified\n")
        evidence = self.root / "evidence.txt"; evidence.write_text("pass")
        self.assertEqual(self.move("COMPLETE", None, "--evidence-ref", "evidence.txt").returncode, 2)
        roadmap.write_text(roadmap.read_text().replace("- [ ] verified", "- [x] verified"))
        self.assertEqual(self.move("COMPLETE", None, "--evidence-ref", "evidence.txt").returncode, 0)

    def test_fifth_rework_requires_user_review(self):
        self.advance_to_executing()
        for index in range(5):
            result = self.move("REWORK", None, "--failure-command", f"pytest case-{index}", "--failure-class", "exit-1", "--failure-id", f"Failure{index}")
            self.assertEqual(result.returncode, 0, result.stderr)
            if index < 4:
                self.assertEqual(self.move("EXECUTING").returncode, 0)
        self.assertTrue(self.state()["user_review_required"])
        self.assertEqual(self.move("EXECUTING").returncode, 2)
        self.assertEqual(self.move("EXECUTING", "docs/project/ROADMAP.md").returncode, 0)


if __name__ == "__main__":
    unittest.main()
