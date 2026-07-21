# Step 04 Prompt — Build Four Loops

## Goal

Implement init, plan, run, and review commands with the defined inputs, artifacts, and outcomes.

## Baseline

Use the core engine from step 03 on `main`.

## Scope

Create CLI entry points and tests for every loop and review regression.

## Instructions

Init creates intent baseline artifacts; plan freezes validation and task graph; run records evidence; review emits COMPLETE, REPLAN, BLOCKED, or DEFERRED_BACKLOG. REPLAN must route only to plan.

## Constraints

Do not invoke external effects from commands. Approval requests only record pending actions.

## Expected Deliverable

Four lifecycle commands and transition tests.

## Completion Criteria

- The happy-path fixture reaches COMPLETE.
- A failed review emits a remediation packet and transitions only to plan.
- Critical action and retry-limit fixtures produce BLOCKED.

## Next Step Handoff

Expose validated commands through skills.
