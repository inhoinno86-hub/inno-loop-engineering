# Project Loop Plugin Design

## 1. Purpose

`project-loop` is a personal, globally available Codex plugin that standardizes project definition, planning, prompt compilation, execution, review, and milestone closeout.

The plugin preserves user control. It coordinates existing workflows but does not silently approve plans, enable Superpowers execution, expand scope, or run indefinitely.

## 2. Goals

- Establish one reusable project lifecycle across repositories.
- Keep project intent, design, roadmap, implementation plan, and execution prompts distinct.
- Use one coordinator as owner of sequencing, integration, validation, and state transitions.
- Create subagents only for bounded work where delegation improves speed or review quality.
- Make every loop iteration observable, bounded, resumable, and auditable.
- Provide a concise status report on explicit user request.
- Reuse `make-prompts`, `exec-prompts`, and explicitly approved Superpowers workflows.

## 3. Non-goals

- Running a permanently active autonomous agent team.
- Automatically modifying every repository when the plugin is installed.
- Replacing repository-specific `AGENTS.md` rules, tests, or safety policy.
- Replacing `make-prompts`, `exec-prompts`, or Superpowers skills.
- Automatically committing, pushing, merging, publishing, deploying, or deleting branches.
- Continuing after an approval gate, unresolved blocker, or loop limit.
- Adding MCP servers, apps, external services, or scheduled automation in version 1.

## 4. Architecture

The design uses an installable personal plugin containing four focused skills, reference contracts, deterministic validation scripts, and project-document templates.

The plugin is a workflow package, not a daemon. A main Codex thread invokes a skill, reads project-local state, performs an allowed transition, validates the result, and stops at the next required approval gate.

```text
User
  |
  v
project-loop skill
  |
  +-- reads project documents and .project-loop/state.json
  +-- invokes approved external workflows when applicable
  +-- creates bounded subagents when applicable
  +-- validates artifacts and transition
  +-- writes project-local state and status
  v
User approval or next allowed state
```

### 4.1 Plugin layout

```text
~/plugins/project-loop/
|-- .codex-plugin/plugin.json
|-- skills/
|   |-- project-loop-init/SKILL.md
|   |-- project-loop-plan/SKILL.md
|   |-- project-loop-run/SKILL.md
|   `-- project-loop-status/SKILL.md
|-- references/
|   |-- approval-policy.md
|   |-- agent-contracts.md
|   |-- document-contracts.md
|   `-- state-machine.md
|-- scripts/
|   |-- init_project_loop.py
|   |-- render_status.py
|   `-- validate_project_loop.py
`-- assets/templates/
    |-- charter.md
    |-- design.md
    |-- roadmap.md
    |-- state.json
    `-- status.md
```

Each skill also contains `agents/openai.yaml` for UI metadata. No plugin hook is included in version 1. Hooks may be considered only after real usage demonstrates a recurring omission that skills and validation scripts cannot handle reliably.

## 5. Skill Responsibilities

### 5.1 `project-loop-init`

Use for a new project or one that has not adopted the lifecycle.

1. Inspect repository and existing documentation.
2. Create missing directories and documents without overwriting user content.
3. Guide Charter, Design, and Roadmap definition and approval.
4. Initialize and validate `.project-loop/state.json`.
5. Stop at `ROADMAP_APPROVED` before implementation planning.

This skill may use Superpowers `brainstorming` only when explicitly approved for the current planning task. Otherwise it uses normal Codex planning.

### 5.2 `project-loop-plan`

Use when an approved roadmap has an active milestone ready for detailed planning.

1. Select exactly one active milestone.
2. Confirm outcome, scope, dependencies, and Definition of Done.
3. Create or update a valid root plan, for example `PLAN-2026-07-16-project-loop.md`.
4. Include planning metadata required by global Codex policy.
5. Record validation commands, rollback, risks, progress, and decisions.
6. Request plan approval.
7. Record Superpowers planning and execution as separate decisions.
8. Stop at `PLAN_APPROVED`.

When Superpowers planning is approved, this skill composes `brainstorming` and `writing-plans`. Global root-plan naming and metadata policy overrides Superpowers' default plan location.

### 5.3 `project-loop-run`

Use after a milestone plan is approved and execution is explicitly requested.

1. Verify approved plan and execution policy.
2. Invoke `make-prompts` when staged prompts are useful.
3. Validate that prompt files do not add scope or design decisions.
4. Invoke `exec-prompts` as sole top-level execution coordinator.
5. Apply only explicitly approved Superpowers execution workflows.
6. Run plan-defined verification and specification and quality review.
7. Classify result as `COMPLETE`, `REWORK`, `REPLAN`, or `BLOCKED`.
8. Update state, plan logs, decisions, and status.
9. Stop at milestone closeout approval or another user gate.

`project-loop-run` must not stack `exec-prompts` and a Superpowers execution coordinator. `exec-prompts` owns orchestration. Approved Superpowers skills supply disciplines such as TDD, debugging, verification, and review.

### 5.4 `project-loop-status`

Use for read-only project progress inspection.

1. Read authoritative documents and state.
2. Detect inconsistencies without silently repairing them.
3. Render current milestone, progress, evidence, blockers, risks, decisions needed, and next allowed action.
4. Avoid implementation, planning, approval, and state transitions.

## 6. Project-local Document System

```text
docs/project/CHARTER.md
docs/project/DESIGN.md
docs/project/ROADMAP.md
PLAN-2026-07-16-example-feature.md
to-do-prompts/main.md
to-do-prompts/step-*.md
.project-loop/state.json
docs/project/STATUS.md
```

The dated plan shown above is a naming example. Each active milestone uses its actual current date and lowercase kebab-case feature name.

### 6.1 Authority and ownership

| Artifact | Owns | Must not own |
|---|---|---|
| `CHARTER.md` | problem, users, goals, non-goals, success measures, constraints | implementation tasks |
| `DESIGN.md` | architecture, alternatives, interfaces, risks, decisions | milestone scheduling |
| `ROADMAP.md` | milestones, dependencies, outcomes, Definition of Done | code-level steps |
| Root dated plan | approved scope and method for one milestone | unrelated milestones |
| `to-do-prompts/*` | executable compilation of approved plan | new requirements or design decisions |
| `state.json` | machine-readable state and counters | narrative rationale |
| `STATUS.md` | human-readable derived snapshot | independent decisions or hidden state |

The active root plan is implementation source of truth. Prompt files are derived execution inputs. If they conflict, the plan wins and prompts must be regenerated.

### 6.2 Project `AGENTS.md`

Plugin does not create or modify project `AGENTS.md` by default. Repository commands, conventions, safety rules, and review expectations belong there. Writing it requires explicit user approval.

## 7. State Model

### 7.1 Primary states

```text
DRAFT
  -> CHARTER_APPROVED
  -> DESIGN_APPROVED
  -> ROADMAP_APPROVED
  -> PLAN_APPROVED
  -> PROMPTS_READY
  -> EXECUTING
  -> VERIFYING
  -> COMPLETE
```

Exception transitions:

```text
EXECUTING | VERIFYING -> REWORK | REPLAN | BLOCKED
REWORK -> EXECUTING
REPLAN -> ROADMAP_APPROVED after invalidating the active plan and prompts
BLOCKED -> prior valid state after explicit resume decision
COMPLETE -> ROADMAP_APPROVED after closeout approval selects the next milestone
```

### 7.2 State data

`.project-loop/state.json` contains at least:

```json
{
  "schema_version": 1,
  "project_id": "project-slug",
  "state": "DRAFT",
  "active_milestone": null,
  "active_plan": null,
  "superpowers_planning": "disabled",
  "superpowers_execution": "disabled",
  "iteration": 0,
  "rework_count": 0,
  "same_failure_count": 0,
  "last_failure_fingerprint": null,
  "resume_state": null,
  "last_transition_at": null,
  "last_verified_at": null,
  "blocked_reason": null
}
```

Timestamps use ISO 8601 with explicit offset. State updates use a temporary file followed by atomic replacement.

### 7.3 Transition invariants

- Advance only after required artifacts validate.
- Approval-dependent transitions require explicit user approval recorded in relevant Decision Log.
- `CHARTER_APPROVED`, `DESIGN_APPROVED`, and `ROADMAP_APPROVED` each require their corresponding approved document.
- Only one milestone and one root plan may be active.
- `PROMPTS_READY` requires prompt-to-plan consistency validation.
- `COMPLETE` requires evidence for every Definition of Done item.
- `STATUS.md` is derived and never determines state.
- Unknown schema versions fail closed with a migration-required message.

## 8. Execution Loop

```text
Load state and approved sources
-> validate preconditions
-> select one executable step
-> execute directly or delegate bounded work
-> integrate result
-> run required verification
-> run spec review
-> run quality review
-> classify outcome
-> persist evidence and transition
-> continue only when no approval gate or stop condition is reached
```

### 8.1 Outcome classification

- `COMPLETE`: all Definition of Done checks and validations pass.
- `REWORK`: approved scope remains valid, but implementation or tests need correction.
- `REPLAN`: scope, architecture, dependency, or completion criteria must change.
- `BLOCKED`: required input or capability is unavailable, or repeated-failure limit is reached.

### 8.2 Loop limits

- Stop as `BLOCKED` after same normalized failure occurs three consecutive times.
- Stop for mandatory user review after five total `REWORK` iterations for one milestone.
- At the five-iteration limit, remain in `REWORK` and prohibit execution until explicit user direction is recorded.
- Reset `same_failure_count` only when fingerprint changes or failure is resolved.
- Never convert failed or unexecuted verification into completion evidence.
- Never begin next milestone without closeout approval.

Failure fingerprints summarize failing command, exit class, and primary error identifier. They exclude secrets, volatile timestamps, and raw temporary paths.

## 9. Agent Model

Main thread is always Coordinator. It owns sequencing, integration, verification, state changes, and user communication.

| Role | Scope | Write permission |
|---|---|---|
| Investigator | search, dependency analysis, failure diagnosis | read-only by default |
| Implementer | one bounded plan task | assigned files only |
| Spec Reviewer | compare result with approved plan | read-only |
| Quality Reviewer | correctness, maintainability, tests, risks | read-only |

Delegation rules:

- Create subagents only when user requests delegation or active approved skill directs it.
- Prefer subagents for read-heavy exploration, isolated implementation, and independent review.
- Workers do not coordinate directly or decide state transitions.
- Do not run parallel writers on overlapping files.
- Coordinator re-reads affected files and validates worker claims.
- Each worker receives exact scope, expected output, and non-reversion constraints.
- Keep nesting depth at one; recursive fan-out is outside version 1.

## 10. Approval Policy

Explicit user approval is required for:

1. Design acceptance.
2. Roadmap acceptance.
3. Implementation plan acceptance.
4. Superpowers planning activation unless already explicitly requested.
5. Superpowers execution activation, separately from planning.
6. Scope, architecture, success metric, or Definition of Done changes.
7. Destructive, irreversible, external, publish, deploy, commit, push, merge, or branch actions.
8. Milestone closeout and transition to next milestone.
9. Resume from `BLOCKED` when resolution changes scope or assumptions.

Routine steps inside an approved plan do not need repeated approval unless repository policy requires it.

## 11. External Workflow Contracts

### 11.1 Superpowers

- Globally opt-in and task-scoped.
- Planning and execution approvals are independent.
- Planning may use `brainstorming` and `writing-plans`.
- Execution uses only skills appropriate to approved scope.
- Automatic branch completion, commit, worktree, merge, or publishing behavior is not inherited.
- Ouroboros remains disabled and is not part of design.

### 11.2 `make-prompts`

- Input: one approved active root plan.
- Output: `to-do-prompts/main.md` and ordered step files.
- Preserve scope, constraints, dependencies, validation, and completion criteria.
- Do not create product or architecture decisions.
- Regenerate prompts when plan changes materially.

### 11.3 `exec-prompts`

- Sole top-level execution coordinator beneath `project-loop-run`.
- Execute ordered steps and validate observable completion criteria.
- May delegate bounded subtasks under agent rules.
- Return evidence and outcomes; do not approve milestones.

## 12. Scripts and Deterministic Validation

### 12.1 `init_project_loop.py`

- Accept project root and slug.
- Create missing files from templates.
- Refuse to overwrite non-empty files unless explicit overwrite flag is supplied.
- Initialize valid schema version 1 state.
- Print created, preserved, and conflicted paths.

### 12.2 `validate_project_loop.py`

- Validate state schema and allowed states.
- Validate required documents for current state.
- Validate exactly one active milestone and plan where required.
- Validate plan metadata against global policy.
- Validate prompt presence and traceability from `PROMPTS_READY` onward.
- Validate loop counters and completion evidence.
- Exit nonzero with actionable diagnostics on failure.

### 12.3 `render_status.py`

- Read documents and state without changing workflow state.
- Generate `docs/project/STATUS.md` deterministically.
- Report inconsistencies rather than masking them.
- Exclude secrets and excessive raw command output.

Scripts use Python standard library only.

## 13. Error Handling and Recovery

- Missing documents: stop and identify earliest valid recovery state.
- Malformed state: preserve file, report errors, require explicit repair.
- State/document disagreement: fail closed; evidence and explicit approval determine repair.
- Partial script write: atomic replacement protects final state.
- Prompt drift: return to `PLAN_APPROVED`, regenerate, and revalidate.
- Verification failure: record command and concise evidence, then classify outcome.
- Worker conflict: Coordinator re-reads sources and asks user if material ambiguity remains.

## 14. Testing Strategy

### 14.1 Script tests

- Fresh and idempotent initialization.
- Existing-file preservation and overwrite refusal.
- Valid and invalid schemas and transitions.
- Required artifacts per state.
- Prompt drift detection.
- Same-failure and rework limits.
- Deterministic status rendering.
- Atomic state update behavior.

### 14.2 Skill validation

- Run standard validator for all four skills.
- Test trigger and non-trigger prompts.
- Confirm approval boundaries.
- Confirm status remains read-only.
- Confirm plan authority under conflicting inputs.

### 14.3 Plugin validation

- Run standard plugin validator.
- Verify all manifest paths.
- Install through personal marketplace development path.
- Confirm skills are discoverable in a new task.
- Run disposable project through initialization, planning, prompt compilation, one rework cycle, status, and completion.

## 15. Installation and Distribution

Initial target:

- Plugin path: `~/plugins/project-loop`
- Marketplace: `~/.agents/plugins/marketplace.json`
- Policy: available, authentication on install, category `Productivity`

Use installed `plugin-creator` workflow for scaffolding and validation. Do not expand global `AGENTS.md` with full loop specification. Cross-project workflow belongs in plugin skills and references.

## 16. Implementation Sequence

1. Scaffold plugin and personal marketplace entry.
2. Add contracts, state machine, approval policy, and templates.
3. Implement and test deterministic scripts.
4. Implement and validate init and status skills.
5. Implement and validate plan skill.
6. Implement and validate run skill and external workflow contracts.
7. Validate packaging and disposable end-to-end scenario.
8. Review installation behavior and record unresolved risks in implementation plan.

## 17. Acceptance Criteria

- Personal marketplace contains valid `project-loop` entry.
- Plugin passes standard validation.
- Four skills pass validation and are discoverable in a new session.
- Fresh sample project initializes without overwriting content.
- Invalid state and illegal transitions fail closed.
- Root plan remains authoritative over prompts.
- Planning and execution approvals remain separate and enforced.
- Loop limits stop repeated failure.
- Status reporting does not mutate workflow state.
- End-to-end sample reaches `COMPLETE` only with validation and Definition of Done evidence.

## 18. Deferred Decisions

- Plugin hooks.
- MCP integrations.
- Scheduled or unattended execution.
- Team marketplace distribution.
- Recursive agent teams.
- Automated Git branch lifecycle.

Each requires separate design and approval because it changes trust, permissions, or operating cost.
