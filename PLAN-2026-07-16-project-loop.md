# Project Loop Plugin Implementation Plan

> **For agentic workers:** Execute task-by-task only after explicit user approval. `exec-prompts` is the top-level coordinator. Approved Superpowers execution skills may provide TDD, debugging, verification, and review disciplines, but must not create a second coordinator.

**Goal:** Build and install a validated personal Codex plugin that manages a bounded, approval-gated project lifecycle from Charter through milestone completion.

**Architecture:** A personal plugin at `~/plugins/project-loop` contains four workflow skills, shared reference contracts, Markdown/JSON templates, and three standard-library Python CLIs. Project state stays in each adopted repository under `.project-loop/state.json`; `validate_project_loop.py transition` is the only plugin-provided state mutation path after initialization.

**Tech Stack:** Codex plugin and skill manifests, Markdown, JSON, Python 3 standard library, `unittest`.

---

## Planning Metadata

- Date: 2026-07-16
- Feature name: project-loop
- Planning artifact: PLAN-2026-07-16-project-loop.md
- Planning mode: Superpowers
- Superpowers planning: enabled
- Superpowers execution: enabled
- Superpowers brainstorming: used
- Ouroboros interview: disabled / not used
- Notes: Ouroboros is currently disabled in the global Codex configuration. Execution requires separate user approval. Git commits, branch operations, and publishing remain disabled unless separately requested.

## Approved Source

- Design specification: `docs/superpowers/specs/2026-07-16-project-loop-design.md`
- Design approval: user approved in the current thread on 2026-07-16.
- Installation target: personal plugin at `~/plugins/project-loop` and personal marketplace at `~/.agents/plugins/marketplace.json`.

## Context Discovered

- Current working directory is not a Git repository. Commit-oriented Superpowers steps do not apply unless the user later initializes or selects a repository and explicitly requests commits.
- No personal marketplace currently exists at `~/.agents/plugins/marketplace.json`.
- Installed creator tools:
  - `/home/inno/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py`
  - `/home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py`
  - `/home/inno/.codex/skills/.system/skill-creator/scripts/init_skill.py`
  - `/home/inno/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py`
  - `/home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py`
- Existing global `make-prompts` and `exec-prompts` skills remain external dependencies and must not be copied into this plugin.
- Superpowers is task-scoped and opt-in. Planning approval does not enable execution skills.

## Non-goals

- No hooks, MCP server, app connector, scheduler, unattended daemon, or recursive agent team.
- No automatic changes to global or project `AGENTS.md`.
- No replacement or modification of `make-prompts`, `exec-prompts`, or Superpowers.
- No automatic Git, deployment, publishing, or destructive operations.
- No team marketplace distribution in version 1.

## Assumptions

- Python 3 is available as `python3`.
- Plugin creator remains the authority for marketplace and manifest scaffolding.
- Skill and plugin validators remain available at the discovered paths.
- A new Codex task or restart may be required to observe newly installed plugin skills.
- Tests use disposable temporary directories and never initialize the current project as a managed sample.

## Constraints and Safety Rules

- Preserve all existing user files. Never use scaffold `--force` unless a reviewed conflict explicitly requires replacement.
- Do not hand-edit marketplace JSON during initial creation; use `create_basic_plugin.py --with-marketplace`.
- Use `apply_patch` for manual edits.
- Use Python standard library only.
- Never store approval solely in `state.json`; an approval record must exist in the corresponding document Decision Log.
- Never treat `STATUS.md` as authoritative.
- Never mark `COMPLETE` without validation evidence for all Definition of Done entries.
- Normalize failure fingerprints without secrets, timestamps, or volatile temporary paths.
- Keep worker agents bounded; Coordinator owns integration, verification, and state transitions.

## File Map

### Planning repository

- Existing: `docs/superpowers/specs/2026-07-16-project-loop-design.md`
- Existing/living: `PLAN-2026-07-16-project-loop.md`

### Personal plugin

- Create: `~/plugins/project-loop/.codex-plugin/plugin.json`
- Create: `~/plugins/project-loop/references/{approval-policy,agent-contracts,document-contracts,state-machine}.md`
- Create: `~/plugins/project-loop/assets/templates/{charter,design,roadmap,state,status}.md` except state template uses `state.json`
- Create: `~/plugins/project-loop/scripts/{init_project_loop,validate_project_loop,render_status}.py`
- Create: `~/plugins/project-loop/tests/{test_init_project_loop,test_validate_project_loop,test_render_status}.py`
- Create: `~/plugins/project-loop/skills/project-loop-{init,plan,run,status}/SKILL.md`
- Create: `~/plugins/project-loop/skills/project-loop-{init,plan,run,status}/agents/openai.yaml`

### Personal marketplace

- Create or update through creator: `~/.agents/plugins/marketplace.json`

## Command Interface Contract

The implementation must expose these stable commands:

```bash
python3 ~/plugins/project-loop/scripts/init_project_loop.py \
  --project-root /path/to/project \
  --project-id example-project

python3 ~/plugins/project-loop/scripts/validate_project_loop.py \
  validate --project-root /path/to/project

python3 ~/plugins/project-loop/scripts/validate_project_loop.py \
  transition --project-root /path/to/project \
  --to CHARTER_APPROVED \
  --approval-ref docs/project/CHARTER.md

python3 ~/plugins/project-loop/scripts/render_status.py \
  --project-root /path/to/project
```

All commands return `0` on success and nonzero on validation, conflict, or I/O failure. Diagnostics go to stderr; concise result summaries go to stdout.

## Task 1: Scaffold Personal Plugin and Marketplace

**Files:**

- Create: `~/plugins/project-loop/.codex-plugin/plugin.json`
- Create: `~/.agents/plugins/marketplace.json`
- Create directories: `~/plugins/project-loop/{skills,scripts,assets}`

- [x] **Step 1: Record pre-scaffold state**

Run:

```bash
test ! -e ~/plugins/project-loop
test ! -e ~/.agents/plugins/marketplace.json
```

Expected: both commands return `0`. If either fails, inspect and stop before overwriting.

- [x] **Step 2: Scaffold through plugin creator**

Run:

```bash
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py \
  project-loop \
  --with-skills \
  --with-scripts \
  --with-assets \
  --with-marketplace \
  --install-policy AVAILABLE \
  --auth-policy ON_INSTALL \
  --category Productivity
```

Expected: plugin directory and personal marketplace are created without `--force`.

- [x] **Step 3: Set manifest metadata**

Use a minimal version `0.1.0` manifest with:

```json
{
  "name": "project-loop",
  "version": "0.1.0",
  "description": "Run approval-gated project definition, planning, execution, review, and closeout loops.",
  "author": {"name": "inno"},
  "license": "UNLICENSED",
  "keywords": ["planning", "workflow", "project", "coordination"],
  "skills": "./skills/",
  "interface": {
    "displayName": "Project Loop",
    "shortDescription": "Approval-gated project delivery loop",
    "longDescription": "Define projects, plan one milestone, compile execution prompts, run bounded work, verify results, and report status.",
    "developerName": "inno",
    "category": "Productivity",
    "capabilities": ["Read", "Write"],
    "defaultPrompt": [
      "Initialize this repository with Project Loop.",
      "Plan the next approved Project Loop milestone.",
      "Show the current Project Loop status."
    ]
  }
}
```

- [x] **Step 4: Validate scaffold**

Run:

```bash
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  ~/plugins/project-loop
```

Expected: validator exits `0`.

**Completion criteria:** Valid plugin scaffold exists; marketplace entry points to `./plugins/project-loop`; no existing content was overwritten.

## Task 2: Add Contracts and Project Templates

**Files:**

- Create: `~/plugins/project-loop/references/approval-policy.md`
- Create: `~/plugins/project-loop/references/agent-contracts.md`
- Create: `~/plugins/project-loop/references/document-contracts.md`
- Create: `~/plugins/project-loop/references/state-machine.md`
- Create: `~/plugins/project-loop/assets/templates/charter.md`
- Create: `~/plugins/project-loop/assets/templates/design.md`
- Create: `~/plugins/project-loop/assets/templates/roadmap.md`
- Create: `~/plugins/project-loop/assets/templates/state.json`
- Create: `~/plugins/project-loop/assets/templates/status.md`

- [x] **Step 1: Write reference contracts from approved spec**

Required content:

- `approval-policy.md`: nine approval gates, task-scoped Superpowers policy, destructive-action policy.
- `agent-contracts.md`: Coordinator, Investigator, Implementer, Spec Reviewer, Quality Reviewer; bounded delegation and no overlapping writers.
- `document-contracts.md`: authority table, required headings, Decision Log format, prompt traceability marker.
- `state-machine.md`: states, legal transitions, prerequisites, counter rules, `BLOCKED` resume behavior.

- [x] **Step 2: Write usable templates**

Each Markdown template must include an `Artifact Status`, `Last Updated`, and `Decision Log`. Required domain sections:

```text
charter.md: Problem, Users, Goals, Non-goals, Success Measures, Constraints
design.md: Context, Chosen Design, Alternatives, Interfaces, Risks, Validation
roadmap.md: Milestones, Dependencies, Active Milestone, Definition of Done
status.md: Current State, Active Milestone, Evidence, Blockers, Risks, Decisions Needed, Next Action
```

`state.json` must match schema version 1 from the design, including `resume_state`.

- [x] **Step 3: Check references for drift and placeholders**

Run:

```bash
rg -n 'T[B]D|T[O]DO|implement later|fill in' ~/plugins/project-loop/references \
  ~/plugins/project-loop/assets/templates
```

Expected: no output. Template fill-in markers must use explicit instructional comments rather than ambiguous placeholders.

**Completion criteria:** Contracts fully encode approved design; templates are independently understandable; no duplicated or conflicting authority exists.

## Task 3: Implement Initialization CLI with Tests

**Files:**

- Create: `~/plugins/project-loop/scripts/init_project_loop.py`
- Create: `~/plugins/project-loop/tests/test_init_project_loop.py`

- [x] **Step 1: Write failing initialization tests**

Cover:

```python
def test_fresh_initialization_creates_expected_files(): ...
def test_second_run_preserves_existing_files(): ...
def test_nonempty_conflict_is_reported_without_overwrite(): ...
def test_explicit_overwrite_replaces_only_plugin_managed_targets(): ...
def test_invalid_project_id_is_rejected(): ...
def test_state_write_is_atomic(): ...
```

Tests invoke CLI through `subprocess.run`, use `tempfile.TemporaryDirectory`, and assert exact created/preserved/conflicted categories.

- [ ] **Step 2: Verify tests fail before implementation**

Run:

```bash
python3 -m unittest -v ~/plugins/project-loop/tests/test_init_project_loop.py
```

Expected: failure because CLI behavior is not implemented.

- [x] **Step 3: Implement minimal initialization CLI**

Required behavior:

- Resolve project root without requiring Git.
- Validate project ID against `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- Copy templates only when target is absent or empty.
- Preserve non-empty targets and return conflict exit status when required initialization cannot complete.
- Replace state template project ID and timestamp.
- Use `tempfile.NamedTemporaryFile` in target directory, `flush`, `os.fsync`, and `os.replace` for JSON.
- Expose `--overwrite`, defaulting to false. When true, replace only the documented plugin-managed target files and report each replacement; never replace unrelated paths.

- [x] **Step 4: Run tests**

Run:

```bash
python3 -m unittest -v ~/plugins/project-loop/tests/test_init_project_loop.py
```

Expected: all initialization tests pass.

**Completion criteria:** Fresh and repeated initialization behave safely; conflicts never overwrite content; JSON write is atomic.

## Task 4: Implement Validation and Transition CLI with Tests

**Files:**

- Create: `~/plugins/project-loop/scripts/validate_project_loop.py`
- Create: `~/plugins/project-loop/tests/test_validate_project_loop.py`

- [x] **Step 1: Write failing schema and artifact tests**

Cover valid schema, unknown schema, unknown state, missing document, malformed JSON, invalid counters, multiple active plans, missing plan metadata, and prompt package without plan traceability.

- [x] **Step 2: Write failing transition tests**

Cover every legal forward/exception transition and representative illegal transitions. Explicit tests:

```python
def test_approval_transition_requires_approval_ref(): ...
def test_approval_ref_requires_approved_decision_log_entry(): ...
def test_replan_invalidates_active_plan_and_prompts(): ...
def test_third_identical_failure_moves_to_blocked(): ...
def test_fifth_rework_requires_user_review_without_execution(): ...
def test_complete_requires_all_dod_evidence(): ...
def test_blocked_resume_requires_resume_state(): ...
```

- [ ] **Step 3: Verify tests fail**

Run:

```bash
python3 -m unittest -v ~/plugins/project-loop/tests/test_validate_project_loop.py
```

Expected: failures before implementation.

- [x] **Step 4: Implement `validate` subcommand**

Implement explicit Python dictionaries for schema fields, state prerequisites, and allowed transitions. Do not use third-party JSON Schema packages. Validation diagnostics must name JSON field or missing artifact and expected remedy.

- [x] **Step 5: Implement `transition` subcommand**

Required options:

```text
--project-root PATH
--to STATE
--approval-ref RELATIVE_PATH
--failure-command TEXT
--failure-class TEXT
--failure-id TEXT
--evidence-ref RELATIVE_PATH (repeatable)
--resume-state STATE
--active-milestone IDENTIFIER
--active-plan RELATIVE_PATH
--superpowers-planning enabled|disabled
--superpowers-execution enabled|disabled
```

Only accept options needed by target transition. Validate before and after mutation. Compute failure fingerprint with SHA-256 over normalized command, class, and ID. Persist atomically. On `REPLAN`, clear active plan and require prompt directory removal or archival by Coordinator before transition succeeds.

- [x] **Step 6: Run tests**

Run:

```bash
python3 -m unittest -v ~/plugins/project-loop/tests/test_validate_project_loop.py
```

Expected: all validation and transition tests pass.

**Completion criteria:** Invalid state and transitions fail closed; approvals require document evidence; loop limits and completion evidence are enforced deterministically.

## Task 5: Implement Read-only Status Renderer with Tests

**Files:**

- Create: `~/plugins/project-loop/scripts/render_status.py`
- Create: `~/plugins/project-loop/tests/test_render_status.py`

- [x] **Step 1: Write failing renderer tests**

Cover normal status, blocked status, inconsistent state, deterministic repeated output, secret-like value redaction, and state file byte-for-byte immutability.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python3 -m unittest -v ~/plugins/project-loop/tests/test_render_status.py
```

- [x] **Step 3: Implement renderer**

Renderer must first run equivalent validation logic without mutation, derive status from authoritative files, redact values matching common token/password/key assignments, and atomically replace only `docs/project/STATUS.md`.

- [x] **Step 4: Run renderer and full script suite**

Run:

```bash
python3 -m unittest discover -v -s ~/plugins/project-loop/tests -p 'test_*.py'
```

Expected: all tests pass.

**Completion criteria:** Status is deterministic, readable, redacted, inconsistency-aware, and state-preserving.

## Task 6: Implement Init and Status Skills

**Files:**

- Create: `~/plugins/project-loop/skills/project-loop-init/SKILL.md`
- Create: `~/plugins/project-loop/skills/project-loop-init/agents/openai.yaml`
- Create: `~/plugins/project-loop/skills/project-loop-status/SKILL.md`
- Create: `~/plugins/project-loop/skills/project-loop-status/agents/openai.yaml`

- [x] **Step 1: Initialize skill folders**

Run:

```bash
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  project-loop-init --path ~/plugins/project-loop/skills \
  --interface 'display_name=Project Loop Init' \
  --interface 'short_description=Initialize an approval-gated project lifecycle' \
  --interface 'default_prompt=Use $project-loop-init to initialize this project lifecycle.'
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  project-loop-status --path ~/plugins/project-loop/skills \
  --interface 'display_name=Project Loop Status' \
  --interface 'short_description=Report project-loop progress without mutations' \
  --interface 'default_prompt=Use $project-loop-status to report this project status.'
```

Expected: both skill directories contain `SKILL.md` and `agents/openai.yaml`. Do not generate example resources.

- [x] **Step 2: Write `project-loop-init` workflow**

Must inspect context, call initialization CLI, guide one approval boundary at a time, use transition CLI, stop at `ROADMAP_APPROVED`, and never enable Superpowers implicitly.

- [x] **Step 3: Write `project-loop-status` workflow**

Must invoke validation and renderer read-only path, report inconsistencies, and prohibit plan edits, implementation, approval recording, or state transitions.

- [x] **Step 4: Generate UI metadata and validate skills**

Run:

```bash
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/plugins/project-loop/skills/project-loop-init
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/plugins/project-loop/skills/project-loop-status
```

Expected: both exit `0`.

**Completion criteria:** Init stops at Roadmap approval; status is strictly read-only; both skills validate.

## Task 7: Implement Plan Skill

**Files:**

- Create: `~/plugins/project-loop/skills/project-loop-plan/SKILL.md`
- Create: `~/plugins/project-loop/skills/project-loop-plan/agents/openai.yaml`

- [x] **Step 1: Initialize skill folder and metadata**

Run:

```bash
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  project-loop-plan --path ~/plugins/project-loop/skills \
  --interface 'display_name=Project Loop Plan' \
  --interface 'short_description=Plan one approved roadmap milestone in detail' \
  --interface 'default_prompt=Use $project-loop-plan to plan the active milestone.'
```

Expected: plan skill contains `SKILL.md` and `agents/openai.yaml`. Its description must trigger only for detailed planning of one approved milestone.

- [x] **Step 2: Write plan workflow**

Required gates and rules:

- Require `ROADMAP_APPROVED` and exactly one selected milestone.
- Use actual-date root filename with lowercase kebab-case feature.
- Include all global planning metadata fields.
- Treat Superpowers planning and execution as independent values.
- When planning is enabled, compose brainstorming then writing-plans while retaining root filename policy.
- Require validation, rollback, Progress Log, Decision Log, and explicit user approval.
- Transition only after approval evidence exists.
- Stop at `PLAN_APPROVED`.

- [x] **Step 3: Validate skill**

Run `quick_validate.py` against plan skill. Expected: exit `0`.

**Completion criteria:** One milestone maps to one authoritative plan; global metadata and approval rules are enforced; skill validates.

## Task 8: Implement Run Skill and External Workflow Contracts

**Files:**

- Create: `~/plugins/project-loop/skills/project-loop-run/SKILL.md`
- Create: `~/plugins/project-loop/skills/project-loop-run/agents/openai.yaml`

- [x] **Step 1: Initialize skill folder and metadata**

Run:

```bash
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  project-loop-run --path ~/plugins/project-loop/skills \
  --interface 'display_name=Project Loop Run' \
  --interface 'short_description=Execute an approved plan through bounded loops' \
  --interface 'default_prompt=Use $project-loop-run to execute the approved milestone plan.'
```

Expected: run skill contains `SKILL.md` and `agents/openai.yaml`. Description must trigger only when user explicitly asks to execute an approved Project Loop plan or continue its bounded loop.

- [x] **Step 2: Write preflight and prompt compilation flow**

Require valid `PLAN_APPROVED`, explicit execution request, and separate Superpowers execution value. Invoke `make-prompts` only when useful. Require `main.md` to record active plan path and a digest of approved plan; reject scope drift before `PROMPTS_READY`.

- [x] **Step 3: Write coordinator flow**

Invoke `exec-prompts` as sole coordinator. Define delegation triggers, disjoint file ownership, worker result verification, spec review before quality review, and Coordinator-only transitions.

- [x] **Step 4: Write loop outcome flow**

Map evidence to `COMPLETE`, `REWORK`, `REPLAN`, or `BLOCKED`; call transition CLI; enforce repeated-failure and fifth-rework stops; request milestone closeout approval before next milestone.

- [x] **Step 5: Validate skill**

Run `quick_validate.py` against run skill. Expected: exit `0`.

**Completion criteria:** No coordinator stacking; prompt drift fails closed; execution approval is separate; loop stops are enforced; skill validates.

## Task 9: Plugin Validation and Disposable End-to-End Test

**Files:**

- Validate all plugin files.
- Create only temporary sample project paths under `mktemp -d`.

- [x] **Step 1: Run full unit suite**

```bash
python3 -m unittest discover -v -s ~/plugins/project-loop/tests -p 'test_*.py'
```

Expected: all tests pass.

- [x] **Step 2: Validate all skills and plugin**

Run all four `quick_validate.py` commands followed by:

```bash
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  ~/plugins/project-loop
```

Expected: all exit `0`.

- [x] **Step 3: Run disposable lifecycle scenario**

Scenario must demonstrate:

1. Fresh initialization.
2. Charter, Design, and Roadmap approvals using fixture Decision Logs.
3. Plan approval with separate planning/execution metadata.
4. Prompt traceability validation.
5. One simulated `REWORK` cycle.
6. Successful verification evidence and `COMPLETE`.
7. Status render with no state mutation.
8. Rejection of one illegal transition.

- [x] **Step 4: Verify marketplace entry**

Use JSON parsing, not text matching, to assert name, source path, installation policy, authentication policy, and category.

- [x] **Step 5: New-session discovery check**

Start a new Codex task or restart supported client. Confirm all four skill names are visible. If current tooling cannot automate this, record it as the only manual verification item rather than claiming success.

**Completion criteria:** Unit, skill, plugin, lifecycle, marketplace, and discovery checks pass or any manual-only check is explicitly documented.

## Validation Summary

Required before implementation completion:

```bash
python3 -m unittest discover -v -s ~/plugins/project-loop/tests -p 'test_*.py'
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/plugins/project-loop/skills/project-loop-init
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/plugins/project-loop/skills/project-loop-plan
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/plugins/project-loop/skills/project-loop-run
python3 /home/inno/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/plugins/project-loop/skills/project-loop-status
python3 /home/inno/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ~/plugins/project-loop
```

## Rollback Plan

Before execution, copy any pre-existing target paths to timestamped backups only if they unexpectedly exist; otherwise stop rather than overwrite. If a new installation must be rolled back:

1. Remove only the `project-loop` marketplace entry created by the plugin-creator update flow, not unrelated entries.
2. Move `~/plugins/project-loop` to a timestamped quarantine path rather than deleting it.
3. Leave project-local adopted documents intact; they are user data.
4. Restart Codex and verify the four skills are no longer discovered.

Marketplace rollback must use the plugin-creator documented update/reinstall path or a separately reviewed patch. No destructive rollback runs without explicit approval.

## Execution Skill Policy

- `exec-prompts`: required as top-level coordinator after prompt compilation.
- Superpowers execution: currently disabled.
- If separately approved, applicable disciplines may include TDD, systematic debugging, verification, and code review.
- `subagent-driven-development` and `executing-plans` must not become a second top-level coordinator beneath `project-loop-run`.
- `finishing-a-development-branch`, worktrees, commits, merge, push, and publishing remain manual-only and disabled for this plan.

## Progress Log

- 2026-07-16: Reviewed initial project workflow proposal and identified overlapping plan/execution responsibilities.
- 2026-07-16: User approved modular personal plugin architecture.
- 2026-07-16: Wrote and self-reviewed design specification.
- 2026-07-16: User approved design specification.
- 2026-07-16: Inspected installed creator tools, personal marketplace state, and official Codex customization model.
- 2026-07-16: Created this implementation plan. No plugin implementation started.
- 2026-07-16: User approved the implementation plan and explicitly enabled Superpowers execution.
- 2026-07-16: Execution discovery: state mutation needs transition options for active milestone, active plan, and separate Superpowers flags; added them without changing lifecycle scope.
- 2026-07-16: Created prompt package with approved plan SHA-256 and executed all nine steps through the coordinator workflow.
- 2026-07-16: Installed `project-loop@personal` version 0.1.0; CLI reports `installed, enabled`.
- 2026-07-16: Passed 14 Python tests, four skill validators, plugin validator, marketplace assertions, Python compilation, disposable lifecycle, and new-process explicit discovery of all four skills.
- 2026-07-16: Process deviation recorded: tests were added before final verification but their pre-implementation failing runs were not captured; those three historical-only checkboxes remain open and cannot be retroactively claimed.
- 2026-07-16: Removed generated Python bytecode from distribution, reinstalled final source snapshot, and confirmed source/cache equality plus `installed, enabled` status.

## Decision Log

- 2026-07-16: Use one personal plugin named `project-loop` instead of modifying existing global skills.
- 2026-07-16: Keep `exec-prompts` as sole top-level execution coordinator.
- 2026-07-16: Do not include hooks in version 1.
- 2026-07-16: Keep state project-local and status derived.
- 2026-07-16: Enforce state mutation through `validate_project_loop.py transition` so illegal transitions and atomic writes are deterministic.
- 2026-07-16: Use Python standard library and `unittest`; add no runtime dependency.
- 2026-07-16: Omit Git commit steps because current directory is not a Git repository and branch operations require separate approval.
- 2026-07-16: Execute through `exec-prompts` as sole coordinator with approved Superpowers TDD, debugging, verification, and review disciplines.

## Open Questions

None blocking implementation. New-session skill discovery may require manual confirmation in the active Codex client.
