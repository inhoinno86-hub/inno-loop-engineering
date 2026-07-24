#!/usr/bin/env python3
"""Deterministic, local-only state engine for inno-loop-engineering."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOOPS = ("project-init", "project-plan", "project-run", "project-review")
OUTCOMES = ("COMPLETE", "BLOCKED", "DEFERRED_BACKLOG")
APPROVAL_CATEGORIES = (
    "external_irreversible", "security_privacy_secrets", "budget_limit_breach",
    "intent_or_core_architecture_change", "repeated_evaluation_failure",
)
REQUIRED_INTEGRATIONS = (
    "ouroboros-interview", "superpowers-brainstorming", "superpowers-writing-plans",
)
INTEGRATION_STATUSES = ("USED", "UNAVAILABLE", "FAILED")
STATE_RELATIVE = Path(".inno-loop/state.json")
MAX_INPUT_BYTES = 1_000_000
DEFAULT_MAX_REPLANS = 3


class PolicyError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def redact(value: str) -> str:
    lowered = value.lower()
    return "[REDACTED]" if any(token in lowered for token in ("secret", "password", "token=", "api_key")) else value


def input_record(intent: str, source_ref: str = "inline") -> dict:
    encoded = intent.encode("utf-8")
    if not intent.strip():
        raise PolicyError("empty input")
    if len(encoded) > MAX_INPUT_BYTES:
        raise PolicyError("oversized input")
    return {"source_ref": source_ref, "content_hash": hashlib.sha256(encoded).hexdigest(), "media_type": "text/markdown", "size_bytes": len(encoded), "captured_at": now()}


def state_path(project_root: Path) -> Path:
    return project_root / STATE_RELATIVE


def load(project_root: Path) -> dict:
    path = state_path(project_root)
    if not path.exists():
        raise PolicyError("state does not exist")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1:
        raise PolicyError("unknown state schema")
    if state.get("outcome") == "REPLAN":
        state["outcome"] = None
        state["last_review_outcome"] = "REPLAN"
        if not state.get("replan_history") and state.get("remediation_packet"):
            state["replan_history"] = [state["remediation_packet"]]
        state["plan_iteration"] = max(state.get("plan_iteration", 1), state.get("replan_count", 0) + 1)
    state.setdefault("max_replans", DEFAULT_MAX_REPLANS)
    state.setdefault("replan_history", [])
    state.setdefault("last_review_outcome", None)
    state.setdefault("plan_iteration", 1)
    return state


def save(project_root: Path, state: dict):
    state["updated_at"] = now()
    atomic_write(state_path(project_root), state)


def initialize(project_root: Path, intent: str, source_ref: str = "inline", full_lifecycle: bool = False, max_replans: int = DEFAULT_MAX_REPLANS) -> dict:
    if state_path(project_root).exists():
        raise PolicyError("state already exists")
    record = input_record(intent, source_ref)
    if max_replans < 1:
        raise PolicyError("max replans must be positive")
    state = {
        "schema_version": 1, "run_id": str(uuid.uuid4()), "current_loop": "project-init", "outcome": None,
        "input_hash": record["content_hash"], "input": record, "artifact_version": 1, "checkpoint": None,
        "lifecycle_authorization": {"scope": "full-lifecycle", "evidence": "initial inno-loop invocation", "recorded_at": now()} if full_lifecycle else None,
        "last_review_outcome": None, "replan_history": [], "max_replans": max_replans, "plan_iteration": 1,
        "decision_log": [], "assumption_log": [], "verification_evidence": [], "integration_evidence": [], "remediation_packet": None,
        "backlog": [], "block": None, "failure_history": [], "replan_count": 0, "created_at": now(),
    }
    save(project_root, state)
    return state


def add_evidence(state: dict, kind: str, value: str):
    state["verification_evidence"].append({"kind": kind, "value": redact(value), "recorded_at": now()})


def block(state: dict, reason: str, requires_human: bool, evidence: str):
    state["outcome"] = "BLOCKED"
    state["block"] = {"reason": reason, "requires_human": requires_human, "evidence": redact(evidence), "recorded_at": now()}
    add_evidence(state, "block", evidence)


def approval_request(state: dict, category: str, action: str, impact: str, alternatives: str, requested_decision: str):
    if category not in APPROVAL_CATEGORIES:
        raise PolicyError("unknown approval category")
    request = {"category": category, "action": action, "impact": impact, "alternatives": alternatives, "requested_decision": requested_decision, "status": "PENDING"}
    block(state, category, True, json.dumps(request, sort_keys=True))
    state["approval_request"] = request


def authorize_lifecycle(state: dict, evidence: str):
    if not evidence:
        raise PolicyError("lifecycle authorization evidence required")
    state["lifecycle_authorization"] = {"scope": "full-lifecycle", "evidence": redact(evidence), "recorded_at": now()}
    add_evidence(state, "lifecycle-authorization", evidence)
    if state.get("outcome") == "BLOCKED" and (state.get("block") or {}).get("reason") == "full_lifecycle_authorization_required":
        state["outcome"] = None
        state["block"] = None
        add_evidence(state, "resume", evidence)


def lifecycle_authorized(state: dict):
    authorization = state.get("lifecycle_authorization") or {}
    if authorization.get("scope") == "full-lifecycle":
        return
    reason = "full lifecycle authorization required before project-run"
    block(state, "full_lifecycle_authorization_required", True, reason)
    raise PolicyError(reason)


def record_integration(state: dict, loop: str, name: str, status: str, evidence: str, artifact_ref: str | None = None, content_hash: str | None = None):
    if loop not in ("project-init", "project-plan"):
        raise PolicyError("integration loop is not supported")
    if loop != state.get("current_loop"):
        raise PolicyError("integration loop does not match current loop")
    if name not in REQUIRED_INTEGRATIONS:
        raise PolicyError("unknown required integration")
    if status not in INTEGRATION_STATUSES:
        raise PolicyError("unknown integration status")
    if not evidence:
        raise PolicyError("integration evidence required")
    if status == "USED" and (not artifact_ref or not content_hash):
        raise PolicyError("used integration requires artifact and content hash")
    iteration = state.get("plan_iteration", 1) if loop == "project-plan" else 1
    record = {"loop": loop, "iteration": iteration, "name": name, "status": status, "evidence": redact(evidence), "recorded_at": now()}
    if artifact_ref:
        record["artifact_ref"] = artifact_ref
    if content_hash:
        record["content_hash"] = content_hash
    state.setdefault("integration_evidence", []).append(record)
    add_evidence(state, "integration", json.dumps(record, sort_keys=True))
    if status != "USED":
        block(state, "required_integration_" + status.lower(), False, json.dumps(record, sort_keys=True))


def required_integrations_used(state: dict, loop: str):
    iteration = state.get("plan_iteration", 1) if loop == "project-plan" else 1
    used = {item["name"] for item in state.get("integration_evidence", []) if item["loop"] == loop and item.get("iteration", 1) == iteration and item["status"] == "USED"}
    missing = set(REQUIRED_INTEGRATIONS) - used
    if missing:
        reason = "required integrations missing: " + ", ".join(sorted(missing))
        block(state, "required_integrations_missing", False, reason)
        raise PolicyError(reason)


def transition(state: dict, event: str, evidence: str = "", backlog: dict | None = None):
    if state.get("outcome") == "BLOCKED" and event != "resume":
        raise PolicyError("blocked state requires resume")
    current = state.get("current_loop")
    if current not in LOOPS:
        raise PolicyError("illegal current loop")
    expected = {"complete-init": ("project-init", "project-plan"), "complete-plan": ("project-plan", "project-run"), "complete-run": ("project-run", "project-review")}
    if event in expected:
        source, target = expected[event]
        if current != source:
            raise PolicyError("illegal transition")
        if current in ("project-init", "project-plan"):
            required_integrations_used(state, current)
        if current == "project-plan":
            lifecycle_authorized(state)
        state["current_loop"] = target
        add_evidence(state, event, evidence)
        return
    if event == "complete":
        if current != "project-review": raise PolicyError("only review can complete")
        state["outcome"] = "COMPLETE"; add_evidence(state, event, evidence); return
    if event == "replan":
        if current != "project-review": raise PolicyError("only review can replan")
        next_count = state.get("replan_count", 0) + 1
        if next_count > state.get("max_replans", DEFAULT_MAX_REPLANS):
            block(state, "max_replans_exceeded", True, evidence)
            return
        packet = {"evidence": redact(evidence), "created_at": now(), "replan_count": next_count}
        state["current_loop"] = "project-plan"; state["outcome"] = None; state["last_review_outcome"] = "REPLAN"
        state["replan_count"] = next_count; state["plan_iteration"] = state.get("plan_iteration", 1) + 1
        state["remediation_packet"] = packet; state.setdefault("replan_history", []).append(packet); add_evidence(state, "replan", evidence); return
    if event == "defer":
        if current != "project-review" or not backlog: raise PolicyError("review backlog required")
        required = {"impact", "rationale", "owner", "revisit_trigger"}
        if not required.issubset(backlog): raise PolicyError("incomplete backlog")
        state["outcome"] = "DEFERRED_BACKLOG"; state["backlog"].append(backlog); return
    if event == "resume":
        if state.get("outcome") != "BLOCKED": raise PolicyError("not blocked")
        if state["block"].get("requires_human") and not evidence: raise PolicyError("approval evidence required")
        state["outcome"] = None; state["block"] = None; add_evidence(state, event, evidence); return
    raise PolicyError("unknown event")


def record_failure(state: dict, command: str, failure_class: str, failure_id: str):
    raw = "|".join((command, failure_class, failure_id))
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()
    history = state["failure_history"]
    history.append({"fingerprint": fingerprint, "recorded_at": now()})
    consecutive = 0
    for item in reversed(history):
        if item["fingerprint"] != fingerprint:
            break
        consecutive += 1
    if consecutive >= 3:
        block(state, "repeated_evaluation_failure", True, fingerprint)
    return fingerprint
