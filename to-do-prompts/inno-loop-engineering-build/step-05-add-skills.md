# Step 05 Prompt — Add Skills

## Goal

Provide clear Codex skills for init, plan, run, review, and status.

## Baseline

Use the validated command interfaces from step 04 on `main`.

## Scope

Create skill instructions and agent configuration only where needed.

## Instructions

Skills must identify required inputs and outputs, preserve the approval policy, report BLOCKED honestly, and treat Ouroboros/Superpowers as optional explicit integrations.

## Constraints

Skills must not claim to grant approval or bypass runtime preflight.

## Expected Deliverable

Skill directories with valid instructions referencing existing scripts.

## Completion Criteria

- Each of the five skills exists and points to an implemented command or read-only report.
- No skill references legacy `project-loop` paths.

## Next Step Handoff

Validate the complete plugin and fixture behavior.
