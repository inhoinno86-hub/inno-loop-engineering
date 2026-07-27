"""Public local `loop-engine` command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import core


def _intent(root: Path, candidate: str | None) -> tuple[str, str]:
    if candidate: paths = [root / candidate]
    else: paths = [root / name for name in ("intent.md", "intend.md") if (root / name).is_file()]
    if len(paths) != 1 or not paths[0].is_file(): raise core.PolicyError("exactly one intent.md or intend.md is required")
    path = paths[0].resolve()
    try: path.relative_to(root)
    except ValueError as error: raise core.PolicyError("intent file must be inside project root") from error
    return path.read_text(encoding="utf-8"), str(path.relative_to(root))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="loop-engine")
    parser.add_argument("--project-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "init-auto"):
        item=sub.add_parser(name); item.add_argument("--intent-file"); item.add_argument("--full-lifecycle", action="store_true"); item.add_argument("--new-lifecycle", action="store_true"); item.add_argument("--max-replans", type=int, default=3)
    for name in ("plan", "run", "replan"): sub.add_parser(name).add_argument("--evidence", required=True)
    review=sub.add_parser("review"); review.add_argument("--run-report", required=True)
    review_complete=sub.add_parser("review-complete"); review_complete.add_argument("--artifact", required=True)
    defer=sub.add_parser("defer"); defer.add_argument("--artifact", required=True)
    packet=sub.add_parser("record-input-packet"); packet.add_argument("--loop", required=True); packet.add_argument("--artifact", required=True)
    quality=sub.add_parser("record-quality-gate"); quality.add_argument("--loop", required=True); quality.add_argument("--analysis", action="append", required=True); quality.add_argument("--judge", required=True); quality.add_argument("--mediator")
    run_quality=sub.add_parser("run-quality-gate"); run_quality.add_argument("--loop", required=True); run_quality.add_argument("--analysis-runner", required=True); run_quality.add_argument("--judge-runner", required=True); run_quality.add_argument("--mediator-runner")
    finish_init=sub.add_parser("complete-init"); finish_init.add_argument("--input-packet", required=True); finish_init.add_argument("--charter", required=True); finish_init.add_argument("--design", required=True); finish_init.add_argument("--roadmap", required=True)
    finish_plan=sub.add_parser("complete-plan"); finish_plan.add_argument("--input-packet", required=True); finish_plan.add_argument("--execution-plan", required=True); finish_plan.add_argument("--validation-matrix", required=True)
    review_artifact=sub.add_parser("record-review-artifact"); review_artifact.add_argument("--artifact", required=True)
    remediation=sub.add_parser("record-remediation-packet"); remediation.add_argument("--artifact", required=True)
    execution_policy=sub.add_parser("record-execution-policy"); execution_policy.add_argument("--artifact", required=True)
    prompt_package=sub.add_parser("record-prompt-package"); prompt_package.add_argument("--artifact", required=True)
    run_report=sub.add_parser("record-run-report"); run_report.add_argument("--artifact", required=True)
    receipt=sub.add_parser("record-validation-receipt"); receipt.add_argument("--artifact", required=True)
    submission=sub.add_parser("record-stage-submission"); submission.add_argument("--artifact", required=True)
    ledger=sub.add_parser("record-epistemic-ledger"); ledger.add_argument("--artifact", required=True)
    trajectory=sub.add_parser("record-trajectory-summary"); trajectory.add_argument("--artifact", required=True)
    context=sub.add_parser("artifact-context"); context.add_argument("--artifact-type", required=True)
    bound=sub.add_parser("write-bound-artifact"); bound.add_argument("--artifact-type", required=True); bound.add_argument("--payload", required=True); bound.add_argument("--output-name", required=True)
    validate=sub.add_parser("validate-stage-artifacts"); validate.add_argument("--artifact", action="append", required=True, help="key=project-relative artifact ref")
    retrieve=sub.add_parser("retrieve-trajectories"); retrieve.add_argument("--tag", action="append", required=True); retrieve.add_argument("--limit", type=int, default=5)
    integ=sub.add_parser("record-integration"); integ.add_argument("--loop", required=True); integ.add_argument("--name", required=True); integ.add_argument("--status", required=True); integ.add_argument("--artifact"); integ.add_argument("--detail", default="")
    auth=sub.add_parser("authorize-lifecycle"); auth.add_argument("--evidence", required=True)
    resume=sub.add_parser("resume"); resume.add_argument("--evidence", required=True)
    fail=sub.add_parser("failure"); fail.add_argument("--failed-command", required=True); fail.add_argument("--failure-class", required=True); fail.add_argument("--failure-id", required=True)
    approval=sub.add_parser("request-approval"); [approval.add_argument(f"--{x}", required=True) for x in ("category", "action", "impact", "alternatives", "decision")]
    sub.add_parser("status")
    preflight=sub.add_parser("preflight"); preflight.add_argument("--host-bridge-command")
    sub.add_parser("continuation")
    sub.add_parser("capture-worktree-baseline")
    alerts=sub.add_parser("alerts"); alertsub=alerts.add_subparsers(dest="alert_command", required=True); alertsub.add_parser("pending"); ack=alertsub.add_parser("ack"); ack.add_argument("--alert-id", required=True); ack.add_argument("--receipt", required=True)
    runner=sub.add_parser("continue-until-terminal"); runner.add_argument("--max-stages", type=int, default=64); runner.add_argument("--codex-bin", default="codex"); runner.add_argument("--codex-sandbox", choices=("read-only", "workspace-write", "danger-full-access")); runner.add_argument("--integration-adapter", "--host-bridge-command", dest="integration_adapter"); runner.add_argument("--integration-retries", type=int, default=2); runner.add_argument("--integration-retry-backoff-seconds", type=float, default=1.0); runner.add_argument("--alert-adapter")
    runs=sub.add_parser("runs"); runsub=runs.add_subparsers(dest="run_command", required=True); runsub.add_parser("list"); select=runsub.add_parser("select"); select.add_argument("--run-id", required=True); lease=runsub.add_parser("lease"); lease.add_argument("--holder", required=True); lease.add_argument("--timeout-seconds", type=int, default=300); release=runsub.add_parser("release-lease"); release.add_argument("--holder", required=True)
    registry=sub.add_parser("registry"); rsub=registry.add_subparsers(dest="registry_command", required=True); add=rsub.add_parser("add"); add.add_argument("--agent-id", required=True); add.add_argument("--parent-id"); add.add_argument("--depth", type=int, required=True); add.add_argument("--scope", required=True); update=rsub.add_parser("update"); update.add_argument("--agent-id", required=True); update.add_argument("--status", required=True); rsub.add_parser("list")
    heartbeat=sub.add_parser("heartbeat"); hsub=heartbeat.add_subparsers(dest="heartbeat_command", required=True); touch=hsub.add_parser("touch"); touch.add_argument("--agent-id", required=True); hstatus=hsub.add_parser("status"); hstatus.add_argument("--timeout-seconds", type=int, default=300)
    health=sub.add_parser("health"); healthsub=health.add_subparsers(dest="health_command", required=True); report=healthsub.add_parser("report"); report.add_argument("--agent-id", required=True); report.add_argument("--outcome", required=True); report.add_argument("--failure-id", default=""); report.add_argument("--max-attempts", type=int, default=3); report.add_argument("--required", action="store_true"); healthsub.add_parser("status"); reconcile=healthsub.add_parser("reconcile"); reconcile.add_argument("--timeout-seconds", type=int, default=300)
    args=parser.parse_args(argv); root=Path(args.project_root).resolve(); state = None
    try:
        if args.command in ("init", "init-auto"):
            intent, source = _intent(root, args.intent_file); state=core.start_run(root, intent, source, args.full_lifecycle, args.max_replans, args.new_lifecycle)
        elif args.command == "status": state=core.load(root)
        elif args.command == "preflight":
            from .continuation_runner import bridge_preflight
            state=bridge_preflight(root, core.load(root), args.host_bridge_command)
        elif args.command == "continuation": state=core.continuation_directive(core.load(root))
        elif args.command == "artifact-context": state=core.artifact_context(root, core.load(root), args.artifact_type)
        elif args.command == "write-bound-artifact":
            state=core.load(root); state={"artifact_ref": core.write_bound_artifact(root, state, args.artifact_type, args.payload, args.output_name)}
        elif args.command == "validate-stage-artifacts":
            state=core.load(root); artifacts={}
            for item in args.artifact:
                key, separator, ref = item.partition("=")
                if not separator or not key or not ref or key in artifacts: raise core.PolicyError("--artifact must be unique key=ref")
                artifacts[key] = ref
            state=core.validate_stage_artifacts(root, state, artifacts)
        elif args.command == "capture-worktree-baseline":
            state=core.load(root); core.capture_worktree_baseline(root, state); core.save(root, state)
        elif args.command == "alerts":
            state=core.load(root)
            if args.alert_command == "pending":
                alerts = core.pending_alerts(state); core.save(root,state); state={"alerts": alerts}
            else:
                alert=core.acknowledge_alert(state,args.alert_id,args.receipt); core.save(root,state); state={"alert": alert}
        elif args.command == "continue-until-terminal":
            from .continuation_runner import main as runner_main
            runner_args = ["--project-root", str(root), "--max-stages", str(args.max_stages), "--codex-bin", args.codex_bin, "--integration-retries", str(args.integration_retries), "--integration-retry-backoff-seconds", str(args.integration_retry_backoff_seconds)]
            if args.codex_sandbox: runner_args.extend(["--codex-sandbox", args.codex_sandbox])
            if args.integration_adapter: runner_args.extend(["--integration-adapter", args.integration_adapter])
            if args.alert_adapter: runner_args.extend(["--alert-adapter", args.alert_adapter])
            return runner_main(runner_args)
        elif args.command == "runs":
            if args.run_command == "list": state = {"runs": core.list_runs(root)}
            elif args.run_command == "select": state = core.select_run(root, args.run_id)
            elif args.run_command == "lease": state = core.acquire_lease(root, args.holder, args.timeout_seconds)
            else: core.release_lease(root, args.holder); state = {"released": True}
        elif args.command == "registry":
            state = core.registry_add(root,args.agent_id,args.parent_id,args.depth,args.scope) if args.registry_command=="add" else core.registry_update(root,args.agent_id,args.status) if args.registry_command=="update" else core.load_registry(root)
        elif args.command == "heartbeat": state=core.heartbeat_touch(root,args.agent_id) if args.heartbeat_command=="touch" else core.heartbeat_status(root,args.timeout_seconds)
        elif args.command == "health": state=core.record_agent_health(root,args.agent_id,args.outcome,args.failure_id,args.max_attempts,args.required) if args.health_command=="report" else core.reconcile_agent_health(root,args.timeout_seconds) if args.health_command=="reconcile" else core.agent_health_status(root)
        else:
            state=core.load(root)
            if args.command=="record-input-packet": core.record_input_packet(root,state,args.loop,args.artifact)
            elif args.command=="record-quality-gate": core.record_quality_gate(root,state,args.loop,args.analysis,args.judge,args.mediator)
            elif args.command=="run-quality-gate": core.run_quality_gate(root,state,args.loop,args.analysis_runner,args.judge_runner,args.mediator_runner)
            elif args.command=="complete-init": core.complete_init(root,state,args.input_packet,args.charter,args.design,args.roadmap)
            elif args.command=="complete-plan": core.complete_plan(root,state,args.input_packet,args.execution_plan,args.validation_matrix)
            elif args.command=="record-review-artifact": core.record_review_artifact(root,state,args.artifact)
            elif args.command=="record-remediation-packet": state["remediation_packet"] = core.record_remediation_packet(root,state,args.artifact)
            elif args.command=="record-execution-policy": core.record_execution_policy(root,state,args.artifact)
            elif args.command=="record-prompt-package": core.record_prompt_package(root,state,args.artifact)
            elif args.command=="record-run-report": core.record_run_report(root,state,args.artifact)
            elif args.command=="record-validation-receipt": core.record_validation_receipt(root,state,args.artifact)
            elif args.command=="record-stage-submission": core.record_stage_submission(root,state,args.artifact)
            elif args.command=="record-epistemic-ledger": core.record_epistemic_ledger(root,state,args.artifact)
            elif args.command=="record-trajectory-summary": core.record_trajectory_summary(root,state,args.artifact)
            elif args.command=="retrieve-trajectories": core.retrieve_trajectories(root,state,args.tag,args.limit)
            elif args.command=="plan": core.transition(state,"complete-init",args.evidence)
            elif args.command=="run": core.transition(state,"complete-plan",args.evidence)
            elif args.command=="review": core.complete_run(root,state,args.run_report)
            elif args.command=="review-complete": core.complete_review(root,state,args.artifact)
            elif args.command=="defer": core.defer(root,state,args.artifact)
            elif args.command=="replan": core.transition(state,"replan",args.evidence)
            elif args.command=="authorize-lifecycle": core.authorize_lifecycle(state,args.evidence)
            elif args.command=="resume": core.transition(state,"resume",args.evidence)
            elif args.command=="failure": core.record_failure(state,args.failed_command,args.failure_class,args.failure_id)
            elif args.command=="request-approval": core.approval_request(state,args.category,args.action,args.impact,args.alternatives,args.decision)
            elif args.command=="record-integration": core.record_integration(root,state,args.loop,args.name,args.status,args.artifact,args.detail)
            core.save(root,state)
        print(json.dumps(state, sort_keys=True)); return 0
    except core.PolicyError as error:
        # Several fail-closed operations deliberately mutate in-memory state before
        # rejecting the command (for example, recording a blocker/failure artifact).
        # Persist that evidence so an operator can inspect and authorize a resume.
        if state is not None and state.get("run_id"):
            core.save(root, state)
        print(str(error)); return 2


if __name__ == "__main__": raise SystemExit(main())
