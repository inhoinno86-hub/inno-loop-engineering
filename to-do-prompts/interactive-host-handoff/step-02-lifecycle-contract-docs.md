# Step 02 Prompt

## Goal

Publish accurate parent-host and unattended-runner lifecycle contracts.

## Baseline

Use step 1 implementation and current `main.md`.

## Scope

Update `README.md`, `plugin/inno-loop-engineering/skills/inno-loop/SKILL.md`, and `plugin/inno-loop-engineering/references/artifact-contracts.md` only as needed.

## Instructions

1. State that init/plan/replan integrations execute in active parent host when using `inno-loop`.
2. State that unattended continuation requires an explicit protocol-v2 adapter capable of a non-mutating preflight.
3. Describe payload lineage and fail-closed behavior.
4. Remove claims that installed Codex runtime is a default bridge or can host a conversational interview in a new process.

## Constraints

Do not alter unrelated README edits. Do not claim unavailable runtime behavior.

## Expected Deliverable

Docs matching implementation and safety boundary.

## Completion Criteria

- Docs distinguish active parent-host from unattended adapter.
- No stale protocol-v1/default-host claims remain.
- Operator commands use explicit host adapter configuration.

## Next Step Handoff

Add and run regression tests in step 3.
