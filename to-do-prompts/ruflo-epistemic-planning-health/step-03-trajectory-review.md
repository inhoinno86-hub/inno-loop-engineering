# Step 03 Prompt — Trajectory Review Lineage

## Goal

Make terminal review and replan produce complete, immutable outcome memory.

## Baseline

Read main plan and prior step output. Inspect review completion and replan
transition paths.

## Scope

Trajectory schema, review/replan validation, retrieval, and tests.

## Instructions

Require trajectory fields for task tags, claim classifications, preconditions,
actions/validation references, outcome, failures/remediation, quality signal,
and input/plan/review/ledger hashes. Require a matching trajectory before a
ledger-enabled COMPLETE or REPLAN transition. Revalidate candidate artifact
hashes when retrieving across runs; retain non-authoritative status.

## Constraints

Do not let retrieval become proof or mutate a plan automatically.

## Expected Deliverable

Complete/replan trajectory enforcement with deterministic retrieval tests.

## Completion Criteria

- Ledger-enabled terminal/replan paths reject missing/stale trajectory.
- Retrieval records query/ranking/candidate hashes and rejects invalid sources.
- Retrieval cannot satisfy approval/evidence/gate requirements.

## Next Step Handoff

Keep outcome records available to operational health/documentation checks.
