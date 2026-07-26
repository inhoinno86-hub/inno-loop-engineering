# Run/Review Execution Quality Implementation Plan

## Planning Metadata

- Date: 2026-07-25
- Feature name: run-review-execution-quality
- Planning artifact: PLAN-2026-07-25-run-review-execution-quality.md
- Planning mode: Superpowers
- Superpowers planning: enabled
- Superpowers execution: disabled
- Superpowers brainstorming: used
- Ouroboros: requested and used
- Notes: Explicit inno-loop lifecycle authorization covers the generated plan;
  execution-phase Superpowers remains separately opt-in.

## Goal

Make project-run and project-review fail-closed, plan-bound, measurable loops.

## Architecture

Extend `loop_engine.core` with canonical artifact validators and a single review
outcome evaluator. Add explicit CLI record/complete/defer commands that delegate
to that core. Update lifecycle skills, documentation, and tests only after the
runtime behavior exists.

## Tasks

### Task 1: Define state and plan/rubric schemas

- Modify `loop_engine/core.py` normalization and plan validation.
- Modify `plugin/inno-loop-engineering/assets/templates/state.json`.
- Require stable task, criterion, and validation IDs; mappings; weights; and
  current-plan lineage. Preserve historical artifacts as audit-only.
- Test duplicate IDs, missing mappings, stale revision references, and invalid
  rubric entries.

### Task 2: Implement run evidence contracts

- Modify `loop_engine/core.py` and `loop_engine/cli.py`.
- Add validated execution-policy, prompt-package manifest, run-report, and
  validation-receipt records bound to the active plan/matrix hash.
- Replace generic run completion with a validator that requires required tasks,
  prompt steps, and validation receipts.
- Test arbitrary evidence rejection, stale prompt rejection, and complete run
  acceptance.

### Task 3: Implement review evaluator and outcome transitions

- Modify `loop_engine/core.py` and `loop_engine/cli.py`.
- Add structured criterion results, review input lineage, reviewer independence,
  scorecard recomputation, hard-gate precedence, and validated `defer`.
- Make complete/replan/block/defer decisions validate current immutable evidence.
- Test all outcomes, forbidden defer, missing evidence, and non-overridable
  completion gates.

### Task 4: Update runtime skill contracts

- Modify `plugin/inno-loop-engineering/skills/inno-loop/SKILL.md`,
  `inno-loop-run/SKILL.md`, and `inno-loop-review/SKILL.md`.
- Encode `make-prompts -> exec-prompts`, explicit execution opt-in policy,
  required artifact recording, and independent review behavior.

### Task 5: Align documentation and templates

- Modify README and plugin references for artifact contracts, state machine, and
  approval policy only to reflect implemented behavior.
- Describe project-owner resume evidence without permitting completion bypass.

### Task 6: Verify end to end

- Extend unit and CLI tests in `plugin/inno-loop-engineering/tests/`.
- Run unit suite, compilation, CLI help, and clean-root complete/replan/blocked/
  deferred fixtures. Review the final diff.

## Constraints

- No external services or runtime dependencies.
- Preserve atomic writes, redaction, path checks, state migration, approvals,
  registry/heartbeat, and bounded replans.
- Do not commit or modify unrelated worktree changes.

## Validation

- `python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v`
- `python3 -m compileall loop_engine plugin/inno-loop-engineering`
- CLI help and clean temporary-root lifecycle fixtures.

## Rollback

Keep schema changes additive, retain old artifacts for audit, and revert only
files changed by this lifecycle.
