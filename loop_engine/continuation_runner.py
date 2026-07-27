"""Local, terminal-only lifecycle driver for an installed Codex agent runtime."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path

from . import core


BRIDGE_PROTOCOL_VERSION = 2
DEFAULT_INTEGRATION_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0


def _prompt(root: Path, directive: dict) -> str:
    controller = f"loop-engine --project-root {shlex.quote(str(root))}"
    return f"""You are the local Loop Engine continuation worker. Work only in the current
repository and execute exactly the current lifecycle stage: {directive['loop']}.
Read the active state with `{controller} status`. Use only the installed
`loop-engine` CLI for artifact-recording actions; this project is not expected to
contain a plugin checkout or skill files. Required Ouroboros/Superpowers planning
integrations are host-owned and recorded before you run; do not invoke them yourself.
Do not ask the user for routine approval or give progress reports. Create and record
every required artifact, then record one current-loop `record-stage-submission`
manifest containing only its artifact references. Do not invoke `plan`, `run`,
`review`, `review-complete`, `replan`, `defer`, `complete-init`, or `complete-plan`:
the supervisor validates the submission and selects that command. Stop after the
submission, a terminal/HIL BLOCKED state, or a real safety gate. Do not commit, push,
deploy, publish, or contact external services.

Before creating a bound init/plan artifact, call `{controller} artifact-context --artifact-type <type>`.
Write semantic JSON payloads only, then call `{controller} write-bound-artifact --artifact-type <type> --payload <payload-ref> --output-name <name>.json`; Core owns all hash bindings. Before recording a submission, call `{controller} validate-stage-artifacts --artifact key=ref` for every required artifact. A nonzero validation result means fix the artifact and do not record a stage submission."""


def _state_identity(state: dict) -> dict:
    return {"run_id": state.get("run_id"), "loop": state.get("current_loop"),
            "iteration": 0 if state.get("current_loop") == "project-init" else state.get("plan_iteration"),
            "outcome": state.get("outcome")}


def _submission(root: Path, state: dict, directive: dict) -> tuple[dict, dict]:
    key = f"{directive['loop']}:{directive['iteration']}"
    descriptor = state.get("stage_submissions", {}).get(key)
    if not descriptor:
        raise core.PolicyError("stage executor submission is required")
    value, current = core._json_artifact(root, state, descriptor["artifact_ref"])
    if current["content_hash"] != descriptor["content_hash"]:
        raise core.PolicyError("stage submission hash changed")
    return value, descriptor


def execute_stage(root: Path, expected: dict) -> dict:
    """Validate a worker submission and perform exactly one lifecycle transition."""
    state = core.load(root)
    if _state_identity(state) != {key: expected[key] for key in ("run_id", "loop", "iteration", "outcome")}:
        raise core.PolicyError("stage executor observed unexpected state change")
    directive = core.continuation_directive(state)
    if directive["action"] != "continue" or directive["loop"] != expected["loop"] or directive["iteration"] != expected["iteration"]:
        raise core.PolicyError("stage executor directive changed")
    submission, descriptor = _submission(root, state, directive); artifacts = submission["artifacts"]
    loop = directive["loop"]
    if loop == "project-init":
        core.complete_init(root, state, artifacts.get("input_packet", ""), artifacts.get("charter", ""), artifacts.get("design", ""), artifacts.get("roadmap", "")); command = "complete-init"
    elif loop == "project-plan":
        core.complete_plan(root, state, artifacts.get("input_packet", ""), artifacts.get("execution_plan", ""), artifacts.get("validation_matrix", "")); command = "complete-plan"
    elif loop == "project-run":
        report = artifacts.get("run_report", "")
        core.complete_run(root, state, report); command = "review"
    else:
        review_ref = artifacts.get("review_artifact", "")
        if not state.get("review_artifact") or state["review_artifact"]["artifact_ref"] != review_ref:
            raise core.PolicyError("stage submission must reference recorded review artifact")
        review, _ = core._json_artifact(root, state, review_ref)
        matrix, _ = core._json_artifact(root, state, core._active_revision(state)["validation_matrix"]["artifact_ref"])
        protected = {item["criterion_id"] for item in matrix["criteria"] if item["mandatory"] or item["critical"]}
        failures = {item["criterion_id"] for item in review["acceptance_results"] if item["verdict"] != "PASS"}
        if not failures:
            core.complete_review(root, state, review_ref); command = "review-complete"
        elif failures & protected:
            remediation = artifacts.get("remediation_packet", "")
            if not state.get("remediation_packet") or state["remediation_packet"]["artifact_ref"] != remediation:
                raise core.PolicyError("failing protected review requires recorded remediation packet")
            core.transition(state, "replan", remediation); command = "replan"
        else:
            backlog = artifacts.get("backlog_item", "")
            if not backlog:
                raise core.PolicyError("nonmandatory review findings require backlog item")
            core.defer(root, state, backlog); command = "defer"
    receipt = {"executor": "stage-executor", "input": expected, "submission": descriptor,
               "command": command, "result": _state_identity(state)}
    core._artifact_write(root, state, f"continuation/stage-executor-{expected['loop']}-{expected['iteration']}.json", receipt)
    core.save(root, state)
    return receipt


def _planning_integrations_ready(state: dict) -> bool:
    loop = state.get("current_loop")
    if loop not in ("project-init", "project-plan"):
        return True
    iteration = 0 if loop == "project-init" else state["plan_iteration"]
    attempt = core._integration_attempt(state, loop, iteration)
    records = [item for item in state.get("integration_evidence", []) if item["loop"] == loop and item["iteration"] == iteration and item.get("attempt", 0) == attempt]
    return [item["name"] for item in records] == list(core.REQUIRED_INTEGRATIONS) and all(item["status"] == "USED" for item in records)


def _bridge_lineage(state: dict) -> dict:
    """Give a host the immutable input and prior lifecycle evidence it must inspect."""
    return {
        "lifecycle_input": state["input"],
        "lifecycle_authorization": state.get("lifecycle_authorization"),
        "init_outputs": state.get("init_outputs"),
        "latest_plan_revision": state.get("plan_revisions", [])[-1] if state.get("plan_revisions") else None,
        "remediation_packet": state.get("remediation_packet"),
    }


def _bridge_preflight_payload(state: dict, directive: dict) -> dict:
    return {
        "protocol_version": BRIDGE_PROTOCOL_VERSION,
        "operation": "preflight",
        "request_id": f"{state['run_id']}:{directive['loop']}:{directive['iteration']}:preflight",
        "run_id": state["run_id"], "loop": directive["loop"], "iteration": directive["iteration"],
        "required_integrations": list(core.REQUIRED_INTEGRATIONS),
        "interactive_parent_required": True,
        **_bridge_lineage(state),
    }


def bridge_preflight(root: Path, state: dict, command: str | None) -> dict:
    """Verify an explicit, non-mutating host-adapter capability response."""
    directive = core.continuation_directive(state)
    required = directive["action"] == "continue" and directive["loop"] in ("project-init", "project-plan") and not _planning_integrations_ready(state)
    resolved = _resolve_integration_adapter(command)
    result = {"required": required, "configured": bool(resolved), "ready": not required,
              "protocol_version": BRIDGE_PROTOCOL_VERSION,
              "configuration": "--host-bridge-command or LOOP_ENGINE_HOST_BRIDGE_COMMAND"}
    if not required:
        return result
    if not resolved:
        result["detail"] = "interactive planning requires an explicit parent-host adapter"
        return result
    payload = _bridge_preflight_payload(state, directive)
    try:
        completed = subprocess.run(shlex.split(resolved), cwd=root, input=json.dumps(payload), text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if completed.returncode:
            raise RuntimeError((completed.stderr or completed.stdout or "adapter returned nonzero")[-4000:])
        response = json.loads(completed.stdout)
        if (not isinstance(response, dict) or response.get("protocol_version") != BRIDGE_PROTOCOL_VERSION
                or response.get("operation") != "preflight" or response.get("request_id") != payload["request_id"]
                or response.get("ready") is not True):
            raise ValueError("adapter preflight must return matching protocol, request_id, operation, and ready=true")
        result["ready"] = True
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as error:
        result["detail"] = core.redact(str(error))
    return result


def _resolve_integration_adapter(command: str | None) -> str | None:
    """Only an explicitly configured parent-host adapter may own integrations."""
    return command or os.environ.get("LOOP_ENGINE_HOST_BRIDGE_COMMAND")


def _bridge_payload(root: Path, state: dict, directive: dict, attempt: int) -> dict:
    key = f"{directive['loop']}:{directive['iteration']}"
    packet = state.get("input_packets", {}).get(key)
    return {
        "protocol_version": BRIDGE_PROTOCOL_VERSION,
        "operation": "integrate",
        "request_id": f"{state['run_id']}:{directive['loop']}:{directive['iteration']}:{attempt}",
        "run_id": state["run_id"], "loop": directive["loop"],
        "iteration": directive["iteration"], "attempt": attempt,
        "artifact_root": str(core.artifacts_path(root, state["run_id"]).relative_to(root)),
        "input_packet": None if packet is None else {
            "artifact_ref": packet["artifact_ref"], "content_hash": packet["content_hash"],
        },
        "required_integrations": list(core.REQUIRED_INTEGRATIONS),
        "interactive_parent_required": True,
        **_bridge_lineage(state),
    }


def _write_bridge_receipt(root: Path, state: dict, payload: dict, response: dict) -> str:
    path = core.artifacts_path(root, state["run_id"]) / "continuation" / f"bridge-{payload['loop']}-{payload['iteration']}-{payload['attempt']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"request": payload, "response": response}, sort_keys=True, indent=2), encoding="utf-8")
    return path.relative_to(root).as_posix()


def _validate_bridge_response(payload: dict, value: object) -> list[dict]:
    if not isinstance(value, dict):
        raise ValueError("adapter response must be a versioned JSON object")
    if value.get("protocol_version") != BRIDGE_PROTOCOL_VERSION:
        raise ValueError("adapter protocol version mismatch")
    if value.get("operation") != "integrate":
        raise ValueError("adapter operation mismatch")
    if value.get("request_id") != payload["request_id"]:
        raise ValueError("adapter response request_id mismatch")
    values = value.get("results")
    if not isinstance(values, list) or len(values) != len(core.REQUIRED_INTEGRATIONS):
        raise ValueError("adapter must return one result per required integration")
    for expected, item in zip(core.REQUIRED_INTEGRATIONS, values):
        if not isinstance(item, dict) or item.get("name") != expected:
            raise ValueError("adapter results must preserve required integration order")
        if item.get("status") not in ("USED", "FAILED", "UNAVAILABLE"):
            raise ValueError("invalid adapter integration status")
    return values


def _run_integration_adapter(root: Path, state: dict, directive: dict, command: str | None,
                             retries: int = DEFAULT_INTEGRATION_RETRIES,
                             retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS) -> bool:
    """Ask the host-owned bridge for planning integrations, then record its evidence.

    The local Codex child deliberately has no MCP/tool authority.  A host that does
    have those tools supplies a small adapter command which receives a JSON request
    on stdin and returns one ordered result per required integration.  Artifacts
    must already be written beneath the active run root; this runner only verifies
    and records them.  That makes an unavailable host bridge a truthful BLOCKED
    state instead of mislabelling it as a user cancellation.
    """
    command = _resolve_integration_adapter(command)
    if not command:
        core.block(state, "continuation_integration_adapter_required", False,
                   "configure --host-bridge-command or LOOP_ENGINE_HOST_BRIDGE_COMMAND before starting "
                   f"{directive['loop']}:{directive['iteration']}")
        return False
    last_error = None
    for bridge_attempt in range(retries + 1):
        payload = _bridge_payload(root, state, directive, bridge_attempt)
        try:
            result = subprocess.run(shlex.split(command), cwd=root, input=json.dumps(payload), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout or "adapter returned nonzero")[-4000:])
            response = json.loads(result.stdout)
            values = _validate_bridge_response(payload, response)
            _write_bridge_receipt(root, state, payload, response)
            for expected, value in zip(core.REQUIRED_INTEGRATIONS, values):
                if value["status"] == "USED":
                    core.record_integration(root, state, directive["loop"], expected, "USED", value.get("artifact"))
                else:
                    core.record_integration(root, state, directive["loop"], expected, value["status"], detail=value.get("detail", "host integration unavailable"))
                    return False
            return True
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if bridge_attempt < retries:
                time.sleep(retry_backoff_seconds * (bridge_attempt + 1))
    core.block(state, "continuation_integration_adapter_failed", False, core.redact(str(last_error)))
    return False


def _deliver_alerts(root: Path, state: dict, command: str | None) -> None:
    """Deliver terminal alerts through an explicit host-owned adapter only."""
    if not command:
        return
    for alert in core.pending_alerts(state):
        try:
            result = subprocess.run(shlex.split(command), cwd=root, input=json.dumps(alert), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if result.returncode:
                continue
            response = json.loads(result.stdout or "{}")
            receipt = response.get("receipt") if isinstance(response, dict) else None
            if isinstance(receipt, str) and receipt:
                core.acknowledge_alert(state, alert["alert_id"], receipt)
        except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError):
            continue


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-engine-continuation")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--max-stages", type=int, default=64)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--integration-adapter", "--host-bridge-command", dest="integration_adapter", help="host-owned planning-integration bridge command")
    parser.add_argument("--integration-retries", type=int, default=DEFAULT_INTEGRATION_RETRIES)
    parser.add_argument("--integration-retry-backoff-seconds", type=float, default=DEFAULT_RETRY_BACKOFF_SECONDS)
    parser.add_argument("--alert-adapter", help="host-owned terminal alert delivery command")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    if args.max_stages < 1:
        raise SystemExit("max-stages must be positive")
    if args.integration_retries < 0 or args.integration_retry_backoff_seconds < 0:
        raise SystemExit("integration retry values must be non-negative")
    for attempt in range(1, args.max_stages + 1):
        state = core.load(root); directive = core.continuation_directive(state)
        if directive["action"] == "stop":
            _deliver_alerts(root, state, args.alert_adapter); core.save(root, state)
            print(json.dumps(directive, sort_keys=True)); return 0
        preflight = bridge_preflight(root, state, args.integration_adapter)
        if not preflight["ready"]:
            core.block(state, "continuation_host_bridge_unavailable", False,
                       preflight.get("detail", preflight["configuration"]))
            _deliver_alerts(root, state, args.alert_adapter); core.save(root, state)
            print(json.dumps(core.continuation_directive(state), sort_keys=True)); return 2
        if directive["loop"] == "project-run":
            core.capture_worktree_baseline(root, state); core.save(root, state)
        if not _planning_integrations_ready(state):
            if not _run_integration_adapter(root, state, directive, args.integration_adapter,
                                            args.integration_retries, args.integration_retry_backoff_seconds):
                _deliver_alerts(root, state, args.alert_adapter)
                core.save(root, state)
                print(json.dumps(core.continuation_directive(state), sort_keys=True)); return 2
            core.save(root, state)
            state = core.load(root); directive = core.continuation_directive(state)
        output = core.artifacts_path(root, state["run_id"]) / "continuation" / f"attempt-{attempt}.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([args.codex_bin, "exec", "-C", str(root), "--output-last-message", str(output), _prompt(root, directive)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            detail = core.redact((result.stderr or result.stdout or "agent runtime failed")[-4000:])
            core.block(state, "continuation_agent_failed", False, detail); core.save(root, state)
            _deliver_alerts(root, state, args.alert_adapter); core.save(root, state)
            print(json.dumps(core.continuation_directive(state), sort_keys=True)); return 2
        expected = _state_identity(state)
        try:
            execute_stage(root, expected)
        except core.PolicyError as error:
            updated = core.load(root)
            if _state_identity(updated) != expected:
                core.block(updated, "continuation_stage_executor_unexpected_state", False, str(error))
            else:
                core.block(updated, "continuation_stage_executor_validation_failed", False, str(error))
            core.save(root, updated)
            _deliver_alerts(root, updated, args.alert_adapter); core.save(root, updated)
            print(json.dumps(core.continuation_directive(updated), sort_keys=True)); return 2
    raise SystemExit("continuation max-stages exhausted")


if __name__ == "__main__":
    raise SystemExit(main())
