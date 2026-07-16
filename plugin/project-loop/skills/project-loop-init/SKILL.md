---
name: project-loop-init
description: Initialize or adopt the Project Loop lifecycle in a repository, then guide Charter, Design, and Roadmap definition through explicit approval gates. Use for new projects or repositories without .project-loop/state.json. Do not use for implementation or status-only requests.
---

# Project Loop Init

## Workflow

1. Inspect repository guidance and existing project documents. Never overwrite content silently.
2. Run `python3 ../../scripts/init_project_loop.py --project-root <root> --project-id <slug>` from this skill directory. Use `--overwrite` only after explicit approval for named managed files.
3. Read `../../references/{document-contracts,approval-policy,state-machine}.md`.
4. Complete `CHARTER.md` with user input. Present it and wait for approval. Record approval in Decision Log, then call transition CLI to `CHARTER_APPROVED`.
5. Complete `DESIGN.md`, compare credible alternatives, present it, and wait for approval. Record and transition to `DESIGN_APPROVED`.
6. Complete `ROADMAP.md` with ordered milestones and observable Definition of Done. Select exactly one active milestone, wait for approval, record it, then transition to `ROADMAP_APPROVED` with `--active-milestone`.
7. Run validation and stop. Do not begin detailed planning.

Superpowers brainstorming is optional and task-scoped. Use it only after explicit approval. Do not infer Superpowers execution approval.

## Boundaries

- Main agent owns all transitions.
- Do not create or modify `AGENTS.md` without separate approval.
- Do not implement project code, compile prompts, or begin next skill automatically.
- On conflict or invalid state, stop with exact recovery action.
