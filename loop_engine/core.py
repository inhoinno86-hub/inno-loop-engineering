"""Validated local lifecycle state, artifacts, migration, and agent registry."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

CANONICAL_DIR = Path(".loop-engine")
LEGACY_DIR = Path(".inno-loop")
STATE_NAME = "state.json"
RUNS_RELATIVE = CANONICAL_DIR / "runs"
POINTER_RELATIVE = CANONICAL_DIR / "current.json"
LOOPS = ("project-init", "project-plan", "project-run", "project-review")
REQUIRED_INTEGRATIONS = ("ouroboros-interview", "superpowers-brainstorming", "superpowers-writing-plans")
INTEGRATION_STATUSES = ("USED", "FAILED", "UNAVAILABLE")
APPROVAL_CATEGORIES = ("external_irreversible", "security_privacy_secrets", "budget_limit_breach", "intent_or_core_architecture_change", "repeated_evaluation_failure", "uncertain_risk")
MAX_INPUT_BYTES = 1_000_000
DEFAULT_MAX_REPLANS = 3
AGENT_STATUSES = ("active", "completed", "failed", "cancelled")
AGENT_HEALTH_OUTCOMES = ("healthy", "timeout", "failed", "unavailable", "completed", "quarantined")
CLAIM_CLASSIFICATIONS = ("known", "assumption", "known_unknown", "suspected_blind_spot")
CLAIM_STATUSES = ("active", "resolved", "invalidated", "superseded")
QUALITY_SECTIONS = ("requirements", "constraints", "non_goals", "risks", "acceptance_criteria", "ambiguities")
MATERIAL_CATEGORIES = ("security", "privacy", "irreversible_effect", "compliance", "budget", "core_architecture")
ASSESSMENT_VERDICTS = ("confirmed", "implementation_contract_needed", "human_decision_required", "contradictory")
OUTPUT_FIELDS = ("goal", "scope", "requirements", "non_goals", "assumptions", "risks", "safety_approval_policy", "success_criteria", "open_decisions")
RESULT_STATUSES = ("PASS", "FAIL", "BLOCKED", "INSUFFICIENT_EVIDENCE")
RECEIPT_STATUSES = ("PASS", "FAIL", "UNAVAILABLE", "TIMEOUT")
TERMINAL_OUTCOMES = ("COMPLETE", "DEFERRED_BACKLOG", "BLOCKED")


class PolicyError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _artifact_write(root: Path, state: dict, name: str, value: dict) -> str:
    """Atomically create one JSON evidence artifact below the active run root."""
    path = artifacts_path(root, state["run_id"]) / name
    atomic_write(path, value)
    return str(path.relative_to(root))


def redact(value: str) -> str:
    lowered = value.lower()
    return "[REDACTED]" if any(token in lowered for token in ("secret", "password", "token=", "api_key")) else value


def legacy_canonical_state_path(root: Path) -> Path:
    return root / CANONICAL_DIR / STATE_NAME


def legacy_state_path(root: Path) -> Path:
    return root / LEGACY_DIR / STATE_NAME


def run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise PolicyError("invalid run id")
    return root / RUNS_RELATIVE / run_id


def state_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / STATE_NAME


def artifacts_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / "artifacts"


def registry_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / "registry.json"


def pointer_path(root: Path) -> Path:
    return root / POINTER_RELATIVE


def _read_pointer(root: Path) -> str | None:
    path = pointer_path(root)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    run_id = data.get("run_id")
    if not run_id or not state_path(root, run_id).is_file():
        raise PolicyError("invalid current run pointer")
    return run_id


def _write_pointer(root: Path, run_id: str) -> None:
    atomic_write(pointer_path(root), {"run_id": run_id, "selected_at": now()})


def _migrate_single_state(root: Path) -> None:
    old = legacy_canonical_state_path(root)
    if not old.exists() or pointer_path(root).exists():
        return
    data = json.loads(old.read_text(encoding="utf-8")); _normalize(data)
    run_id = data.get("run_id") or str(uuid.uuid4()); data["run_id"] = run_id
    data["migration"] = {"source": str(CANONICAL_DIR / STATE_NAME), "migrated_at": now()}
    atomic_write(state_path(root, run_id), data)
    old_artifacts = root / CANONICAL_DIR / "artifacts"
    if old_artifacts.is_dir():
        shutil.copytree(old_artifacts, artifacts_path(root, run_id), dirs_exist_ok=True)
    backup = old.with_name(f"state.json.pre-runs-{now().replace(':', '-')}.bak")
    os.replace(old, backup); data["migration"]["backup"] = str(backup.relative_to(root))
    atomic_write(state_path(root, run_id), data); _write_pointer(root, run_id)


def _ensure_layout(root: Path) -> None:
    if legacy_state_path(root).exists() and pointer_path(root).exists():
        raise PolicyError("state path conflict: legacy state exists beside run layout")
    if legacy_state_path(root).exists() and legacy_canonical_state_path(root).exists():
        raise PolicyError("state path conflict: both .loop-engine/state.json and .inno-loop/state.json exist")
    if legacy_state_path(root).exists() and not legacy_canonical_state_path(root).exists() and not pointer_path(root).exists():
        data = _migrate_legacy(root)
        atomic_write(legacy_canonical_state_path(root), data)
    _migrate_single_state(root)


def _validate_root(root: Path) -> Path:
    return Path(root).resolve()


def _migrate_legacy(root: Path) -> dict:
    legacy = legacy_state_path(root)
    canonical = legacy_canonical_state_path(root)
    if canonical.exists() and legacy.exists():
        raise PolicyError("state path conflict: both .loop-engine/state.json and .inno-loop/state.json exist")
    if canonical.exists():
        return json.loads(canonical.read_text(encoding="utf-8"))
    if not legacy.exists():
        raise PolicyError("state does not exist")
    data = json.loads(legacy.read_text(encoding="utf-8"))
    backup = legacy.with_name(f"state.json.legacy-{now().replace(':', '-')}.bak")
    shutil.copy2(legacy, backup)
    data["migration"] = {"source": str(LEGACY_DIR / STATE_NAME), "backup": str(backup.relative_to(root)), "migrated_at": now()}
    _normalize(data)
    atomic_write(canonical, data)
    return data


def _normalize(state: dict) -> None:
    if state.get("schema_version") != 1:
        raise PolicyError("unknown state schema")
    if state.get("outcome") == "REPLAN":
        state["outcome"] = None
        state["last_review_outcome"] = "REPLAN"
        if state.get("remediation_packet") and not state.get("replan_history"):
            state["replan_history"] = [state["remediation_packet"]]
    state.setdefault("lifecycle_authorization", None)
    state.setdefault("integration_evidence", [])
    state.setdefault("integration_attempts", {})
    state.setdefault("last_review_outcome", None)
    state.setdefault("replan_history", [])
    state.setdefault("replan_count", 0)
    state.setdefault("max_replans", DEFAULT_MAX_REPLANS)
    state.setdefault("plan_iteration", max(1, state["replan_count"] + 1))
    state.setdefault("decision_a", None)
    state.setdefault("failure_history", [])
    state.setdefault("verification_evidence", [])
    state.setdefault("block", None)
    state.setdefault("input_packets", {})
    state.setdefault("quality_gates", {})
    state.setdefault("init_outputs", None)
    state.setdefault("plan_revisions", [])
    state.setdefault("review_artifact", None)
    state.setdefault("execution_policy", None)
    state.setdefault("prompt_package", None)
    state.setdefault("run_report", None)
    state.setdefault("validation_receipts", [])
    state.setdefault("review_input", None)
    state.setdefault("epistemic_ledgers", {})
    state.setdefault("trajectory_summaries", [])
    state.setdefault("trajectory_retrievals", [])
    state.setdefault("agent_health", {})
    state.setdefault("continuation_policy", {"mode": "automatic", "user_output": "terminal-or-hil-only"})
    state.setdefault("alerts", [])
    state.setdefault("worktree_baseline", None)
    state.setdefault("replan_policy", {"mode": "bounded", "max_replans": state.get("max_replans", DEFAULT_MAX_REPLANS)})
    state["artifact_version"] = max(int(state.get("artifact_version", 1)), 4)


def load(project_root: Path) -> dict:
    root = _validate_root(project_root)
    _ensure_layout(root)
    run_id = _read_pointer(root)
    if not run_id:
        raise PolicyError("state does not exist")
    state = json.loads(state_path(root, run_id).read_text(encoding="utf-8"))
    _normalize(state)
    return state


def save(project_root: Path, state: dict) -> None:
    root = _validate_root(project_root)
    _ensure_layout(root)
    state["updated_at"] = now()
    atomic_write(state_path(root, state["run_id"]), state)


def _input_record(intent: str, source_ref: str) -> dict:
    raw = intent.encode("utf-8")
    if not intent.strip():
        raise PolicyError("empty input")
    if len(raw) > MAX_INPUT_BYTES:
        raise PolicyError("oversized input")
    return {"source_ref": source_ref, "content_hash": hashlib.sha256(raw).hexdigest(), "media_type": "text/markdown", "size_bytes": len(raw), "captured_at": now()}


def initialize(project_root: Path, intent: str, source_ref: str = "inline", full_lifecycle: bool = False, max_replans: int = DEFAULT_MAX_REPLANS) -> dict:
    root = _validate_root(project_root)
    _ensure_layout(root)
    if max_replans < 1:
        raise PolicyError("max replans must be positive")
    record = _input_record(intent, source_ref)
    state = {"schema_version": 1, "run_id": str(uuid.uuid4()), "current_loop": "project-init", "outcome": None, "input_hash": record["content_hash"], "input": record, "artifact_version": 4, "checkpoint": None, "lifecycle_authorization": {"scope": "full-lifecycle", "evidence": "explicit inno-loop invocation", "recorded_at": now()} if full_lifecycle else None, "continuation_policy": {"mode": "automatic", "user_output": "terminal-or-hil-only"}, "alerts": [], "worktree_baseline": None, "replan_policy": {"mode": "bounded", "max_replans": max_replans}, "last_review_outcome": None, "replan_history": [], "max_replans": max_replans, "plan_iteration": 1, "decision_log": [], "assumption_log": [], "verification_evidence": [], "integration_evidence": [], "decision_a": None, "input_packets": {}, "quality_gates": {}, "init_outputs": None, "plan_revisions": [], "review_artifact": None, "execution_policy": None, "prompt_package": None, "run_report": None, "validation_receipts": [], "review_input": None, "epistemic_ledgers": {}, "trajectory_summaries": [], "trajectory_retrievals": [], "agent_health": {}, "remediation_packet": None, "backlog": [], "block": None, "failure_history": [], "replan_count": 0, "created_at": now()}
    save(root, state)
    _write_pointer(root, state["run_id"])
    return state


def list_runs(project_root: Path) -> list[dict]:
    root = _validate_root(project_root); _ensure_layout(root)
    runs = []
    base = root / RUNS_RELATIVE
    for path in sorted(base.glob(f"*/{STATE_NAME}")) if base.exists() else []:
        state = json.loads(path.read_text(encoding="utf-8")); _normalize(state)
        runs.append({"run_id": state["run_id"], "source_ref": state["input"]["source_ref"], "input_hash": state["input_hash"], "current_loop": state["current_loop"], "outcome": state["outcome"], "updated_at": state.get("updated_at")})
    return runs


def select_run(project_root: Path, run_id: str) -> dict:
    root = _validate_root(project_root); _ensure_layout(root)
    state = json.loads(state_path(root, run_id).read_text(encoding="utf-8")); _normalize(state)
    _write_pointer(root, run_id); return state


def start_run(project_root: Path, intent: str, source_ref: str, full_lifecycle: bool, max_replans: int, new_lifecycle: bool = False) -> dict:
    root = _validate_root(project_root); _ensure_layout(root)
    record = _input_record(intent, source_ref)
    runs = list_runs(root)
    active = [item for item in runs if item["outcome"] is None]
    same = [item for item in active if item["input_hash"] == record["content_hash"]]
    if same:
        return select_run(root, same[-1]["run_id"])
    if active and not new_lifecycle:
        raise PolicyError("different input has an active run; use --new-lifecycle")
    return initialize(root, intent, source_ref, full_lifecycle, max_replans)


def lease_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / "lease.json"


def acquire_lease(project_root: Path, holder: str, timeout_seconds: int = 300) -> dict:
    root = _validate_root(project_root); state = load(root); path = lease_path(root, state["run_id"])
    if not holder or timeout_seconds < 1: raise PolicyError("invalid lease request")
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8")); age = (datetime.now(timezone.utc) - datetime.fromisoformat(prior["heartbeat_at"])).total_seconds()
        if age <= timeout_seconds and prior.get("holder") != holder: raise PolicyError("run lease held by another holder")
    lease = {"run_id": state["run_id"], "holder": holder, "acquired_at": now(), "heartbeat_at": now(), "timeout_seconds": timeout_seconds}
    atomic_write(path, lease); return lease


def release_lease(project_root: Path, holder: str) -> None:
    root = _validate_root(project_root); state = load(root); path = lease_path(root, state["run_id"])
    if not path.exists(): return
    lease = json.loads(path.read_text(encoding="utf-8"))
    if lease.get("holder") != holder: raise PolicyError("run lease held by another holder")
    path.unlink()


def add_evidence(state: dict, kind: str, value: str) -> None:
    state.setdefault("verification_evidence", []).append({"kind": kind, "value": redact(value), "recorded_at": now()})


def block(state: dict, reason: str, requires_human: bool, evidence: str) -> None:
    state["outcome"] = "BLOCKED"
    state["block"] = {"reason": reason, "requires_human": requires_human, "evidence": redact(evidence), "recorded_at": now()}
    alert = {"alert_id": str(uuid.uuid4()), "kind": "hil-blocked" if requires_human else "terminal-blocked", "run_id": state.get("run_id"), "loop": state.get("current_loop"), "iteration": state.get("plan_iteration"), "reason": reason, "requires_human": requires_human, "evidence": redact(evidence), "created_at": now(), "delivery": "PENDING"}
    state.setdefault("alerts", []).append(alert)
    add_evidence(state, "block", evidence)


def pending_alerts(state: dict) -> list[dict]:
    reconcile_alerts(state)
    return [item for item in state.get("alerts", []) if item.get("delivery") == "PENDING"]


def reconcile_alerts(state: dict) -> None:
    """Backfill one alert for legacy BLOCKED states created before outbox support."""
    blocked = state.get("block")
    if state.get("outcome") != "BLOCKED" or not blocked:
        # Migration path: old resumes predate automatic outbox resolution.
        for event in state.get("verification_evidence", []):
            if event.get("kind") != "resume":
                continue
            try:
                resume = json.loads(event.get("value", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            prior = {"reason": resume.get("blocked_reason"), "evidence": resume.get("blocked_evidence")}
            if prior["reason"] and prior["evidence"]:
                resolve_alerts_for_block(state, prior, "reconciled from validated project-owner resume")
        return
    if any(item.get("reason") == blocked.get("reason") and item.get("evidence") == blocked.get("evidence") for item in state.get("alerts", [])):
        return
    state.setdefault("alerts", []).append({"alert_id": str(uuid.uuid4()), "kind": "hil-blocked" if blocked.get("requires_human") else "terminal-blocked", "run_id": state.get("run_id"), "loop": state.get("current_loop"), "iteration": state.get("plan_iteration"), "reason": blocked.get("reason"), "requires_human": bool(blocked.get("requires_human")), "evidence": blocked.get("evidence"), "created_at": now(), "delivery": "PENDING", "backfilled": True})


def acknowledge_alert(state: dict, alert_id: str, receipt: str) -> dict:
    if not alert_id or not receipt:
        raise PolicyError("alert id and delivery receipt are required")
    for alert in state.get("alerts", []):
        if alert["alert_id"] == alert_id:
            if alert.get("delivery") != "PENDING":
                raise PolicyError("alert already delivered")
            alert.update({"delivery": "DELIVERED", "delivery_receipt": redact(receipt), "delivered_at": now()})
            return alert
    raise PolicyError("unknown alert")


def resolve_alerts_for_block(state: dict, blocked: dict, resolution: str) -> int:
    """Close alerts for the exact block that a validated resume supersedes."""
    resolved = 0
    for alert in state.get("alerts", []):
        if (alert.get("delivery") == "PENDING" and alert.get("reason") == blocked.get("reason")
                and alert.get("evidence") == blocked.get("evidence")):
            alert.update({"delivery": "RESOLVED", "resolution": redact(resolution), "resolved_at": now()})
            resolved += 1
    return resolved


def capture_worktree_baseline(project_root: Path, state: dict) -> dict:
    root = _validate_root(project_root)
    if state.get("worktree_baseline"):
        return state["worktree_baseline"]
    result = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise PolicyError("cannot capture worktree baseline")
    paths = sorted(line[3:] for line in result.stdout.splitlines() if len(line) >= 4)
    state["worktree_baseline"] = {"captured_at": now(), "paths": paths, "content_hash": hashlib.sha256("\n".join(paths).encode()).hexdigest()}
    add_evidence(state, "worktree-baseline", json.dumps(state["worktree_baseline"], sort_keys=True))
    return state["worktree_baseline"]


def authorize_lifecycle(state: dict, evidence: str) -> None:
    if not evidence:
        raise PolicyError("lifecycle authorization evidence required")
    state["lifecycle_authorization"] = {"scope": "full-lifecycle", "evidence": redact(evidence), "recorded_at": now()}
    add_evidence(state, "lifecycle-authorization", evidence)


def approval_request(state: dict, category: str, action: str, impact: str, alternatives: str, requested_decision: str) -> None:
    if category not in APPROVAL_CATEGORIES:
        raise PolicyError("unknown approval category")
    request = {"category": category, "action": action, "impact": impact, "alternatives": alternatives, "requested_decision": requested_decision, "status": "PENDING"}
    state["approval_request"] = request
    block(state, category, True, json.dumps(request, sort_keys=True))


def _artifact(root: Path, run_id: str, ref: str) -> Path:
    if not ref or Path(ref).is_absolute():
        raise PolicyError("artifact path must be project-relative")
    root = _validate_root(root)
    path = (root / ref).resolve()
    allowed = artifacts_path(root, run_id).resolve()
    try:
        path.relative_to(allowed)
    except ValueError as error:
        raise PolicyError("artifact must be below active run artifacts") from error
    if not path.is_file() or path.is_symlink():
        raise PolicyError("artifact must be a regular file")
    return path


def _json_artifact(root: Path, state: dict, ref: str) -> tuple[dict, dict]:
    """Read a canonical JSON artifact and return its immutable descriptor."""
    path = _artifact(root, state["run_id"], ref)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyError("artifact must contain a JSON object") from error
    if not isinstance(value, dict):
        raise PolicyError("artifact must contain a JSON object")
    return value, {"artifact_ref": str(path.relative_to(root)), "content_hash": hashlib.sha256(path.read_bytes()).hexdigest()}


def _fields(value: dict, names: tuple[str, ...], label: str) -> None:
    missing = [name for name in names if name not in value]
    if missing:
        raise PolicyError(f"{label} missing fields: {', '.join(missing)}")


def _packet_key(loop: str, iteration: int) -> str:
    return f"{loop}:{iteration}"


def _expected_packet(state: dict, loop: str) -> tuple[int, str]:
    if loop == "project-init":
        return 0, state["input_hash"]
    if loop == "project-plan":
        return state["plan_iteration"], ""
    raise PolicyError("unknown input packet loop")


def record_input_packet(project_root: Path, state: dict, loop: str, artifact_ref: str) -> dict:
    """Record the immutable input packet for the active init or plan iteration."""
    root = _validate_root(project_root)
    if loop != state.get("current_loop") or loop not in ("project-init", "project-plan"):
        raise PolicyError("input packet loop does not match current loop")
    packet, descriptor = _json_artifact(root, state, artifact_ref)
    iteration, expected_input = _expected_packet(state, loop)
    _fields(packet, ("loop", "iteration", "input_hash", "source_artifacts", "repository_context"), "input packet")
    if packet["loop"] != loop or packet["iteration"] != iteration or not isinstance(packet["source_artifacts"], list) or not isinstance(packet["repository_context"], list):
        raise PolicyError("input packet loop or iteration mismatch")
    if loop == "project-init":
        if packet["input_hash"] != expected_input:
            raise PolicyError("init input packet hash mismatch")
    else:
        init = state.get("init_outputs")
        if not init:
            raise PolicyError("plan input requires accepted init outputs")
        expected = {item["content_hash"] for item in init["artifacts"]} | {init["quality_gate_hash"]}
        actual = {item.get("content_hash") for item in packet["source_artifacts"] if isinstance(item, dict)}
        if not expected.issubset(actual):
            raise PolicyError("plan input packet omits accepted init artifact hashes")
        if state["plan_iteration"] > 1:
            remediation = state.get("remediation_packet")
            if not remediation or packet.get("remediation_packet_hash") != remediation["content_hash"]:
                raise PolicyError("replan input packet remediation mismatch")
            expected.update({remediation["content_hash"], state["plan_revisions"][-1]["execution_plan"]["content_hash"], (state.get("review_artifact") or {}).get("content_hash")})
            if not expected.issubset(actual):
                raise PolicyError("replan input packet omits remediation lineage hashes")
    canonical = packet.get("canonical_requirements")
    if canonical is not None:
        if not isinstance(canonical, list) or not canonical:
            raise PolicyError("canonical requirements must be a nonempty list")
        ids = set()
        for item in canonical:
            if not isinstance(item, dict): raise PolicyError("invalid canonical requirement")
            _fields(item, ("id", "statement", "material", "category", "source_refs"), "canonical requirement")
            if not isinstance(item["id"], str) or not item["id"] or item["id"] in ids or not isinstance(item["statement"], str) or not item["statement"].strip() or not isinstance(item["material"], bool) or not isinstance(item["category"], str) or not isinstance(item["source_refs"], list) or not item["source_refs"]:
                raise PolicyError("invalid canonical requirement fields")
            ids.add(item["id"])
    record = {**descriptor, "loop": loop, "iteration": iteration, "input_hash": packet["input_hash"], "canonical_requirement_ids": [item["id"] for item in canonical] if canonical else []}
    state["input_packets"][_packet_key(loop, iteration)] = record
    add_evidence(state, "input-packet", json.dumps(record, sort_keys=True))
    return record


def _ledger_key(state: dict) -> str:
    loop = state.get("current_loop")
    if loop not in LOOPS:
        raise PolicyError("unknown lifecycle loop")
    return _packet_key(loop, 0 if loop == "project-init" else state["plan_iteration"])


def _ledger_claims(root: Path, state: dict, key: str | None = None) -> dict[str, dict]:
    record = state.get("epistemic_ledgers", {}).get(key or _ledger_key(state))
    if not record:
        return {}
    value, descriptor = _json_artifact(root, state, record["artifact_ref"])
    if descriptor["content_hash"] != record["content_hash"]:
        raise PolicyError("epistemic ledger hash mismatch")
    return {item["claim_id"]: item for item in value["claims"]}


def record_epistemic_ledger(project_root: Path, state: dict, artifact_ref: str) -> dict:
    """Record an immutable, evidence-first claim ledger for the active loop."""
    root = _validate_root(project_root); key = _ledger_key(state)
    value, descriptor = _json_artifact(root, state, artifact_ref)
    iteration = 0 if state["current_loop"] == "project-init" else state["plan_iteration"]
    _fields(value, ("loop", "iteration", "claims"), "epistemic ledger")
    if value["loop"] != state["current_loop"] or value["iteration"] != iteration or not isinstance(value["claims"], list):
        raise PolicyError("epistemic ledger loop or iteration mismatch")
    ids = set()
    for claim in value["claims"]:
        if not isinstance(claim, dict): raise PolicyError("invalid epistemic claim")
        _fields(claim, ("claim_id", "statement", "classification", "status", "source_artifacts", "confidence", "impact", "owner", "resolution_method", "linked_task_ids", "linked_criterion_ids"), "epistemic claim")
        if (not isinstance(claim["claim_id"], str) or not claim["claim_id"] or claim["claim_id"] in ids
                or not isinstance(claim["statement"], str) or not claim["statement"].strip()
                or claim["classification"] not in CLAIM_CLASSIFICATIONS or claim["status"] not in CLAIM_STATUSES
                or not isinstance(claim["confidence"], (int, float)) or not 0 <= float(claim["confidence"]) <= 1
                or claim["impact"] not in ("low", "medium", "high")
                or not isinstance(claim["owner"], str) or not claim["owner"].strip()
                or not isinstance(claim["resolution_method"], str) or not claim["resolution_method"].strip()
                or not isinstance(claim["linked_task_ids"], list) or not isinstance(claim["linked_criterion_ids"], list)
                or not all(isinstance(item, str) and item for item in claim["linked_task_ids"] + claim["linked_criterion_ids"])
                or not isinstance(claim["source_artifacts"], list)):
            raise PolicyError("invalid epistemic claim fields")
        if claim["classification"] == "known" and claim["status"] == "active" and not claim["source_artifacts"]:
            raise PolicyError("active known claim requires source evidence")
        for source in claim["source_artifacts"]:
            if not isinstance(source, dict): raise PolicyError("invalid claim source")
            _fields(source, ("artifact_ref", "content_hash"), "claim source")
            _, actual = _json_artifact(root, state, source["artifact_ref"])
            if actual["content_hash"] != source["content_hash"]: raise PolicyError("claim source hash mismatch")
        ids.add(claim["claim_id"])
    record = {**descriptor, "loop": state["current_loop"], "iteration": iteration, "claim_count": len(value["claims"])}
    state["epistemic_ledgers"][key] = record
    add_evidence(state, "epistemic-ledger", json.dumps(record, sort_keys=True))
    return record


def _validate_plan_claim_contract(root: Path, state: dict, plan: dict, task_ids: set[str], criterion_ids: set[str]) -> None:
    key = _packet_key("project-plan", state["plan_iteration"])
    claims = _ledger_claims(root, state, key)
    if not claims:
        return
    if plan.get("epistemic_ledger_hash") != state["epistemic_ledgers"][key]["content_hash"]:
        raise PolicyError("execution plan epistemic ledger binding mismatch")
    for claim in claims.values():
        if claim["impact"] == "high" and claim["classification"] in ("known_unknown", "suspected_blind_spot") and claim["status"] == "active":
            if not set(claim["linked_task_ids"]).issubset(task_ids) or not set(claim["linked_criterion_ids"]).issubset(criterion_ids) or not claim["linked_task_ids"] or not claim["linked_criterion_ids"]:
                raise PolicyError("high-impact unknown must map to a plan task and criterion")
    for task in plan["tasks"]:
        _fields(task, ("precondition_claim_ids", "effect_claims", "failure_effects"), "epistemic task contract")
        if not all(isinstance(item, str) and item in claims for item in task["precondition_claim_ids"]):
            raise PolicyError("task precondition claim is unknown")
        for claim_id in task["precondition_claim_ids"]:
            claim = claims[claim_id]
            if claim["status"] != "active" or claim["classification"] not in ("known", "assumption"):
                raise PolicyError("task precondition is not satisfied")
        for field in ("effect_claims", "failure_effects"):
            if not isinstance(task[field], list) or not all(isinstance(item, str) and item in claims for item in task[field]):
                raise PolicyError("task effect claim is unknown")


def record_quality_gate(project_root: Path, state: dict, loop: str, analysis_refs: list[str], judge_ref: str, mediator_ref: str | None = None) -> dict:
    """Validate and persist the evidence-only Socrates-3 judge decision."""
    root = _validate_root(project_root)
    if loop != state.get("current_loop") or loop not in ("project-init", "project-plan"):
        raise PolicyError("quality gate loop does not match current loop")
    iteration, _ = _expected_packet(state, loop)
    packet = state["input_packets"].get(_packet_key(loop, iteration))
    if not packet:
        raise PolicyError("quality gate requires current input packet")
    if len(analysis_refs) != 3 or len(set(analysis_refs)) != 3:
        raise PolicyError("quality gate requires three distinct analyses")
    packet_value, _ = _json_artifact(root, state, packet["artifact_ref"])
    canonical = packet_value.get("canonical_requirements") or []
    canonical_by_id = {item["id"]: item for item in canonical}
    analyses = []
    identities = set()
    for ref in analysis_refs:
        analysis, descriptor = _json_artifact(root, state, ref)
        _fields(analysis, ("tool", "run_id", "invocation_id", "input_packet_hash", "timestamp", "cited_input_hashes", "sibling_output_hashes", *QUALITY_SECTIONS), "analysis")
        if analysis["input_packet_hash"] != packet["content_hash"] or packet["input_hash"] not in analysis["cited_input_hashes"]:
            raise PolicyError("analysis input packet hash mismatch")
        if not isinstance(analysis["tool"], str) or not analysis["tool"] or not isinstance(analysis["invocation_id"], str) or not analysis["invocation_id"] or not isinstance(analysis["timestamp"], str) or not isinstance(analysis["cited_input_hashes"], list) or analysis["sibling_output_hashes"] != []:
            raise PolicyError("analysis identity or independence record is invalid")
        if not isinstance(analysis["run_id"], str) or not analysis["run_id"] or analysis["run_id"] in identities:
            raise PolicyError("analysis run identities must be distinct")
        if any(not isinstance(analysis[name], list) for name in QUALITY_SECTIONS):
            raise PolicyError("analysis sections must be lists")
        if canonical:
            assessments = analysis.get("assessments")
            if not isinstance(assessments, list) or {item.get("requirement_id") for item in assessments if isinstance(item, dict)} != set(canonical_by_id):
                raise PolicyError("analysis must assess every canonical requirement")
            for item in assessments:
                if not isinstance(item, dict): raise PolicyError("invalid requirement assessment")
                _fields(item, ("requirement_id", "verdict", "evidence_refs"), "requirement assessment")
                if item["verdict"] not in ASSESSMENT_VERDICTS or not isinstance(item["evidence_refs"], list):
                    raise PolicyError("invalid requirement assessment verdict")
        identities.add(analysis["run_id"]); analyses.append({**descriptor, "run_id": analysis["run_id"], "tool": analysis["tool"]})
    judge, judge_descriptor = _json_artifact(root, state, judge_ref)
    _fields(judge, ("tool", "run_id", "invocation_id", "timestamp", "input_packet_hash", "analysis_hashes", "requirement_matrix", "consistency_score", "material_contradictions"), "judge")
    if judge["input_packet_hash"] != packet["content_hash"] or set(judge["analysis_hashes"]) != {item["content_hash"] for item in analyses}:
        raise PolicyError("judge analysis or input packet mismatch")
    matrix = judge["requirement_matrix"]
    if not isinstance(matrix, list) or not matrix:
        raise PolicyError("judge requirement matrix is required")
    if canonical and {item.get("id") for item in matrix if isinstance(item, dict)} != set(canonical_by_id):
        raise PolicyError("judge matrix must cover every canonical requirement")
    total = unanimous = 0.0; material_ids = set(); material_differences = set(); critical = set(); human_decisions = set()
    for item in matrix:
        if not isinstance(item, dict): raise PolicyError("invalid requirement matrix entry")
        _fields(item, ("id", "weight", "classification", "material", "category"), "requirement matrix entry")
        if item["classification"] not in ("unanimous", "two-of-three", "unique", "contradictory") or not isinstance(item["weight"], (int, float)) or item["weight"] <= 0:
            raise PolicyError("invalid requirement matrix classification or weight")
        if canonical:
            source = canonical_by_id.get(item["id"])
            if not source or item["material"] != source["material"] or item["category"] != source["category"]:
                raise PolicyError("judge matrix must bind canonical requirements")
            _fields(item, ("resolution", "evidence_refs"), "canonical requirement matrix entry")
            if item["resolution"] not in ASSESSMENT_VERDICTS or not isinstance(item["evidence_refs"], list):
                raise PolicyError("invalid canonical requirement resolution")
            if item["resolution"] == "human_decision_required": human_decisions.add(item["id"])
        if item["material"]:
            material_ids.add(item["id"]); total += item["weight"]
            if item["classification"] == "unanimous": unanimous += item["weight"]
            else: material_differences.add(item["id"])
        if item["classification"] == "contradictory" and item["category"] in MATERIAL_CATEGORIES:
            critical.add(item["id"])
    if not total:
        raise PolicyError("judge matrix requires material requirements")
    score = round(unanimous / total * 100, 6)
    if abs(float(judge["consistency_score"]) - score) > 0.000001:
        raise PolicyError("judge consistency score does not match matrix")
    contradictory_ids = {item["id"] for item in matrix if item["classification"] == "contradictory" and item["material"]}
    if not isinstance(judge["material_contradictions"], list) or not set(judge["material_contradictions"]).issubset(contradictory_ids):
        raise PolicyError("invalid material contradictions")
    critical.update(judge["material_contradictions"])
    mediator = None
    if not canonical and 50 <= score <= 80 and not critical:
        if not mediator_ref:
            block(state, "quality_gate_mediator_required", True, judge_descriptor["artifact_ref"])
            raise PolicyError("mediator is required for 50..80 score")
        value, descriptor = _json_artifact(root, state, mediator_ref)
        _fields(value, ("tool", "run_id", "invocation_id", "timestamp", "input_packet_hash", "judge_hash", "resolved_requirement_ids", "unresolved_requirement_ids"), "mediator")
        if value["input_packet_hash"] != packet["content_hash"] or value["judge_hash"] != judge_descriptor["content_hash"]:
            raise PolicyError("mediator binding mismatch")
        if set(value["unresolved_requirement_ids"]) or not material_differences.issubset(set(value["resolved_requirement_ids"])):
            block(state, "quality_gate_mediator_unresolved", True, descriptor["artifact_ref"])
            raise PolicyError("mediator did not resolve every material difference")
        mediator = descriptor
    semantic_ready = bool(canonical) and not critical and not human_decisions and all(item.get("resolution") != "contradictory" for item in matrix)
    accepted = semantic_ready or (not canonical and (score > 80 and not critical or (50 <= score <= 80 and mediator is not None)))
    record = {"loop": loop, "iteration": iteration, "input_packet_hash": packet["content_hash"], "analyses": analyses, "judge": judge_descriptor, "mediator": mediator, "consistency_score": score, "material_contradictions": sorted(critical), "human_decision_requirement_ids": sorted(human_decisions), "accepted": accepted}
    state["quality_gates"][_packet_key(loop, iteration)] = record
    add_evidence(state, "quality-gate", json.dumps(record, sort_keys=True))
    if (not canonical and score < 50) or critical or human_decisions:
        block(state, "quality_gate_unresolved", True, json.dumps(record, sort_keys=True))
    return record


def _runner_json(command: str, payload: dict) -> dict:
    """Run one local JSON runner without a shell or sibling-output access."""
    try:
        completed = subprocess.run(
            shlex.split(command), input=json.dumps(payload, sort_keys=True), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=60,
        )
        value = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as error:
        raise PolicyError(f"quality runner failed: {redact(str(error))}") from error
    if not isinstance(value, dict):
        raise PolicyError("quality runner must emit a JSON object")
    return value


def _quality_failure(root: Path, state: dict, loop: str, stage: str, detail: str) -> dict:
    iteration, _ = _expected_packet(state, loop)
    ref = _artifact_write(root, state, f"{loop}/iteration-{iteration}/quality-{stage}-failure.json", {
        "loop": loop, "iteration": iteration, "stage": stage,
        "status": "FAILED", "timestamp": now(), "detail": redact(detail),
    })
    evidence = {"artifact_ref": ref, "stage": stage, "status": "FAILED"}
    block(state, "quality_gate_runner_failed", False, json.dumps(evidence, sort_keys=True))
    return evidence


def run_quality_gate(project_root: Path, state: dict, loop: str, analysis_runner: str,
                     judge_runner: str, mediator_runner: str | None = None) -> dict:
    """Execute Socrates-3 runners and persist every output before judging it.

    Runners are local executables receiving one JSON object on stdin and emitting
    one JSON object on stdout. They are deliberately dependency-free adapters:
    callers choose any approved model/tool outside this package. No runner or
    runner failure is a fail-closed lifecycle block, never a synthetic verdict.
    """
    root = _validate_root(project_root)
    if loop != state.get("current_loop") or loop not in ("project-init", "project-plan"):
        raise PolicyError("quality gate loop does not match current loop")
    if not analysis_runner or not judge_runner:
        _quality_failure(root, state, loop, "configuration", "analysis and judge runners are required")
        raise PolicyError("analysis and judge runners are required")
    iteration, _ = _expected_packet(state, loop)
    packet = state["input_packets"].get(_packet_key(loop, iteration))
    if not packet:
        raise PolicyError("quality gate requires current input packet")
    try:
        packet_value, _ = _json_artifact(root, state, packet["artifact_ref"])
        analysis_refs = []
        analysis_hashes = []
        analysis_values = []
        for role in ("socratic-requirements", "socratic-risk", "socratic-adversarial"):
            run_id = str(uuid.uuid4())
            output = _runner_json(analysis_runner, {
                "stage": "analysis", "role": role, "analysis_scope": "canonical_requirement_assessment", "run_id": run_id,
                "input_packet": packet_value, "input_packet_hash": packet["content_hash"],
            })
            _fields(output, QUALITY_SECTIONS, "analysis runner output")
            value = {
                **output, "tool": shlex.split(analysis_runner)[0], "run_id": run_id,
                "invocation_id": str(uuid.uuid4()), "input_packet_hash": packet["content_hash"],
                "timestamp": now(), "cited_input_hashes": [packet["input_hash"]],
                "sibling_output_hashes": [], "role": role,
            }
            ref = _artifact_write(root, state, f"{loop}/iteration-{iteration}/socratic-{role}-{run_id}.json", value)
            analysis_refs.append(ref)
            analysis_hashes.append(_json_artifact(root, state, ref)[1]["content_hash"])
            analysis_values.append(value)
        judged = _runner_json(judge_runner, {
            "stage": "judge", "input_packet": packet_value, "input_packet_hash": packet["content_hash"],
            "analysis_hashes": analysis_hashes, "analyses": analysis_values,
        })
        _fields(judged, ("requirement_matrix", "material_contradictions"), "judge runner output")
        matrix = judged["requirement_matrix"]
        if not isinstance(matrix, list):
            raise PolicyError("judge requirement matrix must be a list")
        total = sum(item["weight"] for item in matrix if isinstance(item, dict) and item.get("material") and isinstance(item.get("weight"), (int, float)))
        unanimous = sum(item["weight"] for item in matrix if isinstance(item, dict) and item.get("material") and item.get("classification") == "unanimous" and isinstance(item.get("weight"), (int, float)))
        if not total:
            raise PolicyError("judge matrix requires material requirements")
        judge = {
            **judged, "tool": shlex.split(judge_runner)[0], "run_id": str(uuid.uuid4()),
            "invocation_id": str(uuid.uuid4()), "timestamp": now(),
            "input_packet_hash": packet["content_hash"], "analysis_hashes": analysis_hashes,
            "consistency_score": round(unanimous / total * 100, 6),
        }
        judge_ref = _artifact_write(root, state, f"{loop}/iteration-{iteration}/judge-{judge['run_id']}.json", judge)
        critical = any(isinstance(item, dict) and item.get("classification") == "contradictory" and item.get("category") in MATERIAL_CATEGORIES for item in matrix)
        mediator_ref = None
        score = judge["consistency_score"]
        if 50 <= score <= 80 and not critical:
            if not mediator_runner:
                raise PolicyError("mediator runner is required for 50..80 score")
            mediator_output = _runner_json(mediator_runner, {
                "stage": "mediator", "input_packet": packet_value, "input_packet_hash": packet["content_hash"],
                "judge_hash": _json_artifact(root, state, judge_ref)[1]["content_hash"],
                "requirement_matrix": matrix,
            })
            _fields(mediator_output, ("resolved_requirement_ids", "unresolved_requirement_ids"), "mediator runner output")
            mediator = {
                **mediator_output, "tool": shlex.split(mediator_runner)[0], "run_id": str(uuid.uuid4()),
                "invocation_id": str(uuid.uuid4()), "timestamp": now(),
                "input_packet_hash": packet["content_hash"],
                "judge_hash": _json_artifact(root, state, judge_ref)[1]["content_hash"],
            }
            mediator_ref = _artifact_write(root, state, f"{loop}/iteration-{iteration}/mediator-{mediator['run_id']}.json", mediator)
        return record_quality_gate(root, state, loop, analysis_refs, judge_ref, mediator_ref)
    except PolicyError as error:
        if state.get("outcome") != "BLOCKED":
            _quality_failure(root, state, loop, "execution", str(error))
        raise


def _output_artifact(root: Path, state: dict, ref: str, packet_hash: str, gate_hash: str) -> dict:
    value, descriptor = _json_artifact(root, state, ref)
    _fields(value, ("input_packet_hash", "quality_gate_hash", *OUTPUT_FIELDS), "lifecycle output")
    if value["input_packet_hash"] != packet_hash or value["quality_gate_hash"] != gate_hash:
        raise PolicyError("lifecycle output binding mismatch")
    return descriptor


def complete_init(project_root: Path, state: dict, packet_ref: str, charter_ref: str, design_ref: str, roadmap_ref: str) -> None:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-init": raise PolicyError("illegal transition")
    packet = state["input_packets"].get(_packet_key("project-init", 0)); gate = state["quality_gates"].get(_packet_key("project-init", 0))
    if not packet or packet["artifact_ref"] != packet_ref or not gate or not gate["accepted"]:
        raise PolicyError("accepted init packet and quality gate are required")
    artifacts = [_output_artifact(root, state, ref, packet["content_hash"], gate["judge"]["content_hash"]) for ref in (charter_ref, design_ref, roadmap_ref)]
    state["init_outputs"] = {"input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "artifacts": artifacts}
    transition(state, "complete-init", ",".join(item["artifact_ref"] for item in artifacts))


def complete_plan(project_root: Path, state: dict, packet_ref: str, plan_ref: str, matrix_ref: str) -> None:
    root = _validate_root(project_root); iteration = state.get("plan_iteration")
    if state.get("current_loop") != "project-plan": raise PolicyError("illegal transition")
    packet = state["input_packets"].get(_packet_key("project-plan", iteration)); gate = state["quality_gates"].get(_packet_key("project-plan", iteration))
    if not packet or packet["artifact_ref"] != packet_ref or not gate or not gate["accepted"]:
        raise PolicyError("accepted plan packet and quality gate are required")
    plan, plan_descriptor = _json_artifact(root, state, plan_ref); matrix, matrix_descriptor = _json_artifact(root, state, matrix_ref)
    for value, label in ((plan, "execution plan"), (matrix, "validation matrix")):
        _fields(value, ("input_packet_hash", "quality_gate_hash", "plan_iteration"), label)
        if value["input_packet_hash"] != packet["content_hash"] or value["quality_gate_hash"] != gate["judge"]["content_hash"] or value["plan_iteration"] != iteration:
            raise PolicyError(f"{label} binding mismatch")
    if not isinstance(plan.get("tasks"), list) or not plan["tasks"]: raise PolicyError("execution plan tasks are required")
    if not isinstance(matrix.get("validations"), list) or not matrix["validations"] or not isinstance(matrix.get("criteria"), list) or not matrix["criteria"]:
        raise PolicyError("validation matrix criteria and validations are required")
    validation_ids = set(); required_validation_ids = set()
    for validation in matrix["validations"]:
        if not isinstance(validation, dict): raise PolicyError("invalid validation entry")
        _fields(validation, ("validation_id", "required", "procedure"), "validation entry")
        if not isinstance(validation["validation_id"], str) or not validation["validation_id"] or validation["validation_id"] in validation_ids or not isinstance(validation["required"], bool) or not isinstance(validation["procedure"], str) or not validation["procedure"].strip():
            raise PolicyError("invalid validation id or required flag")
        validation_ids.add(validation["validation_id"])
        if validation["required"]: required_validation_ids.add(validation["validation_id"])
    criterion_ids = set()
    for criterion in matrix["criteria"]:
        if not isinstance(criterion, dict): raise PolicyError("invalid criterion entry")
        _fields(criterion, ("criterion_id", "weight", "mandatory", "critical", "validation_ids"), "criterion entry")
        if not isinstance(criterion["criterion_id"], str) or not criterion["criterion_id"] or criterion["criterion_id"] in criterion_ids or not isinstance(criterion["weight"], (int, float)) or criterion["weight"] <= 0 or not isinstance(criterion["mandatory"], bool) or not isinstance(criterion["critical"], bool) or not isinstance(criterion["validation_ids"], list) or not criterion["validation_ids"] or not set(criterion["validation_ids"]).issubset(validation_ids):
            raise PolicyError("invalid criterion mapping")
        criterion_ids.add(criterion["criterion_id"])
    task_ids = set(); mapped_criteria = set(); mapped_validations = set()
    task_dependencies: dict[str, list[str]] = {}
    expected_prior_revision = state["plan_revisions"][-1]["execution_plan"]["content_hash"] if state["plan_revisions"] else None
    for task in plan["tasks"]:
        if not isinstance(task, dict): raise PolicyError("invalid execution plan task")
        _fields(task, ("task_id", "scope", "owner", "dependencies", "definition_of_done", "validation", "rollback", "source_input_hash", "source_plan_revision_hash", "criterion_ids", "validation_ids"), "execution plan task")
        if not isinstance(task["task_id"], str) or not task["task_id"] or task["task_id"] in task_ids or not all(isinstance(task[field], str) and task[field].strip() for field in ("scope", "owner", "definition_of_done", "validation", "rollback")) or not isinstance(task["dependencies"], list) or not all(isinstance(item, str) and item for item in task["dependencies"]) or task["task_id"] in task["dependencies"] or task["source_input_hash"] != packet["content_hash"] or task["source_plan_revision_hash"] != expected_prior_revision or not isinstance(task["criterion_ids"], list) or not task["criterion_ids"] or not set(task["criterion_ids"]).issubset(criterion_ids) or not isinstance(task["validation_ids"], list) or not task["validation_ids"] or not set(task["validation_ids"]).issubset(validation_ids):
            raise PolicyError("invalid task mapping")
        task_ids.add(task["task_id"]); task_dependencies[task["task_id"]] = task["dependencies"]
        mapped_criteria.update(task["criterion_ids"]); mapped_validations.update(task["validation_ids"])
    if any(not set(dependencies).issubset(task_ids) for dependencies in task_dependencies.values()):
        raise PolicyError("task dependency must reference an active plan task")
    if criterion_ids != mapped_criteria or not required_validation_ids.issubset(mapped_validations):
        raise PolicyError("plan omits criterion or required validation mapping")
    _validate_plan_claim_contract(root, state, plan, task_ids, criterion_ids)
    revision = {"iteration": iteration, "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "execution_plan": plan_descriptor, "validation_matrix": matrix_descriptor}
    state["plan_revisions"].append(revision)
    transition(state, "complete-plan", plan_descriptor["artifact_ref"])


def _active_revision(state: dict) -> dict:
    if not state.get("plan_revisions") or state["plan_revisions"][-1]["iteration"] != state.get("plan_iteration"):
        raise PolicyError("current plan revision is required")
    return state["plan_revisions"][-1]


def _bound_artifact(root: Path, state: dict, artifact_ref: str, fields: tuple[str, ...], label: str) -> tuple[dict, dict, dict]:
    value, descriptor = _json_artifact(root, state, artifact_ref)
    revision = _active_revision(state)
    _fields(value, ("plan_revision_hash", "validation_matrix_hash", *fields), label)
    if value["plan_revision_hash"] != revision["execution_plan"]["content_hash"] or value["validation_matrix_hash"] != revision["validation_matrix"]["content_hash"]:
        raise PolicyError(f"{label} plan binding mismatch")
    return value, descriptor, revision


def record_execution_policy(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-run": raise PolicyError("execution policy loop does not match current loop")
    value, descriptor, _ = _bound_artifact(root, state, artifact_ref, ("superpowers_execution", "task_policies", "coordinator_id"), "execution policy")
    if not isinstance(value["superpowers_execution"], bool) or not isinstance(value["task_policies"], list) or not isinstance(value["coordinator_id"], str) or not value["coordinator_id"]:
        raise PolicyError("invalid execution policy")
    plan, _ = _json_artifact(root, state, _active_revision(state)["execution_plan"]["artifact_ref"])
    expected = {task["task_id"] for task in plan["tasks"]}
    seen = set()
    for policy in value["task_policies"]:
        if not isinstance(policy, dict):
            raise PolicyError("invalid task execution policy")
        _fields(policy, ("task_id", "topology", "write_scope", "limits", "safety_constraints", "execution_mode", "rationale", "observed_result_refs"), "task execution policy")
        task_id = policy["task_id"]
        if (not isinstance(task_id, str) or task_id in seen or task_id not in expected
                or not all(isinstance(policy[field], str) and policy[field].strip() for field in ("topology", "rationale"))
                or not isinstance(policy["write_scope"], list) or not policy["write_scope"] or not all(isinstance(item, str) and item for item in policy["write_scope"])
                or not isinstance(policy["limits"], dict) or not policy["limits"]
                or not isinstance(policy["safety_constraints"], list) or not policy["safety_constraints"] or not all(isinstance(item, str) and item for item in policy["safety_constraints"])
                or policy["execution_mode"] not in ("normal-codex", "superpowers")
                or not isinstance(policy["observed_result_refs"], list) or not policy["observed_result_refs"] or not all(isinstance(item, str) and item for item in policy["observed_result_refs"])):
            raise PolicyError("invalid task execution policy mapping")
        if (policy["execution_mode"] == "superpowers") != value["superpowers_execution"]:
            raise PolicyError("task execution mode does not match policy opt-in")
        seen.add(task_id)
    if seen != expected:
        raise PolicyError("execution policy must map every active task exactly once")
    state["execution_policy"] = descriptor; add_evidence(state, "execution-policy", json.dumps(descriptor, sort_keys=True)); return descriptor


def record_prompt_package(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-run" or not state.get("execution_policy"): raise PolicyError("prompt package requires execution policy")
    value, descriptor, _ = _bound_artifact(root, state, artifact_ref, ("execution_policy_hash", "steps"), "prompt package")
    if value["execution_policy_hash"] != state["execution_policy"]["content_hash"] or not isinstance(value["steps"], list) or not value["steps"]:
        raise PolicyError("invalid prompt package")
    revision = _active_revision(state); plan, _ = _json_artifact(root, state, revision["execution_plan"]["artifact_ref"]); matrix, _ = _json_artifact(root, state, revision["validation_matrix"]["artifact_ref"])
    task_ids = {item["task_id"] for item in plan["tasks"]}; criterion_ids = {item["criterion_id"] for item in matrix["criteria"]}; validation_ids = {item["validation_id"] for item in matrix["validations"]}; required_validation_ids = {item["validation_id"] for item in matrix["validations"] if item["required"]}
    step_ids = set(); covered_tasks = set(); covered_criteria = set(); covered_validations = set()
    for step in value["steps"]:
        if not isinstance(step, dict): raise PolicyError("invalid prompt step")
        _fields(step, ("step_id", "task_ids", "criterion_ids", "validation_ids", "completion_checks", "task_policy_ids"), "prompt step")
        if not isinstance(step["step_id"], str) or not step["step_id"] or step["step_id"] in step_ids or not isinstance(step["task_ids"], list) or not step["task_ids"] or not all(isinstance(v, list) for v in (step["criterion_ids"], step["validation_ids"], step["completion_checks"], step["task_policy_ids"])) or set(step["task_ids"]) != set(step["task_policy_ids"]): raise PolicyError("invalid prompt step mapping")
        if not set(step["task_ids"]).issubset(task_ids) or not set(step["criterion_ids"]).issubset(criterion_ids) or not set(step["validation_ids"]).issubset(validation_ids): raise PolicyError("unknown prompt step mapping")
        step_ids.add(step["step_id"])
        covered_tasks.update(step["task_ids"]); covered_criteria.update(step["criterion_ids"]); covered_validations.update(step["validation_ids"])
    if covered_tasks != task_ids or covered_criteria != criterion_ids or not required_validation_ids.issubset(covered_validations): raise PolicyError("prompt package omits active plan coverage")
    state["prompt_package"] = descriptor; add_evidence(state, "prompt-package", json.dumps(descriptor, sort_keys=True)); return descriptor


def record_validation_receipt(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-run" or not state.get("prompt_package"): raise PolicyError("validation receipt requires prompt package")
    value, descriptor, _ = _bound_artifact(root, state, artifact_ref, ("prompt_package_hash", "validation_id", "status", "command", "exit_code"), "validation receipt")
    matrix, _ = _json_artifact(root, state, _active_revision(state)["validation_matrix"]["artifact_ref"])
    revision = _active_revision(state)
    state["validation_receipts"] = [
        item for item in state["validation_receipts"]
        if _json_artifact(root, state, item["artifact_ref"])[0].get("plan_revision_hash") == revision["execution_plan"]["content_hash"]
    ]
    known = {item["validation_id"] for item in matrix["validations"]}
    if value["prompt_package_hash"] != state["prompt_package"]["content_hash"] or value["status"] not in RECEIPT_STATUSES or not isinstance(value["validation_id"], str) or value["validation_id"] not in known or not isinstance(value["command"], str) or not value["command"].strip() or not isinstance(value["exit_code"], int) or value["status"] == "PASS" and value["exit_code"] != 0: raise PolicyError("invalid validation receipt")
    for field in ("executor_id", "invocation_id", "timestamp", "evidence_refs"):
        if field not in value:
            raise PolicyError("validation receipt provenance is required")
        valid = isinstance(value[field], str) and bool(value[field].strip()) if field != "evidence_refs" else isinstance(value[field], list) and bool(value[field]) and all(isinstance(ref, str) and ref for ref in value[field])
        if not valid:
            raise PolicyError("invalid validation receipt provenance")
    if any(item.get("validation_id") == value["validation_id"] for item in state["validation_receipts"]): raise PolicyError("validation receipt already recorded")
    record = {**descriptor, "validation_id": value["validation_id"], "status": value["status"]}
    state["validation_receipts"].append(record); add_evidence(state, "validation-receipt", json.dumps(record, sort_keys=True)); return record


def record_run_report(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-run" or not state.get("prompt_package"): raise PolicyError("run report requires prompt package")
    value, descriptor, _ = _bound_artifact(root, state, artifact_ref, ("prompt_package_hash", "task_results", "executor_ids", "changed_files"), "run report")
    if value["prompt_package_hash"] != state["prompt_package"]["content_hash"] or not isinstance(value["task_results"], list) or not isinstance(value["executor_ids"], list) or not value["executor_ids"] or not all(isinstance(item, str) and item for item in value["executor_ids"]) or len(set(value["executor_ids"])) != len(value["executor_ids"]) or not isinstance(value["changed_files"], list) or not all(isinstance(item, str) and item for item in value["changed_files"]): raise PolicyError("invalid run report")
    for result in value["task_results"]:
        if not isinstance(result, dict) or set(result) != {"task_id", "status", "evidence_refs", "executor_id", "invocation_id", "timestamp"} or not isinstance(result["task_id"], str) or result["status"] not in RESULT_STATUSES or not isinstance(result["executor_id"], str) or result["executor_id"] not in value["executor_ids"] or not all(isinstance(result[field], str) and result[field].strip() for field in ("invocation_id", "timestamp")) or not isinstance(result["evidence_refs"], list) or not result["evidence_refs"] or not all(isinstance(ref, str) and ref for ref in result["evidence_refs"]):
            raise PolicyError("invalid task result provenance")
    if "execution_policy_hash" in value and value["execution_policy_hash"] != state["execution_policy"]["content_hash"]:
        raise PolicyError("run report execution policy binding mismatch")
    if "prompt_package_hashes" in value and value["prompt_package_hashes"] != [state["prompt_package"]["content_hash"]]:
        raise PolicyError("run report prompt provenance mismatch")
    state["run_report"] = descriptor; add_evidence(state, "run-report", json.dumps(descriptor, sort_keys=True)); return descriptor


def complete_run(project_root: Path, state: dict, report_ref: str) -> None:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-run" or not state.get("run_report") or state["run_report"]["artifact_ref"] != report_ref: raise PolicyError("current run report is required")
    report, _, revision = _bound_artifact(root, state, report_ref, ("prompt_package_hash", "task_results", "executor_ids", "changed_files"), "run report")
    if not state.get("prompt_package") or report["prompt_package_hash"] != state["prompt_package"]["content_hash"]: raise PolicyError("run report prompt binding mismatch")
    plan, _ = _json_artifact(root, state, revision["execution_plan"]["artifact_ref"])
    task_results = report["task_results"]
    if any(not isinstance(item, dict) or set(item) != {"task_id", "status", "evidence_refs", "executor_id", "invocation_id", "timestamp"} or not isinstance(item.get("task_id"), str) or item.get("status") not in RESULT_STATUSES or not isinstance(item.get("executor_id"), str) or item["executor_id"] not in report["executor_ids"] or not isinstance(item.get("evidence_refs"), list) or not item["evidence_refs"] or not all(isinstance(ref, str) and ref for ref in item["evidence_refs"]) or not all(isinstance(item.get(field), str) and item[field].strip() for field in ("invocation_id", "timestamp")) for item in task_results):
        raise PolicyError("invalid task result")
    result_ids = [item["task_id"] for item in task_results]
    if len(result_ids) != len(set(result_ids)):
        raise PolicyError("duplicate task result")
    completed = {item["task_id"] for item in task_results if item["status"] == "PASS"}
    required_tasks = {item["task_id"] for item in plan["tasks"]}
    if set(result_ids) != required_tasks or not required_tasks.issubset(completed): raise PolicyError("run report omits completed plan tasks")
    matrix, _ = _json_artifact(root, state, revision["validation_matrix"]["artifact_ref"])
    required_validations = {item["validation_id"] for item in matrix["validations"] if item["required"]}
    receipt_status = {item["validation_id"]: item["status"] for item in state["validation_receipts"]}
    if any(receipt_status.get(item) != "PASS" for item in required_validations): raise PolicyError("run report omits passing required validation receipts")
    state["current_loop"] = "project-review"; add_evidence(state, "complete-run", report_ref)


def record_remediation_packet(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review" or not state.get("plan_revisions"):
        raise PolicyError("remediation packet requires a reviewed plan")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    fields = ("failed_acceptance_criteria", "failure_evidence", "plan_vs_actual", "root_cause_or_uncertainty", "required_correction", "risk", "non_deferrable", "prior_plan_revision_hash", "review_artifact_hash")
    _fields(value, fields, "remediation packet")
    prior = state["plan_revisions"][-1]["execution_plan"]["content_hash"]
    review = (state.get("review_artifact") or {}).get("content_hash")
    if not isinstance(value["failed_acceptance_criteria"], list) or not value["failed_acceptance_criteria"] or not isinstance(value["failure_evidence"], list) or not value["failure_evidence"] or not isinstance(value["plan_vs_actual"], list) or not value["plan_vs_actual"] or not all(isinstance(item, str) and item for item in value["failed_acceptance_criteria"] + value["failure_evidence"] + value["plan_vs_actual"]) or not isinstance(value["non_deferrable"], bool) or not value["non_deferrable"] or value["prior_plan_revision_hash"] != prior or value["review_artifact_hash"] != review:
        raise PolicyError("remediation packet lineage or non-deferrable status mismatch")
    return {**descriptor, "packet": value}


def record_review_artifact(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review":
        raise PolicyError("review artifact loop does not match current loop")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    _fields(value, ("plan_revision_hash", "validation_matrix_hash", "prompt_package_hash", "run_report_hash", "acceptance_results", "reviewer_ids"), "review artifact")
    revision = _active_revision(state)
    if value["plan_revision_hash"] != revision["execution_plan"]["content_hash"] or value["validation_matrix_hash"] != revision["validation_matrix"]["content_hash"]:
        raise PolicyError("review artifact plan revision mismatch")
    if not state.get("prompt_package") or value["prompt_package_hash"] != state["prompt_package"]["content_hash"] or not state.get("run_report") or value["run_report_hash"] != state["run_report"]["content_hash"]:
        raise PolicyError("review artifact run lineage mismatch")
    if not isinstance(value["acceptance_results"], list) or not isinstance(value["reviewer_ids"], list) or not value["reviewer_ids"]:
        raise PolicyError("review artifact results and reviewers are required")
    report, _ = _json_artifact(root, state, state["run_report"]["artifact_ref"])
    if set(value["reviewer_ids"]) & set(report["executor_ids"]): raise PolicyError("reviewers must be independent from executors")
    matrix, _ = _json_artifact(root, state, revision["validation_matrix"]["artifact_ref"])
    expected = {item["criterion_id"] for item in matrix["criteria"]}
    actual = set()
    for result in value["acceptance_results"]:
        if not isinstance(result, dict): raise PolicyError("invalid acceptance result")
        _fields(result, ("criterion_id", "verdict", "evidence_refs", "confidence"), "acceptance result")
        if result["criterion_id"] in actual or result["criterion_id"] not in expected or result["verdict"] not in RESULT_STATUSES or not isinstance(result["evidence_refs"], list) or not result["evidence_refs"] or not all(isinstance(ref, str) and ref for ref in result["evidence_refs"]) or not isinstance(result["confidence"], (int, float)) or not 0 <= float(result["confidence"]) <= 1: raise PolicyError("invalid acceptance result mapping")
        actual.add(result["criterion_id"])
    if actual != expected: raise PolicyError("review artifact omits criterion results")
    state["review_artifact"] = descriptor
    add_evidence(state, "review-artifact", json.dumps(descriptor, sort_keys=True))
    return descriptor


def complete_review(project_root: Path, state: dict, artifact_ref: str) -> None:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review" or not state.get("review_artifact") or state["review_artifact"]["artifact_ref"] != artifact_ref:
        raise PolicyError("current review artifact is required")
    review, _ = _json_artifact(root, state, artifact_ref); revision = _active_revision(state)
    matrix, _ = _json_artifact(root, state, revision["validation_matrix"]["artifact_ref"])
    verdicts = {item["criterion_id"]: item["verdict"] for item in review["acceptance_results"]}
    mandatory = {item["criterion_id"] for item in matrix["criteria"] if item["mandatory"] or item["critical"]}
    if any(verdicts[item] != "PASS" for item in mandatory): raise PolicyError("mandatory or critical review criteria are not all PASS")
    required = {item["validation_id"] for item in matrix["validations"] if item["required"]}
    receipt_status = {item["validation_id"]: item["status"] for item in state["validation_receipts"]}
    if any(receipt_status.get(item) != "PASS" for item in required): raise PolicyError("required validations are not all PASS")
    transition(state, "complete", artifact_ref)


def defer(project_root: Path, state: dict, artifact_ref: str) -> None:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review" or not state.get("review_artifact"): raise PolicyError("defer requires review artifact")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    _fields(value, ("impact", "rationale", "owner", "revisit_trigger", "evidence_refs", "criterion_ids"), "backlog item")
    matrix, _ = _json_artifact(root, state, _active_revision(state)["validation_matrix"]["artifact_ref"])
    protected = {item["criterion_id"] for item in matrix["criteria"] if item["mandatory"] or item["critical"]}
    reviewed = {item["criterion_id"]: item["verdict"] for item in _json_artifact(root, state, state["review_artifact"]["artifact_ref"])[0]["acceptance_results"]}
    if not isinstance(value["criterion_ids"], list) or not value["criterion_ids"] or not set(value["criterion_ids"]).issubset(reviewed) or set(value["criterion_ids"]) & protected: raise PolicyError("mandatory or critical finding cannot be deferred")
    if any(reviewed[item] == "PASS" for item in value["criterion_ids"]): raise PolicyError("passing finding cannot be deferred")
    state["backlog"].append({**descriptor, "item": value}); state["outcome"] = "DEFERRED_BACKLOG"; add_evidence(state, "defer", descriptor["artifact_ref"])


def record_integration(project_root: Path, state: dict, loop: str, name: str, status: str, artifact_ref: str | None = None, detail: str = "") -> None:
    root = _validate_root(project_root)
    if loop not in ("project-init", "project-plan") or loop != state.get("current_loop"):
        raise PolicyError("integration loop does not match current loop")
    if name not in REQUIRED_INTEGRATIONS or status not in INTEGRATION_STATUSES:
        raise PolicyError("unknown integration name or status")
    iteration = 0 if loop == "project-init" else state["plan_iteration"]
    attempt = _integration_attempt(state, loop, iteration)
    prior = [r for r in state["integration_evidence"] if r["loop"] == loop and r["iteration"] == iteration and r.get("attempt", 0) == attempt]
    expected = REQUIRED_INTEGRATIONS[len(prior)] if len(prior) < len(REQUIRED_INTEGRATIONS) else None
    if status == "USED" and name != expected:
        raise PolicyError("integration evidence must use required order")
    record = {"loop": loop, "iteration": iteration, "attempt": attempt, "name": name, "status": status, "recorded_at": now()}
    if status == "USED":
        path = _artifact(root, state["run_id"], artifact_ref or "")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if any(r.get("artifact_ref") == str(path.relative_to(root)) for r in state["integration_evidence"]):
            raise PolicyError("integration artifact may not be reused")
        record.update({"artifact_ref": str(path.relative_to(root)), "content_hash": digest})
    elif not detail:
        raise PolicyError("failed integration detail required")
    else:
        record["detail"] = redact(detail)
    state["integration_evidence"].append(record)
    add_evidence(state, "integration", json.dumps(record, sort_keys=True))
    if status != "USED":
        block(state, "required_integration_" + status.lower(), False, json.dumps(record, sort_keys=True))


def _required_integrations(state: dict, loop: str) -> None:
    iteration = 0 if loop == "project-init" else state["plan_iteration"]
    attempt = _integration_attempt(state, loop, iteration)
    records = [r for r in state["integration_evidence"] if r["loop"] == loop and r["iteration"] == iteration and r.get("attempt", 0) == attempt]
    if [r["name"] for r in records] != list(REQUIRED_INTEGRATIONS) or any(r["status"] != "USED" for r in records):
        block(state, "required_integrations_missing", False, f"{loop}:{iteration}")
        raise PolicyError("required ordered integration evidence missing")


def _integration_attempt(state: dict, loop: str, iteration: int) -> int:
    """Select the active, auditable attempt for one planning integration set."""
    key = f"{loop}:{iteration}"
    requested = state.get("integration_attempts", {}).get(key)
    records = [r for r in state.get("integration_evidence", []) if r["loop"] == loop and r["iteration"] == iteration]
    if requested is not None:
        return int(requested)
    attempts = [int(r.get("attempt", 0)) for r in records]
    current = max(attempts, default=0)
    current_records = [r for r in records if int(r.get("attempt", 0)) == current]
    # A prior failed attempt can be retried only after `resume` cleared BLOCKED.
    # The old evidence remains immutable and the retry is explicitly numbered.
    if current_records and any(r["status"] != "USED" for r in current_records) and state.get("outcome") is None:
        current += 1
        state.setdefault("integration_attempts", {})[key] = current
    return current


def record_decision_a(state: dict, analysis_refs: list[str], score: float, score_ref: str, mediator_ref: str | None = None, resolved: bool = False) -> None:
    if len(analysis_refs) != 3 or len(set(analysis_refs)) != 3:
        raise PolicyError("Decision A requires three independent analyses")
    if not 0 <= score <= 100:
        raise PolicyError("consistency score must be 0..100")
    state["decision_a"] = {"analyses": analysis_refs, "score": score, "score_ref": score_ref, "mediator_ref": mediator_ref, "resolved": resolved, "recorded_at": now()}
    if score < 50 or (score <= 80 and not (mediator_ref and resolved)):
        block(state, "decision_a_unresolved", True, json.dumps(state["decision_a"], sort_keys=True))


def transition(state: dict, event: str, evidence: str = "", backlog: dict | None = None) -> None:
    if state.get("outcome") == "BLOCKED" and event != "resume":
        raise PolicyError("blocked state requires resume")
    current = state.get("current_loop")
    if event in {"complete-init", "complete-plan"}:
        expected = {"complete-init": ("project-init", "project-plan"), "complete-plan": ("project-plan", "project-run")}[event]
        if current != expected[0]:
            raise PolicyError("illegal transition")
        if current == "project-init" and not state.get("init_outputs"):
            raise PolicyError("validated init outputs are required")
        if current == "project-plan" and (not state.get("plan_revisions") or state["plan_revisions"][-1].get("iteration") != state.get("plan_iteration")):
            raise PolicyError("validated current plan revision is required")
        if current in ("project-init", "project-plan"):
            _required_integrations(state, current)
        if current == "project-plan" and (state.get("lifecycle_authorization") or {}).get("scope") != "full-lifecycle":
            block(state, "full_lifecycle_authorization_required", True, evidence)
            raise PolicyError("full lifecycle authorization required before project-run")
        state["current_loop"] = expected[1]; add_evidence(state, event, evidence); return
    if event == "complete-run":
        raise PolicyError("complete-run requires validated run report")
    if event == "complete":
        if current != "project-review": raise PolicyError("only review can complete")
        if not state.get("review_artifact") or state["review_artifact"].get("artifact_ref") != evidence:
            raise PolicyError("validated review artifact is required")
        state["outcome"] = "COMPLETE"; add_evidence(state, event, evidence); return
    if event == "replan":
        if current != "project-review": raise PolicyError("only review can replan")
        if state.get("replan_policy", {}).get("mode") != "owner-unlimited" and state["replan_count"] >= state["max_replans"]:
            block(state, "max_replans_exceeded", True, evidence); return
        packet = state.get("remediation_packet")
        if not packet or packet.get("artifact_ref") != evidence:
            raise PolicyError("structured remediation packet is required")
        state["replan_count"] += 1; state["plan_iteration"] += 1; state["last_review_outcome"] = "REPLAN"
        packet = {**packet, "created_at": now(), "replan_count": state["replan_count"]}
        state["remediation_packet"] = packet; state["replan_history"].append(packet); state["current_loop"] = "project-plan"; add_evidence(state, "replan", evidence); return
    if event == "resume":
        if state.get("outcome") != "BLOCKED" or not evidence:
            raise PolicyError("approval evidence required")
        try:
            approval = json.loads(evidence)
        except json.JSONDecodeError as error:
            raise PolicyError("resume requires structured project owner evidence") from error
        _fields(approval, ("owner_id", "owner_role", "blocked_reason", "blocked_evidence", "decision", "remediation_status", "remediation_evidence_refs", "next_attempt_policy"), "resume evidence")
        blocked = state.get("block") or {}
        if approval["owner_role"] != "project-owner" or approval["decision"] != "resume" or approval["remediation_status"] not in ("resolved", "retry-authorized") or not isinstance(approval["remediation_evidence_refs"], list) or not approval["remediation_evidence_refs"] or not all(isinstance(item, str) and item for item in approval["remediation_evidence_refs"]) or not isinstance(approval["next_attempt_policy"], dict) or not all(isinstance(approval[name], str) and approval[name] for name in ("owner_id", "blocked_reason", "blocked_evidence")) or approval["blocked_reason"] != blocked.get("reason") or approval["blocked_evidence"] != blocked.get("evidence"):
            raise PolicyError("resume ownership or blocked evidence mismatch")
        if blocked.get("reason") == "max_replans_exceeded":
            replacement = approval["next_attempt_policy"].get("replacement_max_replans")
            if replacement == "unlimited": state["replan_policy"] = {"mode": "owner-unlimited", "authorized_by": approval["owner_id"], "authorized_at": now()}
            elif isinstance(replacement, int) and replacement > state["replan_count"]:
                state["max_replans"] = replacement; state["replan_policy"] = {"mode": "bounded", "max_replans": replacement}
            else: raise PolicyError("max replan resume requires replacement bound")
        resolve_alerts_for_block(state, blocked, "validated project-owner resume")
        state["outcome"] = None; state["block"] = None; add_evidence(state, event, evidence); return
    raise PolicyError("unknown event")


def continuation_directive(state: dict) -> dict:
    """Return the only permitted runtime directive for an automatic lifecycle.

    The core cannot itself perform agent work; it makes the continuation and
    user-output contract explicit for the runtime that owns those tools.
    """
    outcome = state.get("outcome")
    if outcome in TERMINAL_OUTCOMES:
        return {"action": "stop", "reason": outcome, "user_output": "required"}
    current = state.get("current_loop")
    if current not in LOOPS:
        raise PolicyError("unknown lifecycle loop")
    sequence = ("project-init", "project-plan", "project-run", "project-review") if state.get("replan_count", 0) == 0 else ("project-plan", "project-run", "project-review")
    if current not in sequence:
        raise PolicyError("current loop does not match lifecycle iteration")
    return {
        "action": "continue",
        "loop": current,
        "iteration": state.get("plan_iteration"),
        "cycle": "initial" if state.get("replan_count", 0) == 0 else "replan",
        "sequence": sequence,
        "user_output": "forbidden",
        "stop_only_for": ["COMPLETE", "DEFERRED_BACKLOG", "BLOCKED"],
    }


def record_failure(state: dict, command: str, failure_class: str, failure_id: str) -> str:
    fingerprint = hashlib.sha256("|".join((command, failure_class, failure_id)).encode()).hexdigest()
    state["failure_history"].append({"fingerprint": fingerprint, "recorded_at": now()})
    if len(state["failure_history"]) >= 3 and all(item["fingerprint"] == fingerprint for item in state["failure_history"][-3:]):
        block(state, "repeated_evaluation_failure", True, fingerprint)
    return fingerprint


def record_trajectory_summary(project_root: Path, state: dict, artifact_ref: str) -> dict:
    """Store a terminal/replan outcome summary as auditable, non-authoritative memory."""
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review":
        raise PolicyError("trajectory summary requires project review")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    _fields(value, ("tags", "outcome", "plan_revision_hash", "review_artifact_hash", "non_authoritative"), "trajectory summary")
    revision = _active_revision(state)
    if (not isinstance(value["tags"], list) or not value["tags"] or not all(isinstance(item, str) and item for item in value["tags"])
            or value["outcome"] not in ("COMPLETE", "REPLAN", "BLOCKED", "DEFERRED_BACKLOG")
            or value["plan_revision_hash"] != revision["execution_plan"]["content_hash"]
            or value["review_artifact_hash"] != (state.get("review_artifact") or {}).get("content_hash")
            or value["non_authoritative"] is not True):
        raise PolicyError("invalid trajectory summary")
    record = {**descriptor, "tags": sorted(set(value["tags"])), "outcome": value["outcome"], "recorded_at": now(), "non_authoritative": True}
    state["trajectory_summaries"].append(record)
    add_evidence(state, "trajectory-summary", json.dumps(record, sort_keys=True))
    return record


def retrieve_trajectories(project_root: Path, state: dict, tags: list[str], limit: int = 5) -> dict:
    """Retrieve deterministic tag matches; callers must treat output as planning hints only."""
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-plan" or not tags or limit < 1:
        raise PolicyError("trajectory retrieval requires plan loop, tags, and positive limit")
    wanted = set(tags); candidates = []
    for path in (root / RUNS_RELATIVE).glob(f"*/{STATE_NAME}"):
        try:
            prior = json.loads(path.read_text(encoding="utf-8")); _normalize(prior)
        except (OSError, json.JSONDecodeError, PolicyError):
            continue
        for summary in prior.get("trajectory_summaries", []):
            matched = sorted(wanted & set(summary.get("tags", [])))
            if matched:
                candidates.append({"run_id": prior["run_id"], "artifact_ref": summary.get("artifact_ref"), "content_hash": summary.get("content_hash"), "matched_tags": matched, "score": len(matched), "outcome": summary.get("outcome")})
    candidates.sort(key=lambda item: (-item["score"], item["run_id"], item["content_hash"] or ""))
    result = {"tags": sorted(wanted), "limit": limit, "non_authoritative": True, "candidates": candidates[:limit], "recorded_at": now()}
    ref = _artifact_write(root, state, f"project-plan/iteration-{state['plan_iteration']}/trajectory-retrieval.json", result)
    record = {"artifact_ref": ref, "content_hash": hashlib.sha256((root / ref).read_bytes()).hexdigest(), **result}
    state["trajectory_retrievals"].append(record)
    add_evidence(state, "trajectory-retrieval", json.dumps(record, sort_keys=True))
    return record


def load_registry(project_root: Path) -> dict:
    root = _validate_root(project_root); _ensure_layout(root)
    run_id = _read_pointer(root)
    if not run_id: raise PolicyError("state does not exist")
    path = registry_path(root, run_id)
    return json.loads(path.read_text()) if path.exists() else {"schema_version": 1, "agents": []}


def registry_add(project_root: Path, agent_id: str, parent_id: str | None, depth: int, scope: str) -> dict:
    if not agent_id or depth < 0 or not scope: raise PolicyError("invalid agent record")
    registry = load_registry(project_root)
    if any(a["agent_id"] == agent_id for a in registry["agents"]): raise PolicyError("agent already exists")
    if parent_id and not any(a["agent_id"] == parent_id for a in registry["agents"]): raise PolicyError("unknown parent agent")
    timestamp = now(); registry["agents"].append({"agent_id": agent_id, "parent_id": parent_id, "depth": depth, "scope": scope, "started_at": timestamp, "heartbeat_at": timestamp, "status": "active"})
    root = _validate_root(project_root); atomic_write(registry_path(root, _read_pointer(root) or ""), registry); return registry


def registry_update(project_root: Path, agent_id: str, status: str) -> dict:
    if status not in AGENT_STATUSES: raise PolicyError("invalid agent status")
    registry = load_registry(project_root)
    agent = next((a for a in registry["agents"] if a["agent_id"] == agent_id), None)
    if not agent or (agent["status"] != "active" and status == "active"): raise PolicyError("invalid agent status transition")
    root = _validate_root(project_root); agent["status"] = status; agent["heartbeat_at"] = now(); atomic_write(registry_path(root, _read_pointer(root) or ""), registry); return registry


def heartbeat_touch(project_root: Path, agent_id: str) -> dict:
    registry = load_registry(project_root); agent = next((a for a in registry["agents"] if a["agent_id"] == agent_id), None)
    if not agent or agent["status"] != "active": raise PolicyError("active agent not found")
    root = _validate_root(project_root); agent["heartbeat_at"] = now(); atomic_write(registry_path(root, _read_pointer(root) or ""), registry); return registry


def heartbeat_status(project_root: Path, timeout_seconds: int) -> dict:
    if timeout_seconds < 1: raise PolicyError("timeout must be positive")
    registry = load_registry(project_root); current = datetime.now(timezone.utc)
    stale = [a["agent_id"] for a in registry["agents"] if a["status"] == "active" and (current - datetime.fromisoformat(a["heartbeat_at"])).total_seconds() > timeout_seconds]
    return {"timeout_seconds": timeout_seconds, "stale_agent_ids": stale, "registry": registry}


def record_agent_health(project_root: Path, agent_id: str, outcome: str, failure_id: str = "",
                        max_attempts: int = 3, required: bool = False) -> dict:
    """Record bounded current-run agent health; required failures remain fail-closed."""
    if outcome not in AGENT_HEALTH_OUTCOMES or max_attempts < 1:
        raise PolicyError("invalid agent health report")
    root = _validate_root(project_root); state = load(root); registry = load_registry(root)
    agent = next((item for item in registry["agents"] if item["agent_id"] == agent_id), None)
    if not agent: raise PolicyError("agent health requires a registered agent")
    prior = state["agent_health"].get(agent_id, {})
    attempts = int(prior.get("attempts", 0)) + (1 if outcome in ("failed", "timeout", "unavailable") else 0)
    fingerprint = hashlib.sha256(f"{agent_id}|{outcome}|{failure_id}".encode()).hexdigest() if failure_id else None
    quarantined = outcome == "quarantined" or attempts >= max_attempts
    record = {"agent_id": agent_id, "scope": agent["scope"], "outcome": "quarantined" if quarantined else outcome,
              "attempts": attempts, "max_attempts": max_attempts, "failure_fingerprint": fingerprint,
              "required": required, "recorded_at": now(), "heartbeat_at": agent["heartbeat_at"]}
    state["agent_health"][agent_id] = record
    add_evidence(state, "agent-health", json.dumps(record, sort_keys=True))
    if required and record["outcome"] in ("timeout", "failed", "unavailable", "quarantined"):
        block(state, "required_agent_unhealthy", False, json.dumps(record, sort_keys=True))
    save(root, state)
    return record


def agent_health_status(project_root: Path) -> dict:
    state = load(project_root)
    return {"agent_health": state.get("agent_health", {}), "run_id": state["run_id"]}
