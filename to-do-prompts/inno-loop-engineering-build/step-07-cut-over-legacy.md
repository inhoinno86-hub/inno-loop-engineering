# Step 07 Prompt — Cut Over Legacy

## Goal

Remove the obsolete `project-loop` implementation and its stale prompt package after replacement validation.

## Baseline

Use the passing replacement from step 06 on `main`.

## Scope

Remove `plugin/project-loop` and the old top-level `to-do-prompts` files that describe only the legacy plugin; retain the new request-specific prompt package.

## Instructions

Re-check exact targets before deletion. Do not remove unrelated project documents. Confirm no replacement file imports or references legacy paths.

## Constraints

This is an authorized clean break; do not create migration or compatibility shims.

## Expected Deliverable

Only the replacement plugin and its new prompt package remain.

## Completion Criteria

- `plugin/project-loop` no longer exists.
- Legacy top-level prompt files are removed while `to-do-prompts/inno-loop-engineering-build/` remains.
- Repository search finds no active legacy plugin references.
