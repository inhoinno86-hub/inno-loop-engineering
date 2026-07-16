---
name: project-loop-plan
description: Create the detailed root implementation plan for exactly one active milestone after Project Loop Roadmap approval. Use for approved milestone planning, replanning, or plan review. Do not execute the plan.
---

# Project Loop Plan

## Preconditions

- Validate project state.
- Require `ROADMAP_APPROVED` and exactly one active milestone.
- Read Charter, Design, Roadmap, project guidance, and `../../references/approval-policy.md`.

## Workflow

1. Confirm milestone outcome, scope, dependencies, non-goals, and observable Definition of Done.
2. Choose actual local date and lowercase kebab-case feature name. Create root plan using the global dated plan naming rule.
3. Include Planning Metadata with date, feature, artifact, planning mode, separate Superpowers planning and execution values, brainstorming value, and disabled Ouroboros note.
4. Include goal, discovered context, constraints, file map, ordered tasks, exact validation commands, rollback, execution skill policy, Progress Log, Decision Log, and open questions.
5. If Superpowers planning is explicitly enabled, use brainstorming then writing-plans. Global root location and metadata rules win over their default location.
6. Self-review for spec coverage, placeholders, path and symbol consistency, and executable validation.
7. Present plan and wait for explicit approval. Record approval in its Decision Log.
8. Transition to `PLAN_APPROVED` using `--active-plan`, `--superpowers-planning`, and separately approved `--superpowers-execution`.
9. Stop. Do not compile prompts or execute.

## Boundaries

One milestone maps to one active plan. Planning approval never implies execution approval. Material scope or architecture change returns to Roadmap approval.
