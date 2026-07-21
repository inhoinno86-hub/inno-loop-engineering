#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from loop_engine import PolicyError, approval_request, initialize, load, record_failure, save, transition


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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init_input = init.add_mutually_exclusive_group(required=True)
    init_input.add_argument("--intent")
    init_input.add_argument("--intent-file")
    init.add_argument("--source-ref", default="inline")
    sub.add_parser("init-auto")
    for name in ("plan", "run", "review", "review-complete", "replan"):
        item = sub.add_parser(name); item.add_argument("--evidence", required=True)
    defer = sub.add_parser("defer")
    for field in ("impact", "rationale", "owner", "revisit-trigger"):
        defer.add_argument(f"--{field}", required=True)
    block = sub.add_parser("request-approval"); block.add_argument("--category", required=True); block.add_argument("--action", required=True); block.add_argument("--impact", required=True); block.add_argument("--alternatives", required=True); block.add_argument("--decision", required=True)
    failure = sub.add_parser("failure"); failure.add_argument("--failed-command", required=True); failure.add_argument("--failure-class", required=True); failure.add_argument("--failure-id", required=True)
    resume = sub.add_parser("resume"); resume.add_argument("--evidence", default="")
    status = sub.add_parser("status")
    args = parser.parse_args(argv); root = Path(args.project_root).resolve()
    try:
        if args.command == "init":
            if args.intent_file:
                intent, source_ref = intent_from_file(root, args.intent_file)
            else:
                intent, source_ref = args.intent, args.source_ref
            state = initialize(root, intent, source_ref)
        elif args.command == "init-auto":
            intent, source_ref = discover_intent(root)
            state = initialize(root, intent, source_ref)
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
            elif args.command == "resume": transition(state, "resume", args.evidence)
            if args.command != "status": save(root, state)
        print(json.dumps(state, sort_keys=True))
        return 0
    except PolicyError as error:
        print(str(error), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
