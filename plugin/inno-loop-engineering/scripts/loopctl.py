#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
from loop_engine import PolicyError, approval_request, authorize_lifecycle, initialize, load, record_failure, record_integration, save, transition


INTENT_FILENAMES = ("intent.md", "intend.md")


def intent_from_file(project_root, intent_file):
    path = Path(intent_file).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as error:
        raise PolicyError("intent file must be inside project root") from error
    if not path.is_file():
        raise PolicyError("intent file does not exist")
    try:
        return path.read_text(encoding="utf-8"), str(path.relative_to(project_root))
    except UnicodeDecodeError as error:
        raise PolicyError("intent file must be utf-8 text") from error


def discover_intent(project_root):
    candidates = [project_root / name for name in INTENT_FILENAMES if (project_root / name).is_file()]
    if not candidates:
        raise PolicyError("intent.md or intend.md does not exist")
    if len(candidates) > 1:
        raise PolicyError("ambiguous intent files: intent.md and intend.md")
    return intent_from_file(project_root, candidates[0])


def integration_evidence(project_root, args):
    if args.status != "USED":
        if not args.detail:
            raise PolicyError("failed integration detail required")
        return args.detail, None, None
    if not args.artifact:
        raise PolicyError("used integration artifact required")
    path = (project_root / args.artifact).resolve()
    try:
        relative = path.relative_to(project_root)
    except ValueError as error:
        raise PolicyError("integration artifact must be inside project root") from error
    if not path.is_file():
        raise PolicyError("integration artifact does not exist")
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{relative}#sha256={content_hash}", str(relative), content_hash


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init_input = init.add_mutually_exclusive_group(required=True)
    init_input.add_argument("--intent")
    init_input.add_argument("--intent-file")
    init.add_argument("--source-ref", default="inline")
    init.add_argument("--full-lifecycle", action="store_true")
    init.add_argument("--max-replans", type=int, default=3)
    init_auto = sub.add_parser("init-auto")
    init_auto.add_argument("--full-lifecycle", action="store_true")
    init_auto.add_argument("--max-replans", type=int, default=3)
    for name in ("plan", "run", "review", "review-complete", "replan"):
        item = sub.add_parser(name); item.add_argument("--evidence", required=True)
    defer = sub.add_parser("defer")
    for field in ("impact", "rationale", "owner", "revisit-trigger"):
        defer.add_argument(f"--{field}", required=True)
    block = sub.add_parser("request-approval"); block.add_argument("--category", required=True); block.add_argument("--action", required=True); block.add_argument("--impact", required=True); block.add_argument("--alternatives", required=True); block.add_argument("--decision", required=True)
    failure = sub.add_parser("failure"); failure.add_argument("--failed-command", required=True); failure.add_argument("--failure-class", required=True); failure.add_argument("--failure-id", required=True)
    integration = sub.add_parser("record-integration")
    integration.add_argument("--loop", required=True, choices=("project-init", "project-plan"))
    integration.add_argument("--name", required=True, choices=("ouroboros-interview", "superpowers-brainstorming", "superpowers-writing-plans"))
    integration.add_argument("--status", required=True, choices=("USED", "UNAVAILABLE", "FAILED"))
    integration.add_argument("--artifact")
    integration.add_argument("--detail")
    authorize = sub.add_parser("authorize-lifecycle"); authorize.add_argument("--evidence", required=True)
    resume = sub.add_parser("resume"); resume.add_argument("--evidence", default="")
    status = sub.add_parser("status")
    args = parser.parse_args(argv); root = Path(args.project_root).resolve(); state = None
    try:
        if args.command == "init":
            if args.intent_file:
                intent, source_ref = intent_from_file(root, args.intent_file)
            else:
                intent, source_ref = args.intent, args.source_ref
            state = initialize(root, intent, source_ref, args.full_lifecycle, args.max_replans)
        elif args.command == "init-auto":
            intent, source_ref = discover_intent(root)
            state = initialize(root, intent, source_ref, args.full_lifecycle, args.max_replans)
        else:
            state = load(root)
            if args.command == "plan": transition(state, "complete-init", args.evidence)
            elif args.command == "run": transition(state, "complete-plan", args.evidence)
            elif args.command == "review": transition(state, "complete-run", args.evidence)
            elif args.command == "review-complete": transition(state, "complete", args.evidence)
            elif args.command == "replan": transition(state, "replan", args.evidence)
            elif args.command == "defer": transition(state, "defer", backlog={"impact": args.impact, "rationale": args.rationale, "owner": args.owner, "revisit_trigger": args.revisit_trigger})
            elif args.command == "request-approval": approval_request(state, args.category, args.action, args.impact, args.alternatives, args.decision)
            elif args.command == "failure": record_failure(state, args.failed_command, args.failure_class, args.failure_id)
            elif args.command == "record-integration":
                evidence, artifact_ref, content_hash = integration_evidence(root, args)
                record_integration(state, args.loop, args.name, args.status, evidence, artifact_ref, content_hash)
            elif args.command == "authorize-lifecycle": authorize_lifecycle(state, args.evidence)
            elif args.command == "resume": transition(state, "resume", args.evidence)
            if args.command != "status": save(root, state)
        print(json.dumps(state, sort_keys=True))
        return 0
    except PolicyError as error:
        if state is not None and state.get("outcome") == "BLOCKED":
            save(root, state)
        print(str(error), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
