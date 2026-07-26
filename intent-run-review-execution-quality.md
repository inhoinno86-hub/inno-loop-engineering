# Goal

Upgrade the repository-owned Loop Engine so `project-run` and
`project-review` are enforceable, traceable lifecycle loops rather than
evidence-string state transitions. Use this intent as the lifecycle input for
an inno-loop execution that improves the entire Loop Engine while preserving
the existing `project-init` and `project-plan` quality-gate work.

Invoke it explicitly with:

```text
intent-run-review-execution-quality.md를 기준으로 inno-loop 수행 부탁해
```

# Product Intent

`project-plan` produces the authoritative, hash-bound execution plan and
validation matrix. `project-run` must transform that plan into a versioned,
plan-bound prompt package through `make-prompts`, then execute that package
through `exec-prompts`. `project-review` must independently compare planned
criteria with observable execution evidence and select `COMPLETE`, `REPLAN`,
`BLOCKED`, or `DEFERRED_BACKLOG` using a reproducible rubric.

The system must separate:

- deterministic evidence checks from qualitative judgement;
- execution-plan quality from reviewer agreement;
- an implementation agent from the reviewer that approves its work; and
- normal Codex execution from task-scoped Superpowers execution opt-in.

## Local Continuation Runner and Output Gate

Add a dependency-free local continuation runner that invokes the installed local
Codex agent runtime one lifecycle stage at a time until `COMPLETE`,
`DEFERRED_BACKLOG`, or HIL `BLOCKED`. The initial cycle must execute
`project-init → project-plan → project-run → project-review`; every replan cycle
must execute `project-plan → project-run → project-review`. It captures worker
output under the active run artifacts and must not emit user-facing progress for
nonterminal stages. A failed or no-transition agent invocation records a
fail-closed `BLOCKED` artifact. Planning integrations are owned by the parent
runtime that has MCP authority: the child runtime must never invoke them
directly. The runner accepts an explicit host-owned integration-adapter command
that returns ordered, artifact-backed integration evidence; an absent or failed
adapter records an adapter-specific `BLOCKED` reason, never a fabricated
user-cancellation reason. This is a local adapter, not a remote controller, and
adds no runtime dependency.

# Current Gaps To Close

1. `project-run` can transition to review with an arbitrary evidence string;
   it does not require a plan-bound prompt package, step results, changed-file
   inventory, command results, validation evidence, or a structured run log.
2. The lifecycle skill describes implementation and testing, but never invokes
   or records the required `make-prompts -> exec-prompts` chain.
3. `project-review` records only a plan hash and unrestricted
   `acceptance_results`; it does not validate criterion IDs, verdicts,
   evidence references, quantitative scores, or reviewer independence.
4. `review-complete` can produce `COMPLETE` without a review artifact or proof
   that all mandatory criteria and validations passed.
5. The existing Socrates-3 runner/gate applies only to init and plan. Its
   consistency score measures analysis agreement, not implementation quality,
   so it cannot be reused as the review quality score.
6. Artifact contracts claim derived prompts are invalidated by plan changes,
   but state, CLI, and runtime validation do not model prompt lineage.
7. The documented `DEFERRED_BACKLOG` outcome has no corresponding validated
   transition or CLI behavior.

# Required Behavior

## 1. Strengthen the Project-Plan Contract

- Extend the versioned execution plan so every task has a stable `task_id`,
  owner, dependencies, scope, DoD, rollback, source input hash, and references
  to one or more acceptance-criterion IDs and validation IDs.
- Extend the validation matrix into a criterion rubric. Every criterion has a
  stable ID, description, weight, mandatory/critical classification, expected
  evidence type, validation command or procedure, and pass threshold.
- Reject plans with duplicate or unreferenced IDs, missing task-to-criterion
  mappings, missing validation mappings, invalid weights, or an empty required
  validation set.
- A new plan revision invalidates every prompt package, run evidence, and
  review artifact bound to an older plan revision. Historical artifacts remain
  readable for audit but cannot satisfy the current iteration.

## 2. Project-Run: Plan-Bound Prompt Generation and Execution

### 2.1 Execution policy and preflight

- Before prompt generation, create a versioned `execution-policy` artifact
  bound to the current plan and validation-matrix hashes.
- The policy identifies the coordinator, allowed worker/delegation topology,
  file/write scopes, concurrency/budget limits, safety constraints, and the
  selected execution practices for each task.
- `make-prompts` receives the authoritative plan, validation matrix, execution
  policy, and active plan hash; it must create a request-specific prompt
  package with a manifest that maps every prompt step to task IDs, criterion
  IDs, validation IDs, dependencies, write scope, and completion checks.
- Persist a hash-bound prompt-package manifest and immutable snapshot below the
  active run artifact root. A package made for another plan revision is stale
  and must be rejected or regenerated.
- `exec-prompts` reads only the accepted package for the active iteration. Its
  coordinator remains the single integration owner; workers are bounded,
  report to the coordinator, have disjoint write scopes, and never self-approve
  completion.

### 2.2 Superpowers execution-phase policy

- Superpowers execution is never inferred from `intent.md`, a plan, or a bare
  inno-loop invocation. It is enabled only when the user explicitly opts in
  for the lifecycle, and the execution-policy artifact records that approval.
- When opt-in is absent, use normal Codex execution while producing the same
  plan/prompt/run/review evidence contract.
- When enabled, select only practices that fit the task; do not force every
  skill. The preflight decision and rationale must be recorded per task:
  - `test-driven-development` for a feature or bugfix with testable behavior;
  - `systematic-debugging` when a failing behavior or test needs diagnosis;
  - `subagent-driven-development` or bounded parallel delegation only when
    tasks have independent scopes and a coordinator can retain integration
    control;
  - `using-git-worktrees` only when isolation is suitable and authorized;
  - `verification-before-completion` and `requesting-code-review` for the
    relevant completion/review checkpoint.
- A selected practice must be represented in the generated step prompt and
  its observed output must be recorded. An unselected practice has an explicit
  rationale; it is not silently claimed as used.

### 2.3 Required run evidence and exit gate

- For every executed prompt step, record task/step identifiers, prompt-package
  hash, start/end state, commands invoked, redacted outputs, changed files,
  observed completion checks, validation IDs, deviations, retries, blockers,
  checkpoints, and rollback action when used.
- Persist a structured `run-report` plus individual command/validation receipts
  under the active run artifact root. Each receipt is hash-bound to the plan
  revision and prompt package.
- `complete-run` must reject transition to review unless every required task is
  either evidenced as complete or has an explicit safety `BLOCKED` outcome;
  every mandatory validation has a recorded result; all evidence belongs to the
  active plan/prompt revision; and known deviations are classified.
- External, irreversible, secret, security/privacy, uncertain-risk, and limit
  breaches retain the existing approval/`BLOCKED` behavior. Do not hide them in
  prompt steps, run reports, or backlog entries.

## 3. Project-Review: Evidence-First, Independent Evaluation

### 3.1 Deterministic checks

- Build a review input packet from the active execution-plan hash,
  validation-matrix hash, prompt-package manifest hash, run-report hash,
  command/validation receipts, and changed-file inventory.
- First perform deterministic checks: current-plan lineage, criterion/task
  coverage, required evidence presence, command exit status, validation
  outcome, critical-category policy checks, and stale/missing artifact
  rejection.
- A missing required evidence item is a failed or blocked criterion, never an
  implicit pass and never an LLM-only decision.

### 3.2 Independent LLM-as-judge for qualitative criteria

- For criteria that cannot be decided mechanically, use one or more dedicated
  read-only review agents that did not implement the evaluated task. They may
  inspect the approved plan, source changes, test outputs, and run evidence but
  must not modify the project or communicate verdicts through the implementer.
- Each judge emits structured, hash-bound output per criterion: criterion ID,
  verdict (`PASS`, `FAIL`, `BLOCKED`, or `INSUFFICIENT_EVIDENCE`), cited
  evidence hashes/locations, reasoning summary, confidence, risk category, and
  recommended remediation where applicable.
- If multiple judges are used, a judge/mediator process reconciles material
  disagreement. Agreement is an audit signal only; it must not replace
  criterion evidence or become the execution-quality score.

### 3.3 Quantitative rubric and outcome rule

- Calculate and store at least these reproducible metrics:
  - mandatory-criterion pass rate, weighted by the approved rubric;
  - validation-evidence completion rate;
  - task/criterion traceability coverage rate;
  - prompt-step completion rate; and
  - unresolved qualitative-criterion count and confidence distribution.
- The score formula, weights, inputs, exclusions, and rounding are part of the
  versioned review artifact. Do not store a bare score.
- `COMPLETE` requires 100% mandatory-criterion pass rate, 100% required
  validation evidence completion, 100% required traceability coverage, no
  critical/high-severity unresolved finding, and no criterion marked
  `BLOCKED` or `INSUFFICIENT_EVIDENCE`.
- A current unmet mandatory criterion produces `REPLAN` with a structured,
  non-deferrable remediation packet. A policy, approval, budget, repeated
  evaluation, or uncertain-risk issue produces `BLOCKED`.
- `DEFERRED_BACKLOG` is permitted only for nonblocking, out-of-scope or
  lower-priority findings that do not violate a current DoD, security, privacy,
  compliance, budget, irreversible-effect policy, or mandatory criterion. A
  backlog record includes impact, rationale, owner, revisit trigger, and
  evidence references.

### 3.4 Completion and replan enforcement

- `review-complete` must validate the current structured review artifact and
  independently recompute the completion decision before recording `COMPLETE`.
- `replan` must require a validated review artifact and a structured
  remediation packet containing failed criterion IDs, actual-versus-planned
  differences, cited evidence, root cause or uncertainty, required correction,
  risk, non-deferrable status, and prior plan/review hashes.
- The next `project-plan` iteration consumes this remediation packet and must
  create a fresh plan, prompt package, run evidence, and review evidence.
- Add a validated `defer` transition/CLI path for allowed backlog items only.

## 4. State, CLI, Skills, and Documentation

- Extend the canonical state schema with plan-bound prompt-package records,
  execution-policy records, run-report records, command/validation receipts,
  review input/output records, rubric metrics, reviewer identity/independence
  records, and validated backlog entries.
- Add local `loop-engine` CLI commands to record, inspect, and validate these
  artifacts. Successful state-changing/status commands retain stable JSON
  output. Keep plugin scripts as thin wrappers over the repository-owned core.
- Update `inno-loop`, `inno-loop-run`, and `inno-loop-review` skills so the
  actual lifecycle invokes and records the new run/review contracts.
- Update `make-prompts`/`exec-prompts` integration guidance so a prompt package
  is plan-bound, versioned, and executable from the active artifact snapshot;
  do not rely on an ambiguous global `to-do-prompts/` directory alone.
- Align README, artifact contracts, state machine, templates, and tests with
  runtime behavior. Do not document a feature that is only an intended manual
  convention.

# Non-goals

- Do not replace the four-loop lifecycle, the existing init/plan Socrates-3
  quality gates, atomic writes, redaction, path validation, migration,
  approval policy, registry, heartbeat, or bounded replan behavior.
- Do not add an external model endpoint, database, cloud service, telemetry,
  remote agent controller, internal/company dependency, or new runtime
  dependency merely to support this work.
- Do not force Superpowers execution when the user did not explicitly opt in.
- Do not treat an LLM verdict, agent agreement, a worker self-report, or a
  numeric score without cited evidence as proof of completion.
- Do not commit, push, deploy, publish, contact external services, expose
  secrets, or overwrite unrelated worktree changes without explicit approval.

# Acceptance Criteria

1. A current execution plan and validation matrix contain stable, traceable
   task, criterion, and validation IDs with validated mappings and weights.
2. `project-run` cannot enter review without a current plan-bound prompt
   package created through `make-prompts`, execution through `exec-prompts`, a
   structured run report, and evidence for all mandatory validations.
3. Prompt packages and run evidence from a prior plan revision are rejected for
   the current iteration while remaining auditable.
4. The execution policy records whether Superpowers execution was explicitly
   enabled and, when enabled, records the task-appropriate selected practices,
   rationale, and observed results.
5. Review deterministically checks lineage, coverage, validation receipts, and
   policy conditions before any qualitative judge result is accepted.
6. Qualitative review judges are read-only and independent from implementation;
   their criterion-level verdicts cite immutable evidence and preserve
   confidence/disagreement data.
7. Review emits a reproducible weighted scorecard and can reach `COMPLETE`
   only under the stated mandatory pass, validation, traceability, and
   critical-risk gates.
8. `REPLAN`, `BLOCKED`, and `DEFERRED_BACKLOG` are mutually valid outcomes
   with enforced conditions; current mandatory/critical failures cannot be
   deferred.
9. Empty/arbitrary evidence strings cannot advance run completion or review
   completion.
10. Unit and CLI integration tests cover normal complete flow; stale prompt or
    run evidence; missing/failed validation; criterion mapping errors;
    qualitative judge disagreement; invalid completion; remediation/replan;
    permitted and forbidden defer cases; Superpowers opt-in/opt-out policy;
    and existing safety/migration/regression behavior.

# Validation

- Run the complete Python test suite and static compilation/linting available
  in the repository.
- Exercise clean temporary-project CLI flows for: plan -> prompt generation ->
  execution -> review `COMPLETE`; failed mandatory criterion -> `REPLAN` ->
  fresh plan iteration; critical/policy failure -> `BLOCKED`; and permitted
  nonblocking finding -> `DEFERRED_BACKLOG`.
- Verify every referenced artifact is below the active run artifact root,
  has a recorded SHA-256, and binds to the active plan iteration.
- Verify both Superpowers execution opt-in and normal-Codex opt-out paths meet
  the same evidence and review contracts.
- Review the final diff for stale evidence-string transitions, unbound global
  prompt packages, unsupported documentation, and accidental bypasses of the
  review rubric.

# Rollback

- Keep schema changes additive and normalize legacy records safely; never
  mutate or delete historical run artifacts merely because a newer plan exists.
- Make each contract/CLI/test/documentation change independently testable.
- Preserve compatibility wrappers only when they call the same local shared
  core and cannot diverge in lifecycle policy.

# Open Decisions for Project-Plan

- Decide the exact canonical JSON schema and stable ID format for task,
  criterion, validation, prompt-step, receipt, and reviewer records.
- Decide which deterministic checks are built into the core versus supplied by
  validated local runners, while retaining a dependency-free/fail-closed core.
- Decide the concrete weighted-score formula and whether any nonmandatory
  threshold is informational versus lifecycle-gating.
- Decide how a user explicitly grants Superpowers execution for a full
  inno-loop lifecycle without weakening the global task-scoped opt-in policy.
- Decide whether the review judge requires three independent reviewers for all
  qualitative criteria or a risk-based number with mandatory mediation for
  material disagreement.
