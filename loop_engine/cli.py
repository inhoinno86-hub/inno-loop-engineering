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
    for name in ("plan", "run", "review", "review-complete", "replan"): sub.add_parser(name).add_argument("--evidence", required=True)
    packet=sub.add_parser("record-input-packet"); packet.add_argument("--loop", required=True); packet.add_argument("--artifact", required=True)
    quality=sub.add_parser("record-quality-gate"); quality.add_argument("--loop", required=True); quality.add_argument("--analysis", action="append", required=True); quality.add_argument("--judge", required=True); quality.add_argument("--mediator")
    run_quality=sub.add_parser("run-quality-gate"); run_quality.add_argument("--loop", required=True); run_quality.add_argument("--analysis-runner", required=True); run_quality.add_argument("--judge-runner", required=True); run_quality.add_argument("--mediator-runner")
    finish_init=sub.add_parser("complete-init"); finish_init.add_argument("--input-packet", required=True); finish_init.add_argument("--charter", required=True); finish_init.add_argument("--design", required=True); finish_init.add_argument("--roadmap", required=True)
    finish_plan=sub.add_parser("complete-plan"); finish_plan.add_argument("--input-packet", required=True); finish_plan.add_argument("--execution-plan", required=True); finish_plan.add_argument("--validation-matrix", required=True)
    review_artifact=sub.add_parser("record-review-artifact"); review_artifact.add_argument("--artifact", required=True)
    remediation=sub.add_parser("record-remediation-packet"); remediation.add_argument("--artifact", required=True)
    integ=sub.add_parser("record-integration"); integ.add_argument("--loop", required=True); integ.add_argument("--name", required=True); integ.add_argument("--status", required=True); integ.add_argument("--artifact"); integ.add_argument("--detail", default="")
    auth=sub.add_parser("authorize-lifecycle"); auth.add_argument("--evidence", required=True)
    fail=sub.add_parser("failure"); fail.add_argument("--failed-command", required=True); fail.add_argument("--failure-class", required=True); fail.add_argument("--failure-id", required=True)
    approval=sub.add_parser("request-approval"); [approval.add_argument(f"--{x}", required=True) for x in ("category", "action", "impact", "alternatives", "decision")]
    sub.add_parser("status")
    runs=sub.add_parser("runs"); runsub=runs.add_subparsers(dest="run_command", required=True); runsub.add_parser("list"); select=runsub.add_parser("select"); select.add_argument("--run-id", required=True); lease=runsub.add_parser("lease"); lease.add_argument("--holder", required=True); lease.add_argument("--timeout-seconds", type=int, default=300); release=runsub.add_parser("release-lease"); release.add_argument("--holder", required=True)
    registry=sub.add_parser("registry"); rsub=registry.add_subparsers(dest="registry_command", required=True); add=rsub.add_parser("add"); add.add_argument("--agent-id", required=True); add.add_argument("--parent-id"); add.add_argument("--depth", type=int, required=True); add.add_argument("--scope", required=True); update=rsub.add_parser("update"); update.add_argument("--agent-id", required=True); update.add_argument("--status", required=True); rsub.add_parser("list")
    heartbeat=sub.add_parser("heartbeat"); hsub=heartbeat.add_subparsers(dest="heartbeat_command", required=True); touch=hsub.add_parser("touch"); touch.add_argument("--agent-id", required=True); hstatus=hsub.add_parser("status"); hstatus.add_argument("--timeout-seconds", type=int, default=300)
    args=parser.parse_args(argv); root=Path(args.project_root).resolve()
    try:
        if args.command in ("init", "init-auto"):
            intent, source = _intent(root, args.intent_file); state=core.start_run(root, intent, source, args.full_lifecycle, args.max_replans, args.new_lifecycle)
        elif args.command == "status": state=core.load(root)
        elif args.command == "runs":
            if args.run_command == "list": state = {"runs": core.list_runs(root)}
            elif args.run_command == "select": state = core.select_run(root, args.run_id)
            elif args.run_command == "lease": state = core.acquire_lease(root, args.holder, args.timeout_seconds)
            else: core.release_lease(root, args.holder); state = {"released": True}
        elif args.command == "registry":
            state = core.registry_add(root,args.agent_id,args.parent_id,args.depth,args.scope) if args.registry_command=="add" else core.registry_update(root,args.agent_id,args.status) if args.registry_command=="update" else core.load_registry(root)
        elif args.command == "heartbeat": state=core.heartbeat_touch(root,args.agent_id) if args.heartbeat_command=="touch" else core.heartbeat_status(root,args.timeout_seconds)
        else:
            state=core.load(root)
            if args.command=="record-input-packet": core.record_input_packet(root,state,args.loop,args.artifact)
            elif args.command=="record-quality-gate": core.record_quality_gate(root,state,args.loop,args.analysis,args.judge,args.mediator)
            elif args.command=="run-quality-gate": core.run_quality_gate(root,state,args.loop,args.analysis_runner,args.judge_runner,args.mediator_runner)
            elif args.command=="complete-init": core.complete_init(root,state,args.input_packet,args.charter,args.design,args.roadmap)
            elif args.command=="complete-plan": core.complete_plan(root,state,args.input_packet,args.execution_plan,args.validation_matrix)
            elif args.command=="record-review-artifact": core.record_review_artifact(root,state,args.artifact)
            elif args.command=="record-remediation-packet": state["remediation_packet"] = core.record_remediation_packet(root,state,args.artifact)
            elif args.command=="plan": core.transition(state,"complete-init",args.evidence)
            elif args.command=="run": core.transition(state,"complete-plan",args.evidence)
            elif args.command=="review": core.transition(state,"complete-run",args.evidence)
            elif args.command=="review-complete": core.transition(state,"complete",args.evidence)
            elif args.command=="replan": core.transition(state,"replan",args.evidence)
            elif args.command=="authorize-lifecycle": core.authorize_lifecycle(state,args.evidence)
            elif args.command=="failure": core.record_failure(state,args.failed_command,args.failure_class,args.failure_id)
            elif args.command=="request-approval": core.approval_request(state,args.category,args.action,args.impact,args.alternatives,args.decision)
            elif args.command=="record-integration": core.record_integration(root,state,args.loop,args.name,args.status,args.artifact,args.detail)
            core.save(root,state)
        print(json.dumps(state, sort_keys=True)); return 0
    except core.PolicyError as error:
        print(str(error)); return 2


if __name__ == "__main__": raise SystemExit(main())
