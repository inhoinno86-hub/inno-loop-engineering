# Step 01 Prompt

## Goal

Replace implicit new-Codex planning bridge with explicit parent-host adapter protocol v2.

## Baseline

Current `main` includes commit `970b419`; use `main.md` as contract.

## Scope

Inspect and update `loop_engine/continuation_runner.py`, `loop_engine/cli.py`, `loop_engine/host_bridge.py`, `pyproject.toml`, and focused tests.

## Instructions

1. Remove the implicit `loop_engine.host_bridge` fallback and its entry point/module; retain only explicit command or environment configuration.
2. Make preflight invoke the explicit adapter with a non-mutating v2 capability payload and validate a version/request-id/ready response.
3. Require runner preflight before missing planning integrations are delegated.
4. Send lifecycle input descriptor, authorization, init-output lineage, remediation lineage, and active packet when present in integration payloads.
5. Keep retries limited to process/timeout/schema failures. Preserve fail-closed state handling.

## Constraints

Do not start a fresh `codex exec` for planning integrations. Do not revert `project-init` iteration `0` behavior. Avoid changing unrelated core validation.

## Expected Deliverable

Explicit v2 host-adapter boundary with no default bridge.

## Completion Criteria

- No production call resolves `loop_engine.host_bridge` by default.
- Missing adapter yields a terminal, descriptive block only when planning evidence is required.
- Capability preflight validates explicit v2 response without writing integration evidence.
- Integration request includes lifecycle lineage needed by the host.

## Next Step Handoff

Document exact v2 and active-host behavior in step 2.
