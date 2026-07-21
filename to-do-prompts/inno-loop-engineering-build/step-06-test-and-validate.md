# Step 06 Prompt — Test and Validate

## Goal

Demonstrate that the replacement meets its lifecycle and safety contracts.

## Baseline

Use all replacement files from steps 01–05 on `main`.

## Scope

Run plugin validation and automated tests; add any missing fixture coverage.

## Instructions

Cover state legality, approval gating, retry/blocking, malformed input, checkpoint recovery, review-to-plan regression, and a disposable end-to-end completion.

## Constraints

Do not remove legacy files until all checks pass.

## Expected Deliverable

Passing validation output and test suite.

## Completion Criteria

- Plugin manifest validator succeeds.
- All replacement tests pass.
- Each required fixture has an observable assertion.

## Next Step Handoff

Only a successful validation permits legacy cutover.
