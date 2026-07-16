---
name: project-loop-run
description: Execute or continue an explicitly approved Project Loop milestone plan through bounded prompt compilation, implementation, verification, review, and outcome loops. Use only after the user explicitly requests execution. Do not use for unapproved plans or status-only requests.
---

# Project Loop Run

## Preflight

1. Validate state and require `PLAN_APPROVED` or a resumable execution state.
2. Read active plan as source of truth. Confirm explicit execution request.
3. Read `../../references/{approval-policy,agent-contracts,document-contracts,state-machine}.md`.
4. Treat plan's Superpowers execution value independently. Apply no Superpowers execution skill unless enabled.

## Prompt Compilation

When staged prompts improve execution, invoke `$make-prompts`. Require `to-do-prompts/main.md` to contain active plan path and current SHA-256. Compare prompts to plan for scope, dependencies, validation, and completion criteria. Reject drift, regenerate, then transition to `PROMPTS_READY`.

## Execution

Invoke `$exec-prompts` as sole top-level coordinator. Do not stack `executing-plans` or `subagent-driven-development` as another coordinator. Approved Superpowers TDD, debugging, verification, and review skills are execution disciplines only.

Coordinator may create bounded workers under agent contract. No overlapping writers. After each result, re-read files and verify claims. Run spec review before quality review.

## Outcome Loop

1. Execute one next approved step and integrate it.
2. Run plan-defined verification.
3. Classify evidence:
   - `COMPLETE`: all Definition of Done and validation evidence pass.
   - `REWORK`: approved scope remains valid; implementation needs correction.
   - `REPLAN`: scope, architecture, dependency, or completion criteria must change.
   - `BLOCKED`: capability/input unavailable or repeated-failure limit reached.
4. Call transition CLI with evidence or normalized failure fields.
5. Stop after same failure three times, fifth rework user-review gate, any replan gate, or blocker.
6. On completion, request milestone closeout approval before selecting next milestone.

Never commit, push, merge, deploy, publish, delete, or manage branches without separate explicit approval.
