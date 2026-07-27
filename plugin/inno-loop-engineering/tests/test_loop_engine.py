import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT))
from loop_engine import core
from loop_engine import continuation_runner


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

    def complete_plan(self, root, state, mandatory=True):
        init_sources = [*state["init_outputs"]["artifacts"], {"content_hash": state["init_outputs"]["quality_gate_hash"]}]
        if state.get("remediation_packet"):
            init_sources.extend([state["remediation_packet"], state["plan_revisions"][-1]["execution_plan"], state["review_artifact"]])
        packet_ref, packet = self.packet(root, state, "project-plan", init_sources, (state.get("remediation_packet") or {}).get("content_hash"))
        gate = self.gate(root, state, "project-plan")
        self.integrations(root, state, "project-plan")
        iteration = state["plan_iteration"]
        plan = self.write(root, state, f"project-plan/iteration-{iteration}/execution-plan.json", {
            "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "plan_iteration": iteration,
            "tasks": [{"task_id": "task-1", "scope": "local", "owner": "agent", "dependencies": [], "definition_of_done": "done", "validation": "test", "rollback": "revert", "source_input_hash": packet["content_hash"], "source_plan_revision_hash": state["plan_revisions"][-1]["execution_plan"]["content_hash"] if state["plan_revisions"] else None, "criterion_ids": ["criterion-1"], "validation_ids": ["validation-1"]}],
        })
        matrix = self.write(root, state, f"project-plan/iteration-{iteration}/validation-matrix.json", {"input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "plan_iteration": iteration, "validations": [{"validation_id": "validation-1", "required": True, "procedure": "test"}], "criteria": [{"criterion_id": "criterion-1", "weight": 100, "mandatory": mandatory, "critical": False, "validation_ids": ["validation-1"]}]})
        core.complete_plan(root, state, packet_ref, plan, matrix)

    def test_bound_artifact_injects_trusted_plan_bindings_and_validates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "intent.md").write_text("intent", encoding="utf-8")
            state = core.start_run(root, "intent", "intent.md", True, 3, False)
            self.complete_init(root, state)
            packet_ref, packet = self.packet(root, state, "project-plan", [*state["init_outputs"]["artifacts"], {"content_hash": state["init_outputs"]["quality_gate_hash"]}])
            gate = self.gate(root, state, "project-plan"); self.integrations(root, state, "project-plan")
            iteration = state["plan_iteration"]
            (root / "plan-payload.json").write_text(json.dumps({"tasks": [{"task_id": "task-1", "scope": "local", "owner": "agent", "dependencies": [], "definition_of_done": "done", "validation": "test", "rollback": "revert", "criterion_ids": ["criterion-1"], "validation_ids": ["validation-1"]}]}), encoding="utf-8")
            (root / "matrix-payload.json").write_text(json.dumps({"validations": [{"validation_id": "validation-1", "required": True, "procedure": "test"}], "criteria": [{"criterion_id": "criterion-1", "weight": 1, "mandatory": True, "critical": False, "validation_ids": ["validation-1"]}]}), encoding="utf-8")
            plan_ref = core.write_bound_artifact(root, state, "execution_plan", "plan-payload.json", "execution-plan.json")
            matrix_ref = core.write_bound_artifact(root, state, "validation_matrix", "matrix-payload.json", "validation-matrix.json")
            plan, _ = core._json_artifact(root, state, plan_ref)
            self.assertEqual(plan["quality_gate_hash"], gate["judge"]["content_hash"])
            self.assertEqual(plan["tasks"][0]["source_input_hash"], packet["content_hash"])
            self.assertIsNone(plan["tasks"][0]["source_plan_revision_hash"])
            self.assertEqual(core.validate_stage_artifacts(root, state, {"input_packet": packet_ref, "execution_plan": plan_ref, "validation_matrix": matrix_ref})["valid"], True)

    def test_submission_rejects_unvalidated_plan_without_recording_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "intent.md").write_text("intent", encoding="utf-8")
            state = core.start_run(root, "intent", "intent.md", True, 3, False)
            self.complete_init(root, state)
            packet_ref, _ = self.packet(root, state, "project-plan", [*state["init_outputs"]["artifacts"], {"content_hash": state["init_outputs"]["quality_gate_hash"]}])
            self.gate(root, state, "project-plan"); self.integrations(root, state, "project-plan")
            plan_ref = self.write(root, state, "project-plan/iteration-1/execution-plan.json", {"input_packet_hash": "wrong", "plan_iteration": 1, "tasks": []})
            matrix_ref = self.write(root, state, "project-plan/iteration-1/validation-matrix.json", {"input_packet_hash": "wrong", "plan_iteration": 1, "validations": [], "criteria": []})
            submission = self.write(root, state, "project-plan/iteration-1/stage-submission.json", {"loop": "project-plan", "iteration": 1, "artifacts": {"input_packet": packet_ref, "execution_plan": plan_ref, "validation_matrix": matrix_ref}})
            with self.assertRaises(core.PolicyError):
                core.record_stage_submission(root, state, submission)
            self.assertNotIn("project-plan:1", state["stage_submissions"])

    def complete_run(self, root, state, advance=True):
        revision = state["plan_revisions"][-1]
        plan_hash = revision["execution_plan"]["content_hash"]; matrix_hash = revision["validation_matrix"]["content_hash"]
        policy = self.write(root, state, "project-run/iteration-1/execution-policy.json", {"plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash, "superpowers_execution": False, "task_policies": [{"task_id": "task-1", "topology": "coordinator executes locally", "write_scope": ["loop_engine/"], "limits": {"max_files": 1}, "safety_constraints": ["no external actions"], "execution_mode": "normal-codex", "rationale": "single bounded task", "observed_result_refs": ["execution-log"]}], "coordinator_id": "coordinator"})
        policy_record = core.record_execution_policy(root, state, policy)
        package = self.write(root, state, "project-run/iteration-1/prompt-package.json", {"plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash, "execution_policy_hash": policy_record["content_hash"], "steps": [{"step_id": "step-1", "task_ids": ["task-1"], "criterion_ids": ["criterion-1"], "validation_ids": ["validation-1"], "completion_checks": ["test"], "task_policy_ids": ["task-1"]}]})
        package_record = core.record_prompt_package(root, state, package)
        receipt = self.write(root, state, "project-run/iteration-1/receipt.json", {"plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash, "prompt_package_hash": package_record["content_hash"], "validation_id": "validation-1", "status": "PASS", "command": "test", "exit_code": 0, "executor_id": "executor", "invocation_id": "test-run", "timestamp": "2026-01-01T00:00:00Z", "evidence_refs": ["test-output"]})
        core.record_validation_receipt(root, state, receipt)
        report = self.write(root, state, "project-run/iteration-1/run-report.json", {"plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash, "prompt_package_hash": package_record["content_hash"], "task_results": [{"task_id": "task-1", "status": "PASS", "evidence_refs": ["test-output"], "executor_id": "executor", "invocation_id": "task-run", "timestamp": "2026-01-01T00:00:00Z"}], "executor_ids": ["executor"], "changed_files": []})
        core.record_run_report(root, state, report)
        if advance:
            core.complete_run(root, state, report)
        return plan_hash, matrix_hash, package_record

    def submission(self, root, state, artifacts):
        loop = state["current_loop"]
        iteration = 0 if loop == "project-init" else state["plan_iteration"]
        ref = self.write(root, state, f"{loop}/iteration-{iteration}/stage-submission.json", {
            "loop": loop, "iteration": iteration, "artifacts": artifacts,
        })
        core.record_stage_submission(root, state, ref)
        return ref

    def test_stage_executor_advances_init_and_replans_review_from_submissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            packet_ref, packet = self.packet(root, state, "project-init")
            gate = self.gate(root, state, "project-init"); self.integrations(root, state, "project-init")
            outputs = []
            for name in ("charter", "design", "roadmap"):
                outputs.append(self.write(root, state, f"project-init/iteration-0/{name}.json", {
                    "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"],
                    "goal": name, "scope": [], "requirements": [], "non_goals": [], "assumptions": [], "risks": [], "safety_approval_policy": [], "success_criteria": [], "open_decisions": [],
                }))
            self.submission(root, state, {"input_packet": packet_ref, "charter": outputs[0], "design": outputs[1], "roadmap": outputs[2]})
            expected = continuation_runner._state_identity(state); core.save(root, state)
            receipt = continuation_runner.execute_stage(root, expected)
            state = core.load(root)
            self.assertEqual(receipt["command"], "complete-init")
            self.assertEqual(state["current_loop"], "project-plan")
            self.complete_plan(root, state); self.complete_run(root, state)
            revision = state["plan_revisions"][-1]
            review = self.write(root, state, "project-review/iteration-1/review-executor.json", {
                "plan_revision_hash": revision["execution_plan"]["content_hash"], "validation_matrix_hash": revision["validation_matrix"]["content_hash"],
                "prompt_package_hash": state["prompt_package"]["content_hash"], "run_report_hash": state["run_report"]["content_hash"],
                "acceptance_results": [{"criterion_id": "criterion-1", "verdict": "FAIL", "evidence_refs": ["e"], "confidence": 1}], "reviewer_ids": ["reviewer"],
            })
            review_record = core.record_review_artifact(root, state, review)
            remediation = self.write(root, state, "project-review/iteration-1/remediation-executor.json", {
                "failed_acceptance_criteria": ["criterion-1"], "failure_evidence": ["e"], "plan_vs_actual": ["d"], "root_cause_or_uncertainty": "cause", "required_correction": "fix", "risk": "low", "non_deferrable": True,
                "prior_plan_revision_hash": revision["execution_plan"]["content_hash"], "review_artifact_hash": review_record["content_hash"],
            })
            state["remediation_packet"] = core.record_remediation_packet(root, state, remediation)
            self.submission(root, state, {"review_artifact": review, "remediation_packet": remediation})
            expected = continuation_runner._state_identity(state); core.save(root, state)
            receipt = continuation_runner.execute_stage(root, expected)
            state = core.load(root)
            self.assertEqual(receipt["command"], "replan")
            self.assertEqual((state["current_loop"], state["plan_iteration"]), ("project-plan", 2))

    def test_stage_executor_rejects_missing_submission_and_stale_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True); core.save(root, state)
            expected = continuation_runner._state_identity(state)
            with self.assertRaisesRegex(core.PolicyError, "submission"):
                continuation_runner.execute_stage(root, expected)
            state["current_loop"] = "project-plan"; core.save(root, state)
            with self.assertRaisesRegex(core.PolicyError, "unexpected state"):
                continuation_runner.execute_stage(root, expected)

    def test_stage_executor_advances_run_and_completes_passing_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.complete_init(root, state); self.complete_plan(root, state)
            plan_hash, matrix_hash, package = self.complete_run(root, state, advance=False)
            report = state["run_report"]["artifact_ref"]
            self.submission(root, state, {"run_report": report})
            expected = continuation_runner._state_identity(state); core.save(root, state)
            self.assertEqual(continuation_runner.execute_stage(root, expected)["command"], "review")
            state = core.load(root)
            self.assertEqual(state["current_loop"], "project-review")
            review = self.write(root, state, "project-review/iteration-1/review-pass-executor.json", {
                "plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash,
                "prompt_package_hash": package["content_hash"], "run_report_hash": state["run_report"]["content_hash"],
                "acceptance_results": [{"criterion_id": "criterion-1", "verdict": "PASS", "evidence_refs": ["e"], "confidence": 1}], "reviewer_ids": ["reviewer"],
            })
            core.record_review_artifact(root, state, review)
            self.submission(root, state, {"review_artifact": review})
            expected = continuation_runner._state_identity(state); core.save(root, state)
            self.assertEqual(continuation_runner.execute_stage(root, expected)["command"], "review-complete")
            self.assertEqual(core.load(root)["outcome"], "COMPLETE")

    def test_stage_executor_defers_nonmandatory_review_finding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.complete_init(root, state); self.complete_plan(root, state, mandatory=False)
            plan_hash, matrix_hash, package = self.complete_run(root, state)
            review = self.write(root, state, "project-review/iteration-1/review-defer-executor.json", {
                "plan_revision_hash": plan_hash, "validation_matrix_hash": matrix_hash,
                "prompt_package_hash": package["content_hash"], "run_report_hash": state["run_report"]["content_hash"],
                "acceptance_results": [{"criterion_id": "criterion-1", "verdict": "FAIL", "evidence_refs": ["e"], "confidence": 1}], "reviewer_ids": ["reviewer"],
            })
            core.record_review_artifact(root, state, review)
            backlog = self.write(root, state, "project-review/iteration-1/backlog-executor.json", {
                "impact": "low", "rationale": "not required", "owner": "owner", "revisit_trigger": "next release", "evidence_refs": ["e"], "criterion_ids": ["criterion-1"],
            })
            self.submission(root, state, {"review_artifact": review, "backlog_item": backlog})
            expected = continuation_runner._state_identity(state); core.save(root, state)
            self.assertEqual(continuation_runner.execute_stage(root, expected)["command"], "defer")
            self.assertEqual(core.load(root)["outcome"], "DEFERRED_BACKLOG")


    def test_hash_bound_initial_and_replan_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.complete_init(root, state); self.complete_plan(root, state)
            revision, matrix_hash, package = self.complete_run(root, state)
            review = self.write(root, state, "project-review/iteration-1/review.json", {"plan_revision_hash": revision, "validation_matrix_hash": matrix_hash, "prompt_package_hash": package["content_hash"], "run_report_hash": state["run_report"]["content_hash"], "acceptance_results": [{"criterion_id": "criterion-1", "verdict": "FAIL", "evidence_refs": ["e"], "confidence": 1}], "reviewer_ids": ["reviewer"]})
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
            with self.assertRaisesRegex(core.PolicyError, "validated run report"):
                core.transition(state, "complete-run", "nope")
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

    def test_canonical_requirement_gate_treats_contract_findings_as_plan_work(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            canonical = [
                {"id": "SAFE-1", "statement": "public only", "material": True, "category": "security", "source_refs": ["intent:1"]},
                {"id": "EXEC-1", "statement": "define depth formula", "material": True, "category": "execution", "source_refs": ["intent:2"]},
            ]
            packet_ref = self.write(root, state, "project-init/iteration-0/input-packet.json", {"loop": "project-init", "iteration": 0, "input_hash": state["input_hash"], "source_artifacts": [], "repository_context": ["fixture"], "canonical_requirements": canonical})
            packet = core.record_input_packet(root, state, "project-init", packet_ref)
            refs = []
            for number in range(3):
                refs.append(self.write(root, state, f"project-init/iteration-0/analysis-canonical-{number}.json", {
                    "tool": "fixture", "run_id": f"canonical-{number}", "invocation_id": f"invoke-{number}", "input_packet_hash": packet["content_hash"], "timestamp": "2026-07-26T00:00:00+00:00", "cited_input_hashes": [state["input_hash"]], "sibling_output_hashes": [],
                    "requirements": [], "constraints": [], "non_goals": [], "risks": [], "acceptance_criteria": [], "ambiguities": [],
                    "assessments": [{"requirement_id": "SAFE-1", "verdict": "confirmed", "evidence_refs": ["intent:1"]}, {"requirement_id": "EXEC-1", "verdict": "implementation_contract_needed", "evidence_refs": ["intent:2"]}],
                }))
            hashes = [core._json_artifact(root, state, ref)[1]["content_hash"] for ref in refs]
            judge = self.write(root, state, "project-init/iteration-0/judge-canonical.json", {"tool": "fixture", "run_id": "judge-canonical", "invocation_id": "judge", "timestamp": "2026-07-26T00:00:00+00:00", "input_packet_hash": packet["content_hash"], "analysis_hashes": hashes, "consistency_score": 50, "material_contradictions": [], "requirement_matrix": [
                {"id": "SAFE-1", "weight": 1, "classification": "unanimous", "material": True, "category": "security", "resolution": "confirmed", "evidence_refs": ["intent:1"]},
                {"id": "EXEC-1", "weight": 1, "classification": "unique", "material": True, "category": "execution", "resolution": "implementation_contract_needed", "evidence_refs": ["intent:2"]},
            ]})
            gate = core.record_quality_gate(root, state, "project-init", refs, judge)
            self.assertTrue(gate["accepted"])
            self.assertIsNone(state["outcome"])

    def test_epistemic_ledger_and_agent_health_are_local_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            source = self.write(root, state, "project-init/iteration-0/source.json", {"observed": True})
            source_hash = core._json_artifact(root, state, source)[1]["content_hash"]
            ledger = self.write(root, state, "project-init/iteration-0/ledger.json", {
                "loop": "project-init", "iteration": 0, "claims": [{
                    "claim_id": "fact-1", "statement": "local evidence exists", "classification": "known", "status": "active",
                    "source_artifacts": [{"artifact_ref": source, "content_hash": source_hash, "source_type": "primary_evidence"}], "confidence": 1, "impact": "low", "freshness": "stable", "timestamp": "2026-07-26T00:00:00Z",
                    "owner": "coordinator", "resolution_method": "validation", "linked_task_ids": [], "linked_criterion_ids": [], "conflict_claim_ids": [],
                }],
            })
            record = core.record_epistemic_ledger(root, state, ledger)
            self.assertEqual(record["claim_count"], 1)
            core.save(root, state)
            core.registry_add(root, "worker", None, 0, "bounded-task")
            health = core.record_agent_health(root, "worker", "timeout", "lost heartbeat", max_attempts=1, required=True)
            self.assertEqual(health["outcome"], "quarantined")
            self.assertEqual(core.load(root)["outcome"], "BLOCKED")

    def test_trajectory_retrieval_is_tag_bounded_and_non_authoritative(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            state["current_loop"] = "project-plan"
            retrieval = core.retrieve_trajectories(root, state, ["epistemic"], 2)
            self.assertTrue(retrieval["non_authoritative"])
            self.assertEqual(retrieval["candidates"], [])
            self.assertTrue(retrieval["artifact_ref"].startswith(f".loop-engine/runs/{state['run_id']}/artifacts/"))

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

    def test_continuation_directive_suppresses_nonterminal_output(self):
        with tempfile.TemporaryDirectory() as temp:
            state = core.initialize(Path(temp), "intent", full_lifecycle=True)
            directive = core.continuation_directive(state)
            self.assertEqual(directive["sequence"], ("project-init", "project-plan", "project-run", "project-review"))
            self.assertEqual(directive["iteration"], 0)
            self.assertEqual(directive["user_output"], "forbidden")
            state["replan_count"] = 1; state["plan_iteration"] = 2; state["current_loop"] = "project-plan"
            directive = core.continuation_directive(state)
            self.assertEqual(directive["sequence"], ("project-plan", "project-run", "project-review"))
            state["outcome"] = "COMPLETE"
            self.assertEqual(core.continuation_directive(state)["user_output"], "required")

    def test_continuation_prompt_uses_installed_cli_for_external_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "external-project"
            root.mkdir()
            state = core.initialize(root, "intent", full_lifecycle=True)
            prompt = continuation_runner._prompt(root, core.continuation_directive(state))
            self.assertIn(f"loop-engine --project-root {root}", prompt)
            self.assertNotIn("plugin/inno-loop-engineering", prompt)
            self.assertNotIn("skills/inno-loop/SKILL.md", prompt)

    def test_host_owned_integration_adapter_records_evidence_without_child_mcp(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            adapter = root / "adapter.py"
            adapter.write_text(textwrap.dedent("""
                import json
                from pathlib import Path
                payload = json.load(__import__('sys').stdin)
                if payload['operation'] == 'preflight':
                    print(json.dumps({'protocol_version': payload['protocol_version'], 'operation': 'preflight', 'request_id': payload['request_id'], 'ready': True}))
                    raise SystemExit(0)
                base = Path(payload['artifact_root']) / payload['loop'] / f\"iteration-{payload['iteration']}\"
                base.mkdir(parents=True, exist_ok=True)
                results = []
                for name in payload['required_integrations']:
                    path = base / f'{name}.json'
                    path.write_text(json.dumps({'host_owned': True, 'name': name}))
                    results.append({'name': name, 'status': 'USED', 'artifact': str(path)})
                print(json.dumps({'protocol_version': payload['protocol_version'], 'operation': 'integrate', 'request_id': payload['request_id'], 'results': results}))
            """), encoding="utf-8")
            directive = core.continuation_directive(state)
            self.assertTrue(continuation_runner._run_integration_adapter(root, state, directive, f"{sys.executable} {adapter}"))
            self.assertTrue(continuation_runner._planning_integrations_ready(state))
            self.assertIsNone(state["outcome"])

    def test_host_adapter_protocol_includes_snapshot_packet_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            packet_ref, packet = self.packet(root, state, "project-init")
            adapter = root / "adapter.py"
            adapter.write_text(textwrap.dedent("""
                import json
                from pathlib import Path
                payload = json.load(__import__('sys').stdin)
                assert payload['protocol_version'] == 2
                assert payload['operation'] == 'integrate'
                assert payload['lifecycle_input']['artifact_ref'].endswith('lifecycle-input.md')
                assert payload['lifecycle_input']['content_hash']
                assert payload['lifecycle_authorization']['scope'] == 'full-lifecycle'
                assert payload['input_packet']['artifact_ref'].endswith('input-packet.json')
                assert payload['input_packet']['content_hash']
                base = Path(payload['artifact_root']) / payload['loop'] / f\"iteration-{payload['iteration']}\"
                base.mkdir(parents=True, exist_ok=True)
                results = []
                for name in payload['required_integrations']:
                    path = base / f'{name}.json'; path.write_text('{}')
                    results.append({'name': name, 'status': 'USED', 'artifact': str(path)})
                print(json.dumps({'protocol_version': 2, 'operation': 'integrate', 'request_id': payload['request_id'], 'results': results}))
            """), encoding="utf-8")
            self.assertTrue(continuation_runner._run_integration_adapter(root, state, core.continuation_directive(state), f"{sys.executable} {adapter}", retries=0))
            receipt = core.artifacts_path(root, state['run_id']) / 'continuation' / 'bridge-project-init-0-0.json'
            self.assertTrue(receipt.is_file())
            self.assertEqual(packet['artifact_ref'], packet_ref)

    def test_host_bridge_retries_transient_failure_and_uses_environment_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            adapter = root / "adapter.py"; attempts = root / "attempts.txt"
            adapter.write_text(textwrap.dedent("""
                import json
                from pathlib import Path
                payload = json.load(__import__('sys').stdin)
                assert payload['operation'] == 'integrate'
                counter = Path('attempts.txt')
                count = int(counter.read_text() if counter.exists() else '0') + 1
                counter.write_text(str(count))
                if count == 1: raise SystemExit(1)
                base = Path(payload['artifact_root']) / payload['loop'] / f\"iteration-{payload['iteration']}\"
                base.mkdir(parents=True, exist_ok=True)
                results = []
                for name in payload['required_integrations']:
                    path = base / f'{name}.json'; path.write_text('{}')
                    results.append({'name': name, 'status': 'USED', 'artifact': str(path)})
                print(json.dumps({'protocol_version': 2, 'operation': 'integrate', 'request_id': payload['request_id'], 'results': results}))
            """), encoding="utf-8")
            old = __import__('os').environ.get('LOOP_ENGINE_HOST_BRIDGE_COMMAND')
            __import__('os').environ['LOOP_ENGINE_HOST_BRIDGE_COMMAND'] = f"{sys.executable} {adapter}"
            try:
                self.assertTrue(continuation_runner._run_integration_adapter(root, state, core.continuation_directive(state), None, retries=1, retry_backoff_seconds=0))
            finally:
                if old is None: __import__('os').environ.pop('LOOP_ENGINE_HOST_BRIDGE_COMMAND', None)
                else: __import__('os').environ['LOOP_ENGINE_HOST_BRIDGE_COMMAND'] = old
            self.assertEqual(attempts.read_text(), '2')

    def test_unavailable_host_bridge_blocks_without_cancellation_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.assertFalse(continuation_runner._run_integration_adapter(root, state, core.continuation_directive(state), "definitely-not-a-host-bridge", retries=0))
            self.assertEqual(state["block"]["reason"], "continuation_integration_adapter_failed")
            self.assertNotIn("cancel", state["block"]["evidence"].lower())

    def test_missing_host_adapter_blocks_without_implicit_codex_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.assertFalse(continuation_runner._run_integration_adapter(root, state, core.continuation_directive(state), None, retries=0))
            self.assertEqual(state["block"]["reason"], "continuation_integration_adapter_required")

    def test_preflight_requires_explicit_capable_parent_host_adapter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            self.assertIsNone(continuation_runner._resolve_integration_adapter(None))
            self.assertFalse(continuation_runner.bridge_preflight(root, state, None)["ready"])
            adapter = root / "adapter.py"
            adapter.write_text(textwrap.dedent("""
                import json
                payload = json.load(__import__('sys').stdin)
                assert payload['protocol_version'] == 2
                assert payload['operation'] == 'preflight'
                assert payload['interactive_parent_required'] is True
                print(json.dumps({'protocol_version': 2, 'operation': 'preflight', 'request_id': payload['request_id'], 'ready': True}))
            """), encoding="utf-8")
            self.assertTrue(continuation_runner.bridge_preflight(root, state, f"{sys.executable} {adapter}")["ready"])
            self.assertEqual(state["integration_evidence"], [])
            self.integrations(root, state, "project-init")
            self.assertTrue(continuation_runner.bridge_preflight(root, state, None)["ready"])

    def test_preflight_rejects_non_capable_adapter_and_payload_carries_plan_lineage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            bad = root / "bad.py"
            bad.write_text("import json; print(json.dumps({'ready': True}))", encoding="utf-8")
            self.assertFalse(continuation_runner.bridge_preflight(root, state, f"{sys.executable} {bad}")["ready"])
            self.complete_init(root, state)
            directive = core.continuation_directive(state)
            payload = continuation_runner._bridge_payload(root, state, directive, 0)
            self.assertEqual(payload["operation"], "integrate")
            self.assertEqual(payload["init_outputs"], state["init_outputs"])
            self.assertIsNone(payload["remediation_packet"])

    def test_unattended_runner_blocks_before_child_when_planning_host_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core.initialize(root, "intent", full_lifecycle=True)
            self.assertEqual(continuation_runner.main(["--project-root", str(root), "--codex-bin", "must-not-run"]), 2)
            blocked = core.load(root)
            self.assertEqual(blocked["block"]["reason"], "continuation_host_bridge_unavailable")

    def test_nonplanning_stage_does_not_require_host_adapter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            state["current_loop"] = "project-run"
            self.assertTrue(continuation_runner.bridge_preflight(root, state, None)["ready"])

    def test_resumed_integration_failure_starts_a_new_auditable_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent", full_lifecycle=True)
            core.record_integration(root, state, "project-init", "ouroboros-interview", "FAILED", detail="transient host bridge failure")
            blocked = state["block"]
            core.transition(state, "resume", json.dumps({"owner_id": "owner", "owner_role": "project-owner", "blocked_reason": blocked["reason"], "blocked_evidence": blocked["evidence"], "decision": "resume", "remediation_status": "retry-authorized", "remediation_evidence_refs": ["host-retry"], "next_attempt_policy": {"mode": "retry"}}))
            ref = self.write(root, state, "project-init/iteration-0/retry.json", {"retry": True})
            core.record_integration(root, state, "project-init", "ouroboros-interview", "USED", ref)
            record = state["integration_evidence"][-1]
            self.assertEqual(record["attempt"], 1)
            self.assertEqual(record["status"], "USED")

    def test_block_emits_idempotent_alert_and_baseline_preserves_existing_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            (root / "preexisting.txt").write_text("x", encoding="utf-8")
            # A non-git fixture cannot capture a baseline; alert delivery remains
            # independent from repository inspection.
            core.block(state, "budget_limit_breach", True, "scope exceeded")
            pending = core.pending_alerts(state)
            self.assertEqual(len(pending), 1)
            delivered = core.acknowledge_alert(state, pending[0]["alert_id"], "host-notified")
            self.assertEqual(delivered["delivery"], "DELIVERED")
            self.assertEqual(core.pending_alerts(state), [])

    def test_resume_resolves_the_exact_pending_block_alert(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); state = core.initialize(root, "intent")
            core.block(state, "budget_limit_breach", True, "exact evidence")
            blocked = state["block"]
            core.transition(state, "resume", json.dumps({"owner_id": "owner", "owner_role": "project-owner", "blocked_reason": blocked["reason"], "blocked_evidence": blocked["evidence"], "decision": "resume", "remediation_status": "resolved", "remediation_evidence_refs": ["baseline"], "next_attempt_policy": {"mode": "retry"}}))
            self.assertEqual(state["alerts"][0]["delivery"], "RESOLVED")
            self.assertEqual(core.pending_alerts(state), [])
