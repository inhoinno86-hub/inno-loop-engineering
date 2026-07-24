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
QUALITY_SECTIONS = ("requirements", "constraints", "non_goals", "risks", "acceptance_criteria", "ambiguities")
MATERIAL_CATEGORIES = ("security", "privacy", "irreversible_effect", "compliance", "budget", "core_architecture")
OUTPUT_FIELDS = ("goal", "scope", "requirements", "non_goals", "assumptions", "risks", "safety_approval_policy", "success_criteria", "open_decisions")


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
    state = {"schema_version": 1, "run_id": str(uuid.uuid4()), "current_loop": "project-init", "outcome": None, "input_hash": record["content_hash"], "input": record, "artifact_version": 3, "checkpoint": None, "lifecycle_authorization": {"scope": "full-lifecycle", "evidence": "explicit inno-loop invocation", "recorded_at": now()} if full_lifecycle else None, "last_review_outcome": None, "replan_history": [], "max_replans": max_replans, "plan_iteration": 1, "decision_log": [], "assumption_log": [], "verification_evidence": [], "integration_evidence": [], "decision_a": None, "input_packets": {}, "quality_gates": {}, "init_outputs": None, "plan_revisions": [], "review_artifact": None, "remediation_packet": None, "backlog": [], "block": None, "failure_history": [], "replan_count": 0, "created_at": now()}
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
    add_evidence(state, "block", evidence)


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
    record = {**descriptor, "loop": loop, "iteration": iteration, "input_hash": packet["input_hash"]}
    state["input_packets"][_packet_key(loop, iteration)] = record
    add_evidence(state, "input-packet", json.dumps(record, sort_keys=True))
    return record


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
        identities.add(analysis["run_id"]); analyses.append({**descriptor, "run_id": analysis["run_id"], "tool": analysis["tool"]})
    judge, judge_descriptor = _json_artifact(root, state, judge_ref)
    _fields(judge, ("tool", "run_id", "invocation_id", "timestamp", "input_packet_hash", "analysis_hashes", "requirement_matrix", "consistency_score", "material_contradictions"), "judge")
    if judge["input_packet_hash"] != packet["content_hash"] or set(judge["analysis_hashes"]) != {item["content_hash"] for item in analyses}:
        raise PolicyError("judge analysis or input packet mismatch")
    matrix = judge["requirement_matrix"]
    if not isinstance(matrix, list) or not matrix:
        raise PolicyError("judge requirement matrix is required")
    total = unanimous = 0.0; material_ids = set(); material_differences = set(); critical = set()
    for item in matrix:
        if not isinstance(item, dict): raise PolicyError("invalid requirement matrix entry")
        _fields(item, ("id", "weight", "classification", "material", "category"), "requirement matrix entry")
        if item["classification"] not in ("unanimous", "two-of-three", "unique", "contradictory") or not isinstance(item["weight"], (int, float)) or item["weight"] <= 0:
            raise PolicyError("invalid requirement matrix classification or weight")
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
    if 50 <= score <= 80 and not critical:
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
    record = {"loop": loop, "iteration": iteration, "input_packet_hash": packet["content_hash"], "analyses": analyses, "judge": judge_descriptor, "mediator": mediator, "consistency_score": score, "material_contradictions": sorted(critical), "accepted": score > 80 and not critical or (50 <= score <= 80 and mediator is not None)}
    state["quality_gates"][_packet_key(loop, iteration)] = record
    add_evidence(state, "quality-gate", json.dumps(record, sort_keys=True))
    if score < 50 or critical:
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
                "stage": "analysis", "role": role, "run_id": run_id,
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
    for task in plan["tasks"]:
        if not isinstance(task, dict): raise PolicyError("invalid execution plan task")
        _fields(task, ("scope", "owner", "dependencies", "definition_of_done", "validation", "rollback", "source_input_hash", "source_plan_revision_hash"), "execution plan task")
        if task["source_input_hash"] != packet["content_hash"]: raise PolicyError("task input hash mismatch")
    if not isinstance(matrix.get("validations"), list): raise PolicyError("validation matrix validations are required")
    revision = {"iteration": iteration, "input_packet_hash": packet["content_hash"], "quality_gate_hash": gate["judge"]["content_hash"], "execution_plan": plan_descriptor, "validation_matrix": matrix_descriptor}
    state["plan_revisions"].append(revision)
    transition(state, "complete-plan", plan_descriptor["artifact_ref"])


def record_remediation_packet(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review" or not state.get("plan_revisions"):
        raise PolicyError("remediation packet requires a reviewed plan")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    fields = ("failed_acceptance_criteria", "failure_evidence", "plan_vs_actual", "root_cause_or_uncertainty", "required_correction", "risk", "non_deferrable", "prior_plan_revision_hash", "review_artifact_hash")
    _fields(value, fields, "remediation packet")
    prior = state["plan_revisions"][-1]["execution_plan"]["content_hash"]
    review = (state.get("review_artifact") or {}).get("content_hash")
    if not value["non_deferrable"] or value["prior_plan_revision_hash"] != prior or value["review_artifact_hash"] != review:
        raise PolicyError("remediation packet lineage or non-deferrable status mismatch")
    return {**descriptor, "packet": value}


def record_review_artifact(project_root: Path, state: dict, artifact_ref: str) -> dict:
    root = _validate_root(project_root)
    if state.get("current_loop") != "project-review":
        raise PolicyError("review artifact loop does not match current loop")
    value, descriptor = _json_artifact(root, state, artifact_ref)
    _fields(value, ("plan_revision_hash", "acceptance_results"), "review artifact")
    if not state.get("plan_revisions") or value["plan_revision_hash"] != state["plan_revisions"][-1]["execution_plan"]["content_hash"]:
        raise PolicyError("review artifact plan revision mismatch")
    state["review_artifact"] = descriptor
    add_evidence(state, "review-artifact", json.dumps(descriptor, sort_keys=True))
    return descriptor


def record_integration(project_root: Path, state: dict, loop: str, name: str, status: str, artifact_ref: str | None = None, detail: str = "") -> None:
    root = _validate_root(project_root)
    if loop not in ("project-init", "project-plan") or loop != state.get("current_loop"):
        raise PolicyError("integration loop does not match current loop")
    if name not in REQUIRED_INTEGRATIONS or status not in INTEGRATION_STATUSES:
        raise PolicyError("unknown integration name or status")
    iteration = 0 if loop == "project-init" else state["plan_iteration"]
    prior = [r for r in state["integration_evidence"] if r["loop"] == loop and r["iteration"] == iteration]
    expected = REQUIRED_INTEGRATIONS[len(prior)] if len(prior) < len(REQUIRED_INTEGRATIONS) else None
    if status == "USED" and name != expected:
        raise PolicyError("integration evidence must use required order")
    record = {"loop": loop, "iteration": iteration, "name": name, "status": status, "recorded_at": now()}
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
    records = [r for r in state["integration_evidence"] if r["loop"] == loop and r["iteration"] == iteration]
    if [r["name"] for r in records] != list(REQUIRED_INTEGRATIONS) or any(r["status"] != "USED" for r in records):
        block(state, "required_integrations_missing", False, f"{loop}:{iteration}")
        raise PolicyError("required ordered integration evidence missing")


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
    if event in {"complete-init", "complete-plan", "complete-run"}:
        expected = {"complete-init": ("project-init", "project-plan"), "complete-plan": ("project-plan", "project-run"), "complete-run": ("project-run", "project-review")}[event]
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
    if event == "complete":
        if current != "project-review": raise PolicyError("only review can complete")
        state["outcome"] = "COMPLETE"; add_evidence(state, event, evidence); return
    if event == "replan":
        if current != "project-review": raise PolicyError("only review can replan")
        if state["replan_count"] >= state["max_replans"]:
            block(state, "max_replans_exceeded", True, evidence); return
        packet = state.get("remediation_packet")
        if not packet or packet.get("artifact_ref") != evidence:
            raise PolicyError("structured remediation packet is required")
        state["replan_count"] += 1; state["plan_iteration"] += 1; state["last_review_outcome"] = "REPLAN"
        packet = {**packet, "created_at": now(), "replan_count": state["replan_count"]}
        state["remediation_packet"] = packet; state["replan_history"].append(packet); state["current_loop"] = "project-plan"; add_evidence(state, "replan", evidence); return
    if event == "resume":
        if state.get("outcome") != "BLOCKED" or (state.get("block") or {}).get("requires_human") and not evidence:
            raise PolicyError("approval evidence required")
        state["outcome"] = None; state["block"] = None; add_evidence(state, event, evidence); return
    raise PolicyError("unknown event")


def record_failure(state: dict, command: str, failure_class: str, failure_id: str) -> str:
    fingerprint = hashlib.sha256("|".join((command, failure_class, failure_id)).encode()).hexdigest()
    state["failure_history"].append({"fingerprint": fingerprint, "recorded_at": now()})
    if len(state["failure_history"]) >= 3 and all(item["fingerprint"] == fingerprint for item in state["failure_history"][-3:]):
        block(state, "repeated_evaluation_failure", True, fingerprint)
    return fingerprint


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
