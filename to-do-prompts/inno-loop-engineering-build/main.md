# Main Prompt Plan

## Request Summary

Build the new `inno-loop-engineering` system from `inno-loop-engineering-신규개발개요.md`, then replace the old `plugin/project-loop` implementation without compatibility or migration.

## Overall Goal

Deliver a validated Codex plugin that implements the four-loop lifecycle, critical-only approval gates, bounded retry/recovery behavior, durable state/evidence, and project-facing skills.

## Constraints and Assumptions

- Baseline is the current `main` filesystem state.
- `inno-loop-engineering-신규개발개요.md` is the functional source of truth.
- Create the replacement before removing `plugin/project-loop`.
- Do not preserve compatibility, migration, or dual-write behavior.
- Do not commit, push, publish, or deploy.
- Superpowers integrations remain optional; the implementation must work without them.

## Step Map

1. `step-01-scaffold-replacement.md` — create the replacement plugin structure and manifest.
2. `step-02-define-contracts.md` — add versioned state, policy, and artifact schemas.
3. `step-03-build-core-engine.md` — implement state, input validation, approvals, and recovery primitives.
4. `step-04-build-four-loops.md` — implement init, plan, run, and review transitions.
5. `step-05-add-skills.md` — expose the lifecycle through Codex skills and templates.
6. `step-06-test-and-validate.md` — add fixtures and run automated validation.
7. `step-07-cut-over-legacy.md` — remove the validated legacy implementation and stale prompt package.

## Step Details

Each step depends on all preceding steps. The replacement is scaffolded and validated first; contracts are then implemented, exposed as skills, exercised by tests, and only then used to justify the legacy cutover.

| Step | Purpose | Inputs | Outputs | Dependency | Completion criteria |
| --- | --- | --- | --- | --- | --- |
| 01 | Create plugin skeleton | overview, repository layout | `plugin/inno-loop-engineering` manifest and folders | none | manifest validates and contains no placeholders |
| 02 | Define contracts | overview | schemas, templates, policy references | 01 | all four loops and approval/retry rules are represented |
| 03 | Build core engine | contracts | Python lifecycle utility and tests | 02 | input, state, approval, checkpoint behavior is testable |
| 04 | Build loop commands | core engine | init/plan/run/review commands | 03 | valid transitions and failure paths match the overview |
| 05 | Add skills | commands and contracts | user-facing skills | 04 | skill instructions call only available scripts/contracts |
| 06 | Verify replacement | full plugin | tests and fixture evidence | 05 | plugin validation and lifecycle tests pass |
| 07 | Cut over | validated replacement | old plugin and stale package removed | 06 | only replacement implementation remains |

## Completion Criteria Summary

- A new manifest-backed plugin exists under `plugin/inno-loop-engineering`.
- Four loop commands enforce the documented state, approval, retry, and evidence contracts.
- Skills and tests cover normal completion, blocked approval, replan, malformed input, and recovery.
- Plugin validation and the test suite pass before cutover.
- `plugin/project-loop` and its old prompt package are removed only after the replacement passes validation.
