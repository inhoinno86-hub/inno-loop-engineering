# Step 01 Prompt

## Goal

Implement fail-closed plan/package/receipt/run validation and durable failure persistence.

## Scope

`loop_engine/core.py`, `loop_engine/cli.py`, focused tests.

## Completion Criteria

Unknown, duplicate, stale, missing, incomplete, or non-PASS required evidence cannot advance a run; a failing quality runner persists its block.
