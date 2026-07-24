import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT))
from loop_engine import core


class LoopEngineTest(unittest.TestCase):
    def write(self, root, state, name, value):
        path = core.artifacts_path(root, state["run_id"]) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path.relative_to(root).as_posix()

    def integrations(self, root, state, loop):
        iteration = 0 if loop == "project-init" else state["plan_iteration"]
        for name in core.REQUIRED_INTEGRATIONS:
            ref = self.write(root, state, f"{loop}/iteration-{iteration}/{name}.json", {"name": name})
            core.record_integration(root, state, loop, name, "USED", ref)

    def packet(self, root, state, loop, sources=(), remediation=None):
        iteration = 0 if loop == "project-init" else state["plan_iteration"]
        value = {"loop": loop, "iteration": iteration, "input_hash": state["input_hash"] if loop == "project-init" else "plan-input", "source_artifacts": list(sources), "repository_context": ["fixture"]}
        if remediation: value["remediation_packet_hash"] = remediation
        ref = self.write(root, state, f"{loop}/iteration-{iteration}/input-packet.json", value)
        return ref, core.record_input_packet(root, state, loop, ref)

    def gate(self, root, state, loop, score=81, mediator=False, critical=False):
        iteration = 0 if loop == "project-init" else state["plan_iteration"]
        packet = state["input_packets"][f"{loop}:{iteration}"]
        refs = []
        for number in range(3):
            refs.append(self.write(root, state, f"{loop}/iteration-{iteration}/analysis-{number}.json", {
                "tool": "fixture", "run_id": f"{loop}-{iteration}-{number}", "invocation_id": f"invoke-{number}", "input_packet_hash": packet["content_hash"], "timestamp": "2026-07-24T00:00:00+00:00", "cited_input_hashes": [packet["input_hash"]], "sibling_output_hashes": [],
                "requirements": [], "constraints": [], "non_goals": [], "risks": [], "acceptance_criteria": [], "ambiguities": [],
            }))
        unanimous = score
        matrix = [{"id": "r1", "weight": unanimous, "classification": "unanimous", "material": True, "category": "normal"}]
        if score < 100:
            matrix.append({"id": "r2", "weight": 100 - score, "classification": "contradictory" if critical else "two-of-three", "material": True, "category": "security" if critical else "normal"})
        hashes = [core._json_artifact(root, state, ref)[1]["content_hash"] for ref in refs]
        judge = self.write(root, state, f"{loop}/iteration-{iteration}/judge.json", {
            "tool": "fixture", "run_id": f"judge-{loop}-{iteration}", "invocation_id": "judge-invoke", "timestamp": "2026-07-24T00:00:00+00:00", "input_packet_hash": packet["content_hash"], "analysis_hashes": hashes, "requirement_matrix": matrix, "consistency_score": score, "material_contradictions": ["r2"] if critical else [],
        })
        mediator_ref = None
        if mediator:
            judge_hash = core._json_artifact(root, state, judge)[1]["content_hash"]
            mediator_ref = self.write(root, state, f"{loop}/iteration-{iteration}/mediator.json", {"tool": "fixture", "run_id": f"mediator-{loop}-{iteration}", "invocation_id": "mediator-invoke", "timestamp": "2026-07-24T00:00:00+00:00", "input_packet_hash": packet["content_hash"], "judge_hash": judge_hash, "resolved_requirement_ids": ["r2"], "unresolved_requirement_ids": []})
        return core.record_quality_gate(root, state, loop, refs, judge, mediator_ref)

    def complete_init(self, root, state):
        packet_ref, packet = self.packet(root, state, "project-init")
        gate = self.gate(root, state, "project-init")
        self.integrations(root, state, "project-init")
        outputs = []
        for name in ("charter", "design", "roadmap"):
            outputs.append(self.write(root, state, f"project-init/iteration-0/{name}.json", {
                "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"],
                "goal": name, "scope": [], "requirements": [], "non_goals": [], "assumptions": [], "risks": [], "safety_approval_policy": [], "success_criteria": [], "open_decisions": [],
            }))
        core.complete_init(root, state, packet_ref, *outputs)

    def complete_plan(self, root, state):
        init_sources = [*state["init_outputs"]["artifacts"], {"content_hash": state["init_outputs"]["quality_gate_hash"]}]
        if state.get("remediation_packet"):
            init_sources.extend([state["remediation_packet"], state["plan_revisions"][-1]["execution_plan"], state["review_artifact"]])
        packet_ref, packet = self.packet(root, state, "project-plan", init_sources, (state.get("remediation_packet") or {}).get("content_hash"))
        gate = self.gate(root, state, "project-plan")
        self.integrations(root, state, "project-plan")
        iteration = state["plan_iteration"]
        plan = self.write(root, state, f"project-plan/iteration-{iteration}/execution-plan.json", {
            "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "plan_iteration": iteration,
            "tasks": [{"scope": "local", "owner": "agent", "dependencies": [], "definition_of_done": "done", "validation": "test", "rollback": "revert", "source_input_hash": packet["content_hash"], "source_plan_revision_hash": state["plan_revisions"][-1]["execution_plan"]["content_hash"] if state["plan_revisions"] else None}],
        })
        matrix = self.write(root, state, f"project-plan/iteration-{iteration}/validation-matrix.json", {"input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "plan_iteration": iteration, "validations": ["test"]})
        core.complete_plan(root, state, packet_ref, plan, matrix)

    def test_hash_bound_initial_and_replan_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.complete_init(root, state); self.complete_plan(root, state)
            core.transition(state, "complete-run", "run")
            revision = state["plan_revisions"][-1]["execution_plan"]["content_hash"]
            review = self.write(root, state, "project-review/iteration-1/review.json", {"plan_revision_hash": revision, "acceptance_results": []})
            review_record = core.record_review_artifact(root, state, review)
            remediation = self.write(root, state, "project-review/iteration-1/remediation.json", {"failed_acceptance_criteria": ["r"], "failure_evidence": ["e"], "plan_vs_actual": ["d"], "root_cause_or_uncertainty": "cause", "required_correction": "fix", "risk": "low", "non_deferrable": True, "prior_plan_revision_hash": revision, "review_artifact_hash": review_record["content_hash"]})
            state["remediation_packet"] = core.record_remediation_packet(root, state, remediation)
            core.transition(state, "replan", remediation)
            self.assertEqual((state["current_loop"], state["plan_iteration"]), ("project-plan", 2))
            self.complete_plan(root, state)

    def test_thresholds_and_material_contradiction_fail_closed(self):
        for score, mediator, expected in ((49, False, "BLOCKED"), (50, False, "BLOCKED"), (80, True, None), (81, False, None)):
            with self.subTest(score=score), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); state = core.initialize(root, "intent"); self.packet(root, state, "project-init")
                if score == 50:
                    with self.assertRaisesRegex(core.PolicyError, "mediator"):
                        self.gate(root, state, "project-init", score, mediator)
                else:
                    self.gate(root, state, "project-init", score, mediator)
                self.assertEqual(state["outcome"], expected)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent"); self.packet(root, state, "project-init")
            self.gate(root, state, "project-init", 81, critical=True)
            self.assertEqual(state["outcome"], "BLOCKED")

    def test_rejects_duplicate_identity_hash_mismatch_and_stale_transition(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            with self.assertRaisesRegex(core.PolicyError, "validated init"):
                core.transition(state, "complete-init", "nope")
            self.packet(root, state, "project-init")
            with self.assertRaisesRegex(core.PolicyError, "three distinct"):
                core.record_quality_gate(root, state, "project-init", ["same", "same", "same"], "judge")
            bad_packet = self.write(root, state, "project-init/iteration-0/bad-input-packet.json", {"loop": "project-init", "iteration": 0, "input_hash": "wrong", "source_artifacts": [], "repository_context": []})
            with self.assertRaisesRegex(core.PolicyError, "hash mismatch"):
                core.record_input_packet(root, state, "project-init", bad_packet)

    def test_run_quality_gate_executes_isolated_runners_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            self.packet(root, state, "project-init")
            runner = root / "runner.py"
            runner.write_text(textwrap.dedent("""
                import json, sys
                payload = json.load(sys.stdin)
                if payload['stage'] == 'analysis':
                    print(json.dumps({key: [] for key in ('requirements', 'constraints', 'non_goals', 'risks', 'acceptance_criteria', 'ambiguities')}))
                elif payload['stage'] == 'judge':
                    print(json.dumps({'requirement_matrix': [
                        {'id': 'a', 'weight': 81, 'classification': 'unanimous', 'material': True, 'category': 'normal'},
                        {'id': 'b', 'weight': 19, 'classification': 'two-of-three', 'material': True, 'category': 'normal'}], 'material_contradictions': []}))
                else:
                    print(json.dumps({'resolved_requirement_ids': ['b'], 'unresolved_requirement_ids': []}))
            """), encoding="utf-8")
            command = f"{sys.executable} {runner}"
            gate = core.run_quality_gate(root, state, "project-init", command, command)
            self.assertTrue(gate["accepted"])
            self.assertEqual(len(gate["analyses"]), 3)
            self.assertEqual(len({item["run_id"] for item in gate["analyses"]}), 3)
            self.assertTrue(all(item["artifact_ref"].startswith(f".loop-engine/runs/{state['run_id']}/artifacts/") for item in gate["analyses"]))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            self.packet(root, state, "project-init")
            with self.assertRaisesRegex(core.PolicyError, "quality runner failed"):
                core.run_quality_gate(root, state, "project-init", "missing-quality-runner", "missing-quality-runner")
            self.assertEqual(state["outcome"], "BLOCKED")

    def test_legacy_migration_and_multiple_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); legacy = root / ".inno-loop" / "state.json"; legacy.parent.mkdir()
            legacy.write_text('{"schema_version": 1, "outcome": "REPLAN", "replan_count": 1}', encoding="utf-8")
            migrated = core.load(root); self.assertEqual(migrated["plan_iteration"], 2)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = core.start_run(root, "one", "one.md", True, 3, new_lifecycle=True)
            second = core.start_run(root, "two", "two.md", True, 3, new_lifecycle=True)
            self.assertNotEqual(first["run_id"], second["run_id"])
