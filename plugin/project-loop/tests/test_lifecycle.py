import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
INIT = ROOT / "scripts/init_project_loop.py"
VALIDATE = ROOT / "scripts/validate_project_loop.py"
RENDER = ROOT / "scripts/render_status.py"


class LifecycleTest(unittest.TestCase):
    def test_disposable_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["python3", str(INIT), "--project-root", tmp, "--project-id", "e2e-project"], check=True, capture_output=True)

            def run(*args, ok=True):
                result = subprocess.run(["python3", str(VALIDATE), *args, "--project-root", tmp], text=True, capture_output=True)
                if ok:
                    self.assertEqual(result.returncode, 0, result.stderr)
                return result

            def approve(relative, label):
                path = root / relative
                path.write_text(path.read_text() + f"\n- 2026-07-16: APPROVED - {label} - User\n")
                return relative

            run("transition", "--to", "COMPLETE", ok=False)
            for state, relative in [("CHARTER_APPROVED", "docs/project/CHARTER.md"), ("DESIGN_APPROVED", "docs/project/DESIGN.md")]:
                run("transition", "--to", state, "--approval-ref", approve(relative, state))
            roadmap = root / "docs/project/ROADMAP.md"
            roadmap.write_text(roadmap.read_text() + "\n- [x] lifecycle verified\n")
            run("transition", "--to", "ROADMAP_APPROVED", "--approval-ref", approve("docs/project/ROADMAP.md", "ROADMAP_APPROVED"), "--active-milestone", "m1")

            plan = root / "PLAN-2026-07-16-e2e.md"
            plan.write_text("\n".join(["# E2E Plan", "## Planning Metadata", "- Planning artifact: PLAN-2026-07-16-e2e.md", "- Planning mode: Superpowers", "- Superpowers planning: enabled", "- Superpowers execution: enabled", "- Superpowers brainstorming: used", "- Ouroboros interview: disabled / not used", "## Progress Log", "## Decision Log", "- 2026-07-16: APPROVED - E2E plan - User", "## Rollback Plan"]))
            run("transition", "--to", "PLAN_APPROVED", "--approval-ref", plan.name, "--active-plan", plan.name, "--superpowers-planning", "enabled", "--superpowers-execution", "enabled")
            digest = hashlib.sha256(plan.read_bytes()).hexdigest()
            prompts = root / "to-do-prompts/main.md"; prompts.parent.mkdir(); prompts.write_text(f"Active plan: {plan.name}\nPlan SHA-256: {digest}\n")
            run("transition", "--to", "PROMPTS_READY")
            run("transition", "--to", "EXECUTING")
            run("transition", "--to", "REWORK", "--failure-command", "python3 -m unittest", "--failure-class", "exit-1", "--failure-id", "AssertionError")
            run("transition", "--to", "EXECUTING")
            run("transition", "--to", "VERIFYING")
            evidence = root / "validation.txt"; evidence.write_text("all checks passed\n")
            run("transition", "--to", "COMPLETE", "--evidence-ref", "validation.txt")
            before = (root / ".project-loop/state.json").read_bytes()
            subprocess.run(["python3", str(RENDER), "--project-root", tmp], check=True, capture_output=True)
            self.assertEqual(before, (root / ".project-loop/state.json").read_bytes())
            self.assertEqual(json.loads(before)["state"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
