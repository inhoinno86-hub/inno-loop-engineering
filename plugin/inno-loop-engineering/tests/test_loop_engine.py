import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from loop_engine import PolicyError, approval_request, initialize, load, record_failure, save, transition


class LoopEngineTest(unittest.TestCase):
    def test_happy_path_and_replan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = initialize(root, "# Intent\nBuild a local tool")
            transition(state, "complete-init", "charter"); transition(state, "complete-plan", "plan")
            transition(state, "complete-run", "tests")
            transition(state, "replan", "criterion-1")
            self.assertEqual(state["current_loop"], "project-plan")
            self.assertEqual(state["outcome"], "REPLAN")

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


if __name__ == "__main__":
    unittest.main()
