# Main Prompt Plan

## Request Summary

Repair lifecycle automation after commit `970b419`: preserve automatic loop transitions, but remove the default bridge that starts a new non-interactive Codex session for conversational planning integrations. Create and execute this package, then verify the proposed lifecycle tests.

## Overall Goal

Keep `project-init -> project-plan -> project-run -> project-review` automation while making the active parent host the only owner of Ouroboros/Superpowers planning work. An unattended runner may use only an explicitly configured, capable host adapter.

## Constraints and Assumptions

- Baseline is current `main` / `970b419`; do not overwrite unrelated dirty README or Confluence edits.
- Keep the independent `project-init` iteration `0` correction.
- Do not add a replacement process that starts a fresh `codex exec` for interactive planning work.
- Use a versioned adapter capability preflight before an unattended runner starts planning integrations.
- Preserve fail-closed behavior if no interactive host or valid adapter exists.

## Step Map

1. Define parent-host handoff and adapter protocol v2. Input: current runner/core contracts. Output: explicit adapter-only resolution, capability preflight, and lifecycle lineage payload. Depends on no prior step. Complete when no implicit bridge remains and preflight distinguishes configured/capable adapters.
2. Update lifecycle documentation and skill contract. Input: step 1 behavior. Output: accurate operator and active-host instructions. Depends on step 1. Complete when docs no longer promise a default new-Codex bridge.
3. Add regression coverage and run verification. Input: steps 1-2. Output: tests for missing adapter, capability preflight, lineage, retries, and existing lifecycle behavior. Depends on steps 1-2. Complete when full relevant suite passes and diff review finds no unrelated edits.

## Step Details

### Step 1 — parent-host-handoff

Purpose: replace implicit subprocess-host ownership with an explicit protocol-v2 adapter boundary.

Inputs: `loop_engine/continuation_runner.py`, `loop_engine/cli.py`, `loop_engine/core.py`.

Outputs: adapter capability preflight and request payload containing immutable lifecycle input plus init/replan lineage.

Completion: no default `loop_engine.host_bridge` resolution; runner blocks safely when planning needs an adapter; preflight invokes and validates a non-mutating v2 capability response.

### Step 2 — lifecycle-contract-docs

Purpose: align user-facing lifecycle and artifact contracts with parent-host ownership.

Inputs: step 1 behavior, README and plugin skill/reference docs.

Outputs: instructions for active-host integration and unattended explicit adapter operation.

Completion: no document claims a new Codex process can perform the interactive integrations; v2 fields and preflight semantics are described.

### Step 3 — regression-verification

Purpose: prove the repaired boundary with deterministic tests and a focused review.

Inputs: implementation and docs from steps 1-2.

Outputs: updated test coverage and command results.

Completion: tests cover adapter absence, capability failure, lineage, integration success/retry, and init iteration; all relevant tests pass.

## Connection

Step 1 establishes behavior. Step 2 publishes that behavior. Step 3 proves it. Plan based on current `main` unless user states otherwise.

## Completion Criteria Summary

- Implicit default bridge removed; init iteration fix retained.
- Only an explicit protocol-v2 adapter may run unattended planning integrations.
- Parent-host handoff payload carries source and prior-artifact lineage.
- Documentation matches implementation.
- Relevant test suite passes and diff preserves unrelated edits.
