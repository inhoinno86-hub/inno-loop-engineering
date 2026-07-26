# Step 02 Prompt — Plan and Run Effects

## Goal

Enforce claim preconditions at task execution and apply effects only through
matching evidence.

## Baseline

Read main plan and step 01 output. Inspect plan, execution policy, run report,
receipt, remediation, and replan validators.

## Scope

`loop_engine.core`, CLI if needed, and tests.

## Instructions

Require task claim mappings when an active ledger exists. Validate preconditions
before a task may be reported PASS. Require effect/failure-effect evidence links
and emit a new immutable ledger revision from receipts/run results. Require
high-impact unknown mapping or existing approval block; replan must consume the
latest ledger lineage.

## Constraints

Do not create a lifecycle state or let a worker self-certify a known fact.

## Expected Deliverable

Plan/run/replan validators and fixtures proving stale/invalidated claims fail.

## Completion Criteria

- Task PASS cannot bypass unsatisfied preconditions.
- Effects have validation provenance and revision lineage.
- High-impact unknowns cannot silently reach review/complete.

## Next Step Handoff

Provide terminal/replan ledger references for trajectory summaries.
