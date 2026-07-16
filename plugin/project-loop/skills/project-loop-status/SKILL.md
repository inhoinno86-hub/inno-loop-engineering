---
name: project-loop-status
description: Report current Project Loop milestone, evidence, blockers, risks, decisions, and next action without changing workflow state. Use for progress, checkpoint, or status requests in adopted projects. Do not use to plan or execute work.
---

# Project Loop Status

## Workflow

1. Locate project root and `.project-loop/state.json`.
2. Run `python3 ../../scripts/validate_project_loop.py validate --project-root <root>` from this skill directory. Preserve validation errors.
3. Capture state file bytes or digest before rendering.
4. Run `python3 ../../scripts/render_status.py --project-root <root>`.
5. Confirm state is unchanged.
6. Read `docs/project/STATUS.md` and report current state, milestone, evidence, blockers, risks, decisions needed, and next legal action.

## Read-only Boundary

Do not edit authoritative documents, record approvals, transition state, implement code, compile prompts, or silently repair inconsistency. Renderer may update only derived `STATUS.md`.
