# Goal

Structurally upgrade the repository-owned Loop Engine so review distinguishes
whether a failure was caused by execution, by the plan, or by an unmet user
intent. Preserve the four-loop lifecycle (`project-init` → `project-plan` →
`project-run` → `project-review`), but make each review outcome return to the
correct loop with immutable, evidence-backed remediation.

Use this document as the lifecycle input for a future implementation request:

```text
intent-dual-axis-review-and-run-remediation.md를 기준으로 inno-loop 수행 부탁해
```

# Product Intent

The Loop Engine must not treat a run report, agent self-report, passing command
exit code, or an LLM verdict alone as proof that work is complete. `project-review`
is an independent, evidence-first decision point with two distinct evaluation
axes:

1. **Plan conformance**: whether `project-run` performed the current,
   hash-bound plan and achieved its declared task, criterion, and validation
   outcomes.
2. **Intent realization**: whether the project-level result satisfies the
   immutable baseline of the user's accepted intent from `project-init`, rather
   than merely satisfying a potentially incomplete current plan.

For a plan-conformance failure, review must classify the failure as one of:

- `execution_nonconformance`: the plan was adequately specified and executable,
  but the run did not perform or evidence it correctly. Return to `project-run`
  with a bounded execution remediation attempt.
- `plan_defect`: the plan is incomplete, contradictory, unexecutable, or cannot
  produce the required outcome. Return to `project-plan` with plan remediation
  and a new plan iteration.
- `indeterminate`: available evidence cannot reliably distinguish the two.
  Permit only a bounded, diagnostic execution attempt that seeks specified
  discriminating evidence; then escalate to `project-plan` or `BLOCKED` under
  the stated rules.

An intent-realization failure normally returns to `project-plan`. If new
evidence exposes an unresolved user decision, a changed intent, a core
architecture decision, or a safety-sensitive ambiguity, use the existing
human-decision `BLOCKED` path instead of silently changing intent or looping.

# Current Gaps To Close

1. Review currently evaluates only the active plan's validation matrix. A plan
   that omits a user requirement can therefore pass review without the missing
   requirement ever being evaluated.
2. The plan contract checks ID coverage, but does not require each protected
   init requirement to close through an implementable, observable vertical
   slice and independent validation.
3. A `PASS` task result and a passing validation receipt can be recorded with
   self-reported evidence references. They are not sufficiently linked to the
   task's declared DoD, actual output, and criterion-level outcome.
4. `REPLAN` always returns from `project-review` to `project-plan`. There is no
   safe, bounded retry path to `project-run` for a valid plan that was executed
   incorrectly.
5. Existing remediation describes a failure generally, but does not state the
   feedback axis, failure class, remediation target, run attempt, or the
   evidence needed to distinguish an execution error from a plan defect.

# Required Behavior

## 1. Immutable Intent Baseline and Vertical-Slice Traceability

- At accepted `project-init`, persist a hash-bound **intent acceptance baseline**.
  It derives from the canonical init requirements and contains stable intent
  requirement IDs, project-level observable outcomes, protection level,
  acceptance method, and evidence expectations.
- The baseline is immutable for the lifecycle run. A later plan may add detail
  but may not delete, weaken, or relabel an accepted intent requirement.
- Every protected baseline requirement must map to one or more current plan
  criteria and to at least one implementable vertical slice. A vertical slice
  must identify its task IDs, observable end-user/project outcome, DoD,
  dependency/precondition, validation IDs, and rollback/safety boundary.
- `complete-plan` rejects a plan when a protected baseline requirement lacks
  this complete mapping, even if all plan-local criteria are mapped to tasks.
- If a baseline requirement has become invalid because the user changed intent,
  do not mutate the baseline automatically. Record the conflict and enter the
  existing explicit approval/block path.

## 2. Evidence-First Run Contract

- Retain the current role of `project-run`: it executes the accepted plan. It
  does not decide lifecycle completion or select its own transition.
- A task result must bind to the active plan revision, prompt/execution package,
  task ID, declared DoD, criterion IDs, validation IDs, actual artifact/output
  references, executor identity, invocation/attempt ID, timestamps, deviations,
  and immutable evidence hashes or locations.
- Validation receipts must state the exact validation ID, command/procedure,
  inputs, result, exit status when applicable, executor, and immutable evidence
  references. A passing receipt may not prove an unrelated criterion merely by
  being present.
- The run report must contain a task-by-task planned-versus-actual account and
  may summarize evidence, but cannot replace the underlying task and validation
  receipts.
- Missing, stale, contradictory, or self-reported-only required evidence is
  `FAIL`, `INSUFFICIENT_EVIDENCE`, or `BLOCKED` as appropriate, never implicit
  `PASS`.

## 3. Dual-Axis Review

### 3.1 Plan-conformance feedback

- Review independently recomputes task/criterion/validation coverage from the
  active immutable plan, execution package, receipts, source changes or other
  declared outputs, and run report.
- It produces one cited verdict for each active plan criterion and task-level
  conformance findings where relevant.
- For every protected failure, review records a structured classification:
  `execution_nonconformance`, `plan_defect`, or `indeterminate`; cited evidence;
  alternative explanations; classification confidence; and the selected return
  target.
- An `execution_nonconformance` classification is permitted only when all of
  the following are evidenced:
  - the plan contains a complete, noncontradictory vertical slice for the
    affected requirement;
  - its required preconditions/dependencies were satisfied or explicitly
    provisioned;
  - the intended task/validation method is executable in the observed context;
  - evidence shows a material divergence, omission, or incorrect execution
    relative to that plan; and
  - remediation can state a changed execution method without adding/changing a
    task, criterion, dependency, scope, or intent requirement.
- A `plan_defect` classification is required when the evidence shows any of:
  incomplete vertical-slice coverage, false/missing precondition, contradictory
  task/criterion/validation definitions, an unexecutable validation method,
  or a correction that requires a new/changed task, criterion, dependency,
  scope, or acceptance method.
- Do not infer either class from the executor's self-report. Where the evidence
  is insufficient, classify `indeterminate`.

### 3.2 Intent-realization feedback

- Review independently evaluates every protected intent-baseline requirement
  against project-level output and cited evidence, even when the current plan
  omitted or weakened it.
- Intent-baseline verdicts and plan-criterion verdicts are separate named
  result sets in the review artifact. The review must expose their mappings,
  not collapse them into one score.
- A protected intent-baseline failure is non-deferrable and returns to
  `project-plan`, unless it requires human clarification or an existing safety
  block.
- `COMPLETE` requires all protected plan criteria and all protected intent
  baseline requirements to pass, as well as required validation evidence and
  existing safety/policy gates.

## 4. Bounded Project-Run Return

- Add a supervisor-selected transition from `project-review` to `project-run`
  for `execution_nonconformance` and the permitted diagnostic form of
  `indeterminate`. Workers still record submissions only; they must not choose
  the lifecycle transition.
- Add `run_attempt` as an immutable, monotonically increasing attempt identity
  within a plan iteration. A retry retains the plan revision hash but creates a
  fresh execution remediation packet, prompt package, run report, validation
  receipts, and review evidence. Older attempt evidence remains audit-only and
  cannot satisfy the current attempt.
- An execution remediation packet must bind to the prior review and plan hashes
  and include: affected task/criterion/validation IDs; planned-versus-actual
  difference; cited evidence; failure classification and confidence; allowed
  execution changes; prohibited plan changes; required discriminating evidence;
  retry validation; risk; and retry/escalation policy.
- `make-prompts` must consume the active plan, validation matrix, and execution
  remediation packet to create the fresh attempt-bound package. Its manifest
  binds the remediation hash, `run_attempt`, and prior package/run-report hashes
  and states the changed instructions, completion checks, and retry validation.
- `exec-prompts` executes only that current remediation-bound package. A retry
  may not silently reuse the same instructions when remediation requires a
  changed execution method; its receipts and run report bind to the active plan,
  package, remediation, and attempt hashes.
- Bound execution retries independently from plan replans. Repeated equivalent
  execution failures, a failed diagnostic attempt, newly discovered plan
  inadequacy, or inability to obtain required discriminating evidence escalates
  to `project-plan`. Existing safety, external-effect, budget, privacy, secret,
  and approval conditions remain `BLOCKED`.

## 5. Plan Replan and Remediation

- Retain `project-review → project-plan` for `plan_defect` and protected
  intent-realization failures. It increments plan iteration and requires fresh
  plan quality-gate/integration evidence under the existing lifecycle policy.
- The plan remediation packet must identify its feedback axis (`plan_conformance`
  or `intent_realization`), affected baseline requirement IDs where applicable,
  affected plan IDs, failure evidence, root cause or uncertainty, required
  correction, and the prior plan/review/run-attempt lineage.
- A replan must consume that packet and demonstrate how every non-deferrable
  finding is addressed. It cannot merely restate the old plan with new hashes.

## 6. Outcome and Deferral Rules

- Review chooses the transition deterministically from the validated review
  artifact and remediation packet(s); the executing worker never chooses it.
- Nonmandatory plan-local findings may enter `DEFERRED_BACKLOG` only when they
  do not violate any protected intent-baseline requirement, current DoD,
  security, privacy, compliance, budget, irreversible-effect policy, or
  mandatory/critical plan criterion.
- An unresolved classification, evidence conflict, or uncertain-risk finding
  must not be represented as a passing result. It follows the diagnostic retry,
  plan replan, or `BLOCKED` policy above.

# State, Artifact, and Documentation Requirements

- Extend canonical state with immutable intent-baseline records, run-attempt
  lineage, bounded execution-retry accounting, active execution-remediation
  packet, dual-axis review artifact references, and separate plan/intent
  verdict summaries.
- Keep previous plan revisions and run attempts auditable. Enforce hash binding
  so evidence from an older plan revision or run attempt cannot satisfy the
  active stage.
- Update core validation, CLI commands, continuation supervisor, state template,
  artifact contracts, state machine, skills, README, and tests together. The
  documented transition graph must exactly match executable behavior.
- Preserve the existing core ownership model: only the shared core validates
  artifacts and changes lifecycle state; stage workers produce evidence and
  submissions.

# Non-goals

- Do not replace the four-loop lifecycle or the existing init/plan quality
  gates, approval policy, hash/path validation, atomic writes, redaction,
  lifecycle authorization, or agent-independence requirements.
- Do not automatically mutate user intent, core architecture, scope, or safety
  policy based on a reviewer or executor conclusion.
- Do not treat an LLM verdict, agreement score, self-report, command exit code,
  or numeric score without cited immutable evidence as completion proof.
- Do not add a cloud service, external model endpoint, database, telemetry,
  remote controller, or new runtime dependency merely to implement this work.
- Do not permit an unbounded retry loop. Do not commit, push, deploy, publish,
  or perform external actions without explicit authorization.

# Acceptance Criteria

1. An accepted init produces an immutable, hash-bound intent acceptance baseline
   with stable IDs and protected project-level outcomes.
2. `complete-plan` rejects a plan that lacks complete baseline requirement →
   criterion → vertical slice → validation traceability.
3. Run evidence is attempt-bound and links every task result to its DoD,
   criterion/validation IDs, actual evidence, and executor provenance.
4. Review produces separate, complete plan-conformance and intent-realization
   verdict sets with immutable evidence references.
5. A demonstrated execution-only failure returns to `project-run` with a fresh,
   bounded execution-remediation attempt; it cannot reuse stale attempt evidence
   or silently repeat the prior instructions.
6. A demonstrated plan defect or protected intent failure returns to
   `project-plan` with structured remediation and a fresh plan iteration.
7. Insufficient evidence cannot be misclassified as execution failure. It
   follows the bounded diagnostic retry, plan-replan, or `BLOCKED` policy.
8. `COMPLETE` is rejected unless protected requirements on both review axes,
   required validation receipts, and existing safety/policy gates all pass.
9. `DEFERRED_BACKLOG` rejects any finding that affects a protected intent
   requirement or protected plan criterion.
10. Unit and CLI/integration tests cover normal execution retry, stale attempt
    rejection, repeated retry escalation, plan-defect replan, intent-baseline
    omission, ambiguous classification, blocked human decision, and existing
    complete/defer/replan compatibility paths.

# Validation

- Run the full unit and CLI integration test suite.
- Exercise clean lifecycle fixtures for: successful completion; valid-plan but
  failed execution followed by run retry; unexecutable plan followed by replan;
  omitted init requirement caught by intent review; indeterminate failure;
  bounded retry exhaustion; and a human-decision block.
- Verify all new records are inside the active run artifact root, hash-bound to
  their plan revision and run attempt, and rejected when stale or cross-linked.
- Verify stage workers cannot select `retry-run`, `replan`, `complete`, or
  `defer` directly.
