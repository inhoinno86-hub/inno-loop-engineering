# Step 04 Prompt — Agent Health and Validation

## Goal

Make heartbeat-derived health, bounded retry/quarantine, documentation, and
verification complete.

## Baseline

Read main plan and prior steps. Inspect registry/heartbeat/core CLI/docs/tests.

## Scope

Health policy, CLI/docs/templates, regression tests, and verification.

## Instructions

Turn stale active heartbeats into recorded timeout health reports. Track
task/role identity, retry fingerprint, quarantine reason, and approved
alternative evidence. Required unhealthy agents block unless a valid alternative
is recorded. Update docs only to reflect implementation. Run all validation.

## Constraints

No swarm spawning, remote agents, or automatic approval. Leave the untracked
Obsidian script untouched.

## Expected Deliverable

Operational health implementation, current docs, passing verification output.

## Completion Criteria

- Stale required health fails closed and retries/quarantine are bounded.
- CLI/contracts/template document implemented fields.
- Full tests, compile, CLI help, and diff check pass.

## Next Step Handoff

Return final implementation summary and remaining risks.
