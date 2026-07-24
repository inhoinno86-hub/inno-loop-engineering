import sys
import tempfile
import unittest
import hashlib
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from loop_engine import PolicyError, approval_request, authorize_lifecycle, initialize, load, record_failure, record_integration, save, transition


class LoopEngineTest(unittest.TestCase):
    def record_required_integrations(self, state, loop):
        for name in ("ouroboros-interview", "superpowers-brainstorming", "superpowers-writing-plans"):
            content_hash = hashlib.sha256(name.encode()).hexdigest()
            record_integration(state, loop, name, "USED", f"artifacts/{loop}/{name}.md#sha256={content_hash}", f"artifacts/{loop}/{name}.md", content_hash)

    def test_happy_path_and_replan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = initialize(root, "# Intent\nBuild a local tool", full_lifecycle=True)
            self.record_required_integrations(state, "project-init")
            transition(state, "complete-init", "charter")
            self.record_required_integrations(state, "project-plan")
            transition(state, "complete-plan", "plan")
            transition(state, "complete-run", "tests")
            transition(state, "replan", "criterion-1")
            self.assertEqual(state["current_loop"], "project-plan")
            self.assertIsNone(state["outcome"])
            self.assertEqual(state["last_review_outcome"], "REPLAN")
            self.assertEqual(state["plan_iteration"], 2)
            self.record_required_integrations(state, "project-plan")
            transition(state, "complete-plan", "remediation-plan")
            self.assertEqual(state["current_loop"], "project-run")

    def test_invalid_input_and_illegal_transition_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PolicyError): initialize(Path(temp), "")
            state = initialize(Path(temp), "intent")
            with self.assertRaises(PolicyError): transition(state, "complete-run")

    def test_approval_and_failure_limit_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = initialize(root, "intent")
            approval_request(state, "external_irreversible", "deploy", "public", "do nothing", "approve")
            self.assertEqual(state["outcome"], "BLOCKED")

    def test_failure_limit_requires_consecutive_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            state = initialize(Path(temp), "intent")
            record_failure(state, "test", "exit", "same")
            record_failure(state, "test", "exit", "other")
            record_failure(state, "test", "exit", "same")
            record_failure(state, "test", "exit", "same")
            self.assertNotEqual(state["outcome"], "BLOCKED")
            record_failure(state, "test", "exit", "same")
            self.assertEqual(state["outcome"], "BLOCKED")
            transition(state, "resume", "user approval")
            for _ in range(3): record_failure(state, "test", "exit", "failure")
            self.assertEqual(state["outcome"], "BLOCKED")

    def test_checkpoint_persists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = initialize(root, "intent")
            state["checkpoint"] = {"id": "checkpoint-1"}; save(root, state)
            self.assertEqual(load(root)["checkpoint"]["id"], "checkpoint-1")

    def test_load_normalizes_legacy_replan_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = initialize(root, "intent", full_lifecycle=True)
            state.update({"current_loop": "project-plan", "outcome": "REPLAN", "replan_count": 1, "remediation_packet": {"evidence": "legacy"}})
            save(root, state)
            normalized = load(root)
            self.assertIsNone(normalized["outcome"])
            self.assertEqual(normalized["last_review_outcome"], "REPLAN")
            self.assertEqual(normalized["plan_iteration"], 2)

    def test_required_integrations_block_missing_or_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            state = initialize(Path(temp), "intent")
            with self.assertRaisesRegex(PolicyError, "required integrations missing"):
                transition(state, "complete-init", "charter")
            record_integration(state, "project-init", "ouroboros-interview", "UNAVAILABLE", "tools/interview")
            self.assertEqual(state["outcome"], "BLOCKED")

    def test_project_run_requires_full_lifecycle_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            state = initialize(Path(temp), "intent")
            self.record_required_integrations(state, "project-init")
            transition(state, "complete-init", "charter")
            self.record_required_integrations(state, "project-plan")
            with self.assertRaisesRegex(PolicyError, "full lifecycle authorization"):
                transition(state, "complete-plan", "plan")
            self.assertEqual(state["outcome"], "BLOCKED")
            authorize_lifecycle(state, "explicit inno-loop invocation")
            self.assertIsNone(state["outcome"])
            transition(state, "complete-plan", "plan")
            self.assertEqual(state["current_loop"], "project-run")

    def test_max_replans_blocks_after_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            state = initialize(Path(temp), "intent", full_lifecycle=True, max_replans=1)
            self.record_required_integrations(state, "project-init")
            transition(state, "complete-init", "charter")
            self.record_required_integrations(state, "project-plan")
            transition(state, "complete-plan", "plan")
            transition(state, "complete-run", "run")
            transition(state, "replan", "first remediation")
            self.record_required_integrations(state, "project-plan")
            transition(state, "complete-plan", "replan")
            transition(state, "complete-run", "run")
            transition(state, "replan", "second remediation")
            self.assertEqual(state["outcome"], "BLOCKED")
            self.assertEqual(state["block"]["reason"], "max_replans_exceeded")


if __name__ == "__main__":
    unittest.main()
