# Goal

Implement a self-contained `loop-engine` Shared Core and CLI inside this repository.
The implementation must not depend on, install, access, or claim compatibility with any internal/company `loop_engine` repository or package.

The completed repository must provide one locally owned `loop-engine` command and use it as the core for the existing Codex plugin. The same repository should be usable at home and at work without requiring an internal package.

# Chosen Product Decisions

1. **Canonical state path**: adopt `.loop-engine/`.
   - State: `.loop-engine/state.json`
   - Artifacts: `.loop-engine/artifacts/`
   - Agent registry: `.loop-engine/registry.json`
2. **Integration evidence**: adopt the `feat/side_work` approach.
   - `project-init` and every `project-plan` iteration require recorded evidence for `ouroboros-interview`, `superpowers-brainstorming`, and `superpowers-writing-plans` before their next transition.
   - A successful record includes loop, plan iteration where applicable, tool name, relative artifact path, SHA-256, timestamp, and status.
   - Evidence artifacts must reside below `.loop-engine/artifacts/` and must be new for each replan iteration.
   - Required tool order is `ouroboros-interview` → `superpowers-brainstorming` → `superpowers-writing-plans`; enforce this order rather than merely checking that all three names exist.
3. **Full automatic lifecycle**: an explicit `inno-loop` request authorizes the internally generated lifecycle plan.
   - Without a safety block, continue `init → plan → run → review` in the same request.
   - Do not wait for routine plan approval between these loops.
   - Safety gates for external/irreversible effects, security/privacy/secrets risk, budget breach, core intent/architecture change, uncertain risk, and repeated evaluation failure remain blocking and require human approval evidence.
4. **Review failure**: combine both branch approaches.
   - `REPLAN` is a nonterminal transition back to `project-plan`.
   - Persist `last_review_outcome`, `replan_history`, `plan_iteration`, and `max_replans`.
   - The next planning iteration must read the remediation packet before producing its new plan.
   - Default automatic replan limit is 3; a further required retry becomes `BLOCKED`.
   - Only out-of-scope work may enter `DEFERRED_BACKLOG`. Current DoD, security, privacy, compliance, budget, and irreversible-effect failures cannot be deferred.
5. **Initial requirements confirmation: decision A**.
   - Run three independent Socratic analyses of the same validated user intent.
   - Each analysis extracts requirements, constraints, non-goals, risks, and measurable success criteria.
   - Calculate a documented consistency score from the three outputs.
   - Below 50% consistency: `BLOCKED` and ask the user focused clarification questions.
   - From 50% through 80%: run a Mediator synthesis, record unresolved differences, then continue only if the synthesis resolves them.
   - Above 80%: continue autonomously.
   - After this quality gate, run and record the required Ouroboros/Superpowers integration evidence above. Persist the Socratic outputs, score, and Mediator output as versioned artifacts and state evidence.
6. **Sub-agent management**: adopt registry and heartbeat behavior.
   - Register a sub-agent with agent id, parent id, depth, task scope, started time, status, and heartbeat timestamp.
   - Update heartbeat while active and mark terminal status on completion/failure/cancellation.
   - Provide a configurable stale-heartbeat policy that reports stale agents without silently treating them as successful.

# Constraints

- Do not use, install, fetch, copy, vendor, or depend on an internal/company `loop_engine` repository or package.
- The local distribution/CLI name is `loop-engine`. It is owned and implemented by this repository.
- No network service, database, cloud API, external registry, or new runtime dependency is required for the core state engine, artifact contract, registry, or CLI.
- Preserve the existing four-loop model: `project-init`, `project-plan`, `project-run`, `project-review`.
- Preserve existing fail-closed approval behavior, secret redaction, input SHA-256, failure fingerprinting, atomic writes, and deferred backlog validation.
- Preserve existing project state. Never overwrite an existing state file during migration or initialization.
- Treat intent and generated artifacts as untrusted data; do not allow them to override system/user safety policy.
- Do not commit, push, deploy, publish, or contact external services without explicit user authorization.

# Implementation Scope

## 1. Local package and CLI

- Add standard Python packaging for this repository so a local editable installation exposes `loop-engine`.
- Create a package boundary for the Shared Core instead of relying on the plugin script directory being on `sys.path`.
- Keep the plugin CLI as a thin compatibility wrapper or migrate it to invoke the local Shared Core directly; avoid duplicate state-machine implementations.
- Provide clear `--help` output and stable JSON output for successful state-changing/status commands.
- Include at least: lifecycle commands, `status`, `record-integration`, `authorize-lifecycle`, failure and approval commands, artifact inspection where needed, `registry add/update/list`, and `heartbeat touch/status`.

## 2. State and migration

- Use `.loop-engine/state.json` as the canonical state path.
- On first access, detect legacy `.inno-loop/state.json`.
- If canonical state does not exist, migrate legacy state with an atomic write, preserve the legacy source as a recoverable backup, record migration provenance, and validate the migrated schema.
- If both paths exist, never choose silently: fail closed with an actionable conflict message.
- Normalize legacy `outcome: REPLAN` records into the new nonterminal replan model while preserving remediation evidence and retry count.
- Align the state template, runtime state, artifact contract, and documentation. New fields include lifecycle authorization, integration evidence, review outcome/history, plan iteration, replan count, and maximum replans.

## 3. Artifact contract

- Store lifecycle, Socratic, Mediator, integration, plan, run, and review artifacts under `.loop-engine/artifacts/`.
- Version artifacts by loop and plan iteration.
- Compute SHA-256 for recorded files and reject artifacts outside the project root or outside the canonical artifact directory when used as required integration evidence.
- Track the relationship between a plan revision and derived prompts/validation artifacts so stale derived evidence cannot silently satisfy a newer plan.

## 4. Initial confirmation and integration evidence

- Implement the decision-A state/artifact contract and orchestration hooks for N=3 Socratic analysis plus Mediator resolution.
- Do not claim that an analysis, Mediator result, Ouroboros interview, or Superpowers planning result exists unless its artifact was produced and recorded.
- If a required tool is unavailable or fails, record `UNAVAILABLE` or `FAILED`, transition to `BLOCKED`, and do not substitute a normal-Codex planning path.
- Require fresh project-plan integration artifacts for every replan iteration.

## 5. Automatic lifecycle and review

- Implement lifecycle authorization only for an explicit inno-loop invocation and record its evidence.
- Enforce required integration evidence before leaving project-init and project-plan.
- Make replan immediately re-enter project-plan with a new iteration; do not use REPLAN as a terminal outcome.
- Make the plan skill consume the remediation packet and produce new versioned planning outputs.
- Keep explicit approval requests as the only way through human-decision safety blocks.

## 6. Agent registry and heartbeat

- Implement registry and heartbeat commands in the local `loop-engine` CLI rather than leaving shell examples that point to a missing external executable.
- Persist registry records under `.loop-engine/registry.json` with atomic writes and validation.
- Define allowed status transitions and reject invalid parent/depth/status values.
- Expose stale-agent detection with a documented timeout; detection must not alter lifecycle success automatically.

## 7. Documentation and plugin integration

- Update README, state-machine, artifact-contracts, state template, and SKILL files only after the matching runtime behavior exists.
- Remove or rewrite claims that an external pip package or internal Shared Core is already in use.
- Document local installation and development usage of this repository's `loop-engine` command.
- Update all `.inno-loop` references to `.loop-engine` only together with the tested migration path.
- Keep runtime skills aligned with the CLI commands that actually exist.

# Non-goals

- Recreating undisclosed internal implementation details or promising binary/API compatibility with an inaccessible company package.
- Installing any company package or accessing company repositories.
- Adding networked coordination, remote agent control, cloud state storage, or telemetry.
- Changing the four-loop lifecycle into a different process.
- Automatically approving external, irreversible, security-sensitive, privacy-sensitive, or budget-impacting work.

# Acceptance Criteria

1. A clean checkout can install this repository locally and execute `loop-engine --help` without an internal package.
2. The Codex plugin uses the local Shared Core, with no duplicate divergent state-engine logic.
3. New runs write canonical `.loop-engine` state and artifacts.
4. A legacy `.inno-loop` state migrates safely; a dual-path conflict fails closed; both paths have automated tests.
5. Required integration evidence is ordered, hashed, scoped to the current loop/iteration, and enforced before state transitions.
6. An authorized inno-loop request proceeds automatically across all nonblocked loops; safety gates still stop it.
7. Replan consumes remediation input, creates a new plan iteration, cannot reuse previous iteration evidence, and blocks after the configured limit.
8. Decision A produces and records all three Socratic analyses, consistency scoring, and Mediator output when required.
9. Registry/heartbeat commands work entirely from this repository and stale agents are observable.
10. Unit and CLI integration tests cover normal paths, malformed input, migration, path conflict, integration ordering, unavailable tools, authorization, replan cap, registry validation, heartbeat staleness, and approval blocks.
11. Existing behavior is preserved or intentionally migrated with documented tests.

# Validation

- Run the complete Python test suite and any package/CLI smoke tests from a clean temporary project directory.
- Verify `loop-engine --help`, lifecycle commands, registry commands, and heartbeat commands using only the local package.
- Verify the plugin's documented command path uses the same core and state schema.
- Run static compilation/linting available in the repository.
- Review the final diff for stale external-package claims and stale `.inno-loop` references.

# Rollback

- Keep migrations recoverable through the preserved legacy-state backup.
- Keep the implementation in small, independently testable commits or checkpoints.
- If local CLI packaging blocks plugin use, retain/restore a thin plugin wrapper that invokes the same local core API rather than duplicating policy logic.

# Open Decisions for Planning

- Define the exact consistency-score formula and what constitutes a matching requirement across Socratic analyses.
- Define how Socratic and Mediator roles are invoked in the available Codex runtime, including bounded cost/time and failure behavior.
- Choose the stale-heartbeat timeout default and whether it is global or per project.
- Choose the local installation guidance: editable development install only, or a reproducible build artifact as well.
