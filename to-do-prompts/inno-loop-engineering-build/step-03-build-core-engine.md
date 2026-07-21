# Step 03 Prompt — Build Core Engine

## Goal

Implement deterministic lifecycle primitives for state persistence, input validation, approval gates, budgets, checkpoints, and recovery.

## Baseline

Use step 02 contracts on `main`.

## Scope

Implement standard-library Python scripts/modules and focused tests.

## Instructions

Reject malformed input before a loop starts. Enforce legal transitions and single-writer state updates. Record redacted evidence. Distinguish auto-resolvable from human-decision `BLOCKED` states.

## Constraints

No network execution, secret output, or legacy-state import.

## Expected Deliverable

A testable core engine and unit tests.

## Completion Criteria

- Invalid inputs, illegal transitions, and unknown risk fail closed.
- Checkpoint/resume and retry fingerprints are covered by tests.

## Next Step Handoff

Loop commands must call these primitives rather than duplicate policy.
