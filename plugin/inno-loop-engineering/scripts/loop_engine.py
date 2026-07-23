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
OUTCOMES = ("COMPLETE", "REPLAN", "BLOCKED", "DEFERRED_BACKLOG")
APPROVAL_CATEGORIES = (
    "external_irreversible", "security_privacy_secrets", "budget_limit_breach",
    "intent_or_core_architecture_change", "repeated_evaluation_failure",
)
STATE_RELATIVE = Path(".loop-engine/state.json")
MAX_INPUT_BYTES = 1_000_000


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
    return state


def save(project_root: Path, state: dict):
    state["updated_at"] = now()
    atomic_write(state_path(project_root), state)


def initialize(project_root: Path, intent: str, source_ref: str = "inline") -> dict:
    if state_path(project_root).exists():
        raise PolicyError("state already exists")
    record = input_record(intent, source_ref)
    state = {
        "schema_version": 1, "run_id": str(uuid.uuid4()), "current_loop": "project-init", "outcome": None,
        "input_hash": record["content_hash"], "input": record, "artifact_version": 1, "checkpoint": None,
        "decision_log": [], "assumption_log": [], "verification_evidence": [], "remediation_packet": None,
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
        state["current_loop"] = target
        add_evidence(state, event, evidence)
        return
    if event == "complete":
        if current != "project-review": raise PolicyError("only review can complete")
        state["outcome"] = "COMPLETE"; add_evidence(state, event, evidence); return
    if event == "replan":
        if current != "project-review": raise PolicyError("only review can replan")
        state["current_loop"] = "project-plan"; state["outcome"] = "REPLAN"; state["replan_count"] += 1
        state["remediation_packet"] = {"evidence": redact(evidence), "created_at": now()}; return
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
