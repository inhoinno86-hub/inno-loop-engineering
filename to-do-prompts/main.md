# Project Loop Execution Prompts

## Request Summary

Implement the approved personal `project-loop` Codex plugin exactly as specified by `PLAN-2026-07-16-project-loop.md`.

## Overall Goal

Install and validate an approval-gated project lifecycle plugin with four skills, deterministic Python CLIs, templates, contracts, tests, and a personal marketplace entry.

## Baseline and Authority

- Baseline: current filesystem state; this directory is not a Git repository.
- Source of truth: `PLAN-2026-07-16-project-loop.md`.
- Active plan: `PLAN-2026-07-16-project-loop.md`.
- Plan SHA-256 after execution closeout: `b16fa03d8e5faeda1a0ea761d196e2a0e35ea401b9b42739c14dc4e237f417a8`.
- Initial compilation SHA-256: `105f30305843fc52ccc736368146126bfdbaca86f20c6b6226317f4fc3466693`.
- Design: `docs/superpowers/specs/2026-07-16-project-loop-design.md`.
- Superpowers execution: enabled by user on 2026-07-16.
- `exec-prompts` is sole top-level coordinator.

## Constraints

- Execute only approved plan scope.
- Preserve existing files; do not use destructive Git or filesystem operations.
- Use Python standard library only.
- Apply TDD for Python behavior.
- Validate worker claims locally; Coordinator owns transitions and completion.
- Do not commit, push, merge, publish, deploy, or add hooks/MCP/apps.

## Step Map

1. `step-01-scaffold-plugin.md`: create plugin and marketplace scaffold.
2. `step-02-add-contracts.md`: add references and templates.
3. `step-03-build-initializer.md`: implement initializer with tests.
4. `step-04-build-validator.md`: implement validation and transition CLI with tests.
5. `step-05-build-status.md`: implement read-only status renderer with tests.
6. `step-06-add-init-status-skills.md`: implement init and status skills.
7. `step-07-add-plan-skill.md`: implement planning skill.
8. `step-08-add-run-skill.md`: implement execution-loop skill.
9. `step-09-verify-plugin.md`: run full validation and disposable lifecycle scenario.

Steps are dependency ordered. Each step consumes outputs of all preceding steps. Exact requirements, commands, and completion criteria are the corresponding Task sections in the approved plan and are incorporated by reference without modification.

## Completion Criteria Summary

- Plugin and marketplace validate.
- All Python tests pass.
- All four skills validate.
- Disposable lifecycle covers approval, prompt traceability, rework, completion, status immutability, and illegal-transition rejection.
- Any new-session discovery check that cannot be automated is reported honestly as manual-only.
