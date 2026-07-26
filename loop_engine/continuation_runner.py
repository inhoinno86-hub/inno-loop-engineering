"""Local, terminal-only lifecycle driver for an installed Codex agent runtime."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from . import core


def _prompt(directive: dict) -> str:
    return f"""You are the local Loop Engine continuation worker. Work only in the current
repository and execute exactly the current lifecycle stage: {directive['loop']}.
Read the active state with `python3 plugin/inno-loop-engineering/scripts/loopctl.py --project-root . status`
and follow `plugin/inno-loop-engineering/skills/inno-loop/SKILL.md`. Required
Ouroboros/Superpowers planning integrations are host-owned and are recorded before
you run; do not invoke them yourself. Do not ask the
user for routine approval or give progress reports. Persist every required artifact
and transition. Stop your own work only after advancing the lifecycle, reaching a
terminal/HIL BLOCKED state, or encountering a real safety gate. Do not commit, push,
deploy, publish, or contact external services."""


def _planning_integrations_ready(state: dict) -> bool:
    loop = state.get("current_loop")
    if loop not in ("project-init", "project-plan"):
        return True
    iteration = 0 if loop == "project-init" else state["plan_iteration"]
    attempt = core._integration_attempt(state, loop, iteration)
    records = [item for item in state.get("integration_evidence", []) if item["loop"] == loop and item["iteration"] == iteration and item.get("attempt", 0) == attempt]
    return [item["name"] for item in records] == list(core.REQUIRED_INTEGRATIONS) and all(item["status"] == "USED" for item in records)


def _run_integration_adapter(root: Path, state: dict, directive: dict, command: str | None) -> bool:
    """Ask the host-owned bridge for planning integrations, then record its evidence.

    The local Codex child deliberately has no MCP/tool authority.  A host that does
    have those tools supplies a small adapter command which receives a JSON request
    on stdin and returns one ordered result per required integration.  Artifacts
    must already be written beneath the active run root; this runner only verifies
    and records them.  That makes an unavailable host bridge a truthful BLOCKED
    state instead of mislabelling it as a user cancellation.
    """
    if not command:
        core.block(state, "continuation_integration_adapter_required", False,
                   f"{directive['loop']}:{directive['iteration']}")
        return False
    payload = {
        "run_id": state["run_id"], "loop": directive["loop"],
        "iteration": directive["iteration"],
        "artifact_root": str(core.artifacts_path(root, state["run_id"]).relative_to(root)),
        "required_integrations": list(core.REQUIRED_INTEGRATIONS),
    }
    try:
        result = subprocess.run(shlex.split(command), cwd=root, input=json.dumps(payload), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or "adapter returned nonzero")[-4000:])
        values = json.loads(result.stdout)
        if not isinstance(values, list) or len(values) != len(core.REQUIRED_INTEGRATIONS):
            raise ValueError("adapter must return one result per required integration")
        for expected, value in zip(core.REQUIRED_INTEGRATIONS, values):
            if not isinstance(value, dict) or value.get("name") != expected:
                raise ValueError("adapter results must preserve required integration order")
            status = value.get("status")
            if status == "USED":
                core.record_integration(root, state, directive["loop"], expected, status, value.get("artifact"))
            elif status in ("FAILED", "UNAVAILABLE"):
                core.record_integration(root, state, directive["loop"], expected, status, detail=value.get("detail", "host integration unavailable"))
                return False
            else:
                raise ValueError("invalid adapter integration status")
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as error:
        core.block(state, "continuation_integration_adapter_failed", False, core.redact(str(error)))
        return False
    return True


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
    parser.add_argument("--integration-adapter", help="host-owned planning-integration bridge command")
    parser.add_argument("--alert-adapter", help="host-owned terminal alert delivery command")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    if args.max_stages < 1:
        raise SystemExit("max-stages must be positive")
    for attempt in range(1, args.max_stages + 1):
        state = core.load(root); directive = core.continuation_directive(state)
        if directive["action"] == "stop":
            _deliver_alerts(root, state, args.alert_adapter); core.save(root, state)
            print(json.dumps(directive, sort_keys=True)); return 0
        if directive["loop"] == "project-run":
            core.capture_worktree_baseline(root, state); core.save(root, state)
        if not _planning_integrations_ready(state):
            if not _run_integration_adapter(root, state, directive, args.integration_adapter):
                _deliver_alerts(root, state, args.alert_adapter)
                core.save(root, state)
                print(json.dumps(core.continuation_directive(state), sort_keys=True)); return 2
            core.save(root, state)
            state = core.load(root); directive = core.continuation_directive(state)
        output = core.artifacts_path(root, state["run_id"]) / "continuation" / f"attempt-{attempt}.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([args.codex_bin, "exec", "-C", str(root), "--output-last-message", str(output), _prompt(directive)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            detail = core.redact((result.stderr or result.stdout or "agent runtime failed")[-4000:])
            core.block(state, "continuation_agent_failed", False, detail); core.save(root, state)
            _deliver_alerts(root, state, args.alert_adapter); core.save(root, state)
            print(json.dumps(core.continuation_directive(state), sort_keys=True)); return 2
        updated = core.load(root)
        if updated["current_loop"] == state["current_loop"] and updated.get("outcome") == state.get("outcome"):
            core.block(updated, "continuation_agent_no_transition", False, str(output.relative_to(root))); core.save(root, updated)
            _deliver_alerts(root, updated, args.alert_adapter); core.save(root, updated)
            print(json.dumps(core.continuation_directive(updated), sort_keys=True)); return 2
    raise SystemExit("continuation max-stages exhausted")


if __name__ == "__main__":
    raise SystemExit(main())
