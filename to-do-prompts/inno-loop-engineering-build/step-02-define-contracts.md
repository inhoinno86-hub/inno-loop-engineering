# Step 02 Prompt — Define Contracts

## Goal

Encode the overview's state, evidence, approval, retry, and artifact rules as versioned references and templates.

## Baseline

Build on the replacement skeleton from step 01 on `main`.

## Scope

Create references for state transitions, approval policy, artifact contracts, runtime policy, and review outcomes. Create templates for authoritative state and reports.

## Instructions

Make the four current loops and four outcomes explicit. Include five approval categories, uncertain-risk fail-closed handling, numeric retry limits, and no-compatibility policy.

## Constraints

Keep schemas JSON-compatible and avoid importing legacy formats.

## Expected Deliverable

Readable reference Markdown and machine-readable templates.

## Completion Criteria

- References name all required states, outcomes, approval gates, and retry limits.
- State template has run, artifact, checkpoint, evidence, decision, and assumption fields.

## Next Step Handoff

The core engine must use these contracts as its only source of lifecycle behavior.
