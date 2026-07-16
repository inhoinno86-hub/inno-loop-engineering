#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

STATES = {"DRAFT", "CHARTER_APPROVED", "DESIGN_APPROVED", "ROADMAP_APPROVED", "PLAN_APPROVED", "PROMPTS_READY", "EXECUTING", "VERIFYING", "COMPLETE", "REWORK", "REPLAN", "BLOCKED"}
ALLOWED = {
    "DRAFT": {"CHARTER_APPROVED"}, "CHARTER_APPROVED": {"DESIGN_APPROVED"},
    "DESIGN_APPROVED": {"ROADMAP_APPROVED"}, "ROADMAP_APPROVED": {"PLAN_APPROVED"},
    "PLAN_APPROVED": {"PROMPTS_READY"}, "PROMPTS_READY": {"EXECUTING"},
    "EXECUTING": {"VERIFYING", "REWORK", "REPLAN", "BLOCKED"},
    "VERIFYING": {"COMPLETE", "REWORK", "REPLAN", "BLOCKED"},
    "REWORK": {"EXECUTING"}, "REPLAN": {"ROADMAP_APPROVED"},
    "BLOCKED": STATES, "COMPLETE": {"ROADMAP_APPROVED"},
}
REQUIRED_FIELDS = {"schema_version", "project_id", "state", "active_milestone", "active_plan", "superpowers_planning", "superpowers_execution", "iteration", "rework_count", "same_failure_count", "last_failure_fingerprint", "resume_state", "last_transition_at", "last_verified_at", "blocked_reason", "evidence_refs", "user_review_required"}
DOCS = {"CHARTER_APPROVED": "docs/project/CHARTER.md", "DESIGN_APPROVED": "docs/project/DESIGN.md", "ROADMAP_APPROVED": "docs/project/ROADMAP.md"}
PLAN_METADATA = ["## Planning Metadata", "Planning artifact:", "Planning mode:", "Superpowers planning:", "Superpowers execution:", "Superpowers brainstorming:", "Ouroboros interview:", "## Progress Log", "## Decision Log", "## Rollback Plan"]


def now():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def state_path(root):
    return root / ".project-loop" / "state.json"


def load_state(root):
    try:
        return json.loads(state_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid state file: {exc}") from exc


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def approved(path):
    return path.is_file() and "## Decision Log" in path.read_text(encoding="utf-8") and "APPROVED -" in path.read_text(encoding="utf-8")


def validate(root, state=None):
    errors = []
    state = state or load_state(root)
    missing = REQUIRED_FIELDS - set(state)
    if missing:
        errors.append("missing state fields: " + ", ".join(sorted(missing)))
    if state.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if state.get("state") not in STATES:
        errors.append("unknown state")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(state.get("project_id", ""))):
        errors.append("project_id must be lowercase kebab-case")
    for key in ("iteration", "rework_count", "same_failure_count"):
        if not isinstance(state.get(key), int) or state.get(key, -1) < 0:
            errors.append(f"{key} must be a nonnegative integer")
    current = state.get("state")
    ordered = ["CHARTER_APPROVED", "DESIGN_APPROVED", "ROADMAP_APPROVED"]
    if current in STATES:
        index = ordered.index(current) if current in ordered else (2 if current not in {"DRAFT"} else -1)
        for item in ordered[:index + 1]:
            path = root / DOCS[item]
            if not path.is_file():
                errors.append(f"missing required artifact: {DOCS[item]}")
    if current in {"PLAN_APPROVED", "PROMPTS_READY", "EXECUTING", "VERIFYING", "COMPLETE", "REWORK", "BLOCKED"}:
        plan = state.get("active_plan")
        if not plan or not (root / plan).is_file():
            errors.append("active_plan must reference an existing root plan")
        else:
            text = (root / plan).read_text(encoding="utf-8")
            for marker in PLAN_METADATA:
                if marker not in text:
                    errors.append(f"active plan missing: {marker}")
    if current in {"PROMPTS_READY", "EXECUTING", "VERIFYING", "COMPLETE", "REWORK", "BLOCKED"}:
        main = root / "to-do-prompts" / "main.md"
        if not main.is_file():
            errors.append("missing to-do-prompts/main.md")
        elif state.get("active_plan"):
            text = main.read_text(encoding="utf-8")
            plan_path = root / state["active_plan"]
            digest = hashlib.sha256(plan_path.read_bytes()).hexdigest() if plan_path.is_file() else ""
            if state["active_plan"] not in text or digest not in text:
                errors.append("prompt package lacks active plan path or current SHA-256")
    return errors


def normalize(value):
    value = re.sub(r"/tmp/[^\s]+", "/tmp/<path>", value or "")
    value = re.sub(r"\b\d{4}-\d{2}-\d{2}T[^\s]+", "<timestamp>", value)
    return re.sub(r"(?i)(token|password|secret|key)=\S+", r"\1=<redacted>", value).strip()


def transition(root, args):
    state = load_state(root)
    source, target = state["state"], args.to
    if target not in ALLOWED.get(source, set()):
        raise ValueError(f"illegal transition: {source} -> {target}")
    if source == "BLOCKED" and target != state.get("resume_state") and target != "ROADMAP_APPROVED":
        raise ValueError("blocked transition must use recorded resume_state")
    approval_targets = {"CHARTER_APPROVED", "DESIGN_APPROVED", "ROADMAP_APPROVED", "PLAN_APPROVED"}
    if target in approval_targets:
        if not args.approval_ref or not approved(root / args.approval_ref):
            raise ValueError("transition requires approval-ref with APPROVED Decision Log entry")
    if args.active_milestone is not None:
        state["active_milestone"] = args.active_milestone
    if args.active_plan is not None:
        if Path(args.active_plan).is_absolute() or Path(args.active_plan).parent != Path("."):
            raise ValueError("active plan must be a root-relative filename")
        state["active_plan"] = args.active_plan
    if args.superpowers_planning is not None:
        state["superpowers_planning"] = args.superpowers_planning
    if args.superpowers_execution is not None:
        state["superpowers_execution"] = args.superpowers_execution
    if target == "PLAN_APPROVED" and not state.get("active_plan"):
        raise ValueError("PLAN_APPROVED requires --active-plan")
    if target == "REWORK":
        state["rework_count"] += 1
        state["iteration"] += 1
        if args.failure_command or args.failure_class or args.failure_id:
            raw = "|".join(map(normalize, [args.failure_command, args.failure_class, args.failure_id]))
            fingerprint = hashlib.sha256(raw.encode()).hexdigest()
            state["same_failure_count"] = state["same_failure_count"] + 1 if fingerprint == state.get("last_failure_fingerprint") else 1
            state["last_failure_fingerprint"] = fingerprint
            if state["same_failure_count"] >= 3:
                target = "BLOCKED"
                state["resume_state"] = "REWORK"
                state["blocked_reason"] = "same normalized failure repeated three times"
        if state["rework_count"] >= 5:
            state["user_review_required"] = True
    if source == "REWORK" and target == "EXECUTING" and state.get("user_review_required"):
        if not args.approval_ref or not approved(root / args.approval_ref):
            raise ValueError("fifth rework requires user approval before execution")
        state["user_review_required"] = False
    if target == "REPLAN":
        prompts = root / "to-do-prompts"
        if prompts.exists() and any(prompts.iterdir()):
            raise ValueError("archive or remove prompt package before REPLAN")
        state["active_plan"] = None
    if target == "COMPLETE":
        refs = args.evidence_ref or []
        roadmap = root / "docs/project/ROADMAP.md"
        if not refs or any(not (root / ref).exists() for ref in refs):
            raise ValueError("COMPLETE requires existing evidence-ref values")
        if roadmap.is_file() and re.search(r"^- \[ \]", roadmap.read_text(encoding="utf-8"), re.M):
            raise ValueError("COMPLETE requires all Definition of Done checkboxes checked")
        state["evidence_refs"] = refs
        state["last_verified_at"] = now()
    if target == "BLOCKED" and not state.get("resume_state"):
        state["resume_state"] = args.resume_state or source
    if source == "BLOCKED" and target != "BLOCKED":
        state["blocked_reason"] = None
        state["resume_state"] = None
    state["state"] = target
    state["last_transition_at"] = now()
    errors = validate(root, state)
    if errors:
        raise ValueError("; ".join(errors))
    atomic_json(state_path(root), state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    check = subs.add_parser("validate")
    check.add_argument("--project-root", required=True)
    move = subs.add_parser("transition")
    move.add_argument("--project-root", required=True)
    move.add_argument("--to", required=True, choices=sorted(STATES))
    move.add_argument("--approval-ref")
    move.add_argument("--failure-command")
    move.add_argument("--failure-class")
    move.add_argument("--failure-id")
    move.add_argument("--evidence-ref", action="append")
    move.add_argument("--resume-state", choices=sorted(STATES))
    move.add_argument("--active-milestone")
    move.add_argument("--active-plan")
    move.add_argument("--superpowers-planning", choices=["enabled", "disabled"])
    move.add_argument("--superpowers-execution", choices=["enabled", "disabled"])
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "validate":
            errors = validate(root)
            if errors:
                raise ValueError("; ".join(errors))
            print("project-loop state valid")
        else:
            result = transition(root, args)
            print(json.dumps({"state": result["state"], "last_transition_at": result["last_transition_at"]}, sort_keys=True))
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
