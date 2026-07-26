"""Codex-hosted protocol-v1 bridge for required planning integrations.

This module deliberately delegates the integrations to a fresh Codex host process.
It never writes successful integration artifacts itself: the host agent must perform
the requested work and create the evidence, or report a failed result.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .core import REQUIRED_INTEGRATIONS
from .continuation_runner import BRIDGE_PROTOCOL_VERSION


def _failure(payload: dict, detail: str) -> dict:
    return {"protocol_version": BRIDGE_PROTOCOL_VERSION, "request_id": payload.get("request_id", "invalid-request"),
            "results": [{"name": name, "status": "FAILED", "detail": detail} for name in REQUIRED_INTEGRATIONS]}


def _prompt(payload: dict) -> str:
    root = payload["artifact_root"]
    stage = f"{payload['loop']} iteration {payload['iteration']}"
    names = ", ".join(payload["required_integrations"])
    return f"""You are the Loop Engine host bridge for {stage}. The user explicitly
requested this Loop Engine lifecycle, authorizing exactly these planning
integrations: {names}. Perform each integration in the specified order using the
installed runtime capabilities; do not substitute normal Codex planning.

For each successful integration, write its actual output beneath {root}/{payload['loop']}/
iteration-{payload['iteration']}/, using a distinct file. Do not run any lifecycle
transition, implementation, external action, or user communication. If an
integration is unavailable or fails, report FAILED or UNAVAILABLE with a concise
reason and do not fabricate an artifact.

Your final response must be only one JSON object, without Markdown, with exactly:
protocol_version {BRIDGE_PROTOCOL_VERSION}, request_id {payload['request_id']!r}, and
results in this order: {json.dumps(payload['required_integrations'])}. Each result
has name, status, and either artifact (for USED) or detail (for FAILED/UNAVAILABLE).
The artifact path must be relative to the project root."""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-engine-host-bridge")
    parser.add_argument("--codex-bin", default="codex")
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or payload.get("protocol_version") != BRIDGE_PROTOCOL_VERSION:
            raise ValueError("unsupported bridge protocol")
        if not isinstance(payload.get("required_integrations"), list) or payload["required_integrations"] != list(REQUIRED_INTEGRATIONS):
            raise ValueError("unexpected required integrations")
        if not isinstance(payload.get("artifact_root"), str) or not isinstance(payload.get("request_id"), str):
            raise ValueError("invalid bridge request")
    except (ValueError, json.JSONDecodeError) as error:
        print(json.dumps(_failure({}, str(error)))); return 0
    output = Path(payload["artifact_root"]) / "continuation" / f"host-bridge-{payload['loop']}-{payload['iteration']}-{payload['attempt']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run([args.codex_bin, "exec", "-C", str(Path.cwd()), "--output-last-message", str(output), _prompt(payload)],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900)
        if result.returncode:
            print(json.dumps(_failure(payload, (result.stderr or result.stdout or "Codex host bridge failed")[-1000:]))); return 0
        response = json.loads(output.read_text(encoding="utf-8"))
        print(json.dumps(response)); return 0
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(json.dumps(_failure(payload, str(error)))); return 0


if __name__ == "__main__":
    raise SystemExit(main())
