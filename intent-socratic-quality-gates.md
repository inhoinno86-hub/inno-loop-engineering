# Goal

Implement quality-gated `project-init` and `project-plan` loops for the
repository-owned Loop Engine. This work closes the gap between the intended
Socrates-3/LLM-judge workflow and the current evidence-only state transitions.

This file is an explicit alternative lifecycle input. Invoke it with:

```text
intent-socratic-quality-gates.md를 기준으로 loop engine 수행 부탁해
```

# Product Intent

The engine must produce trustworthy project charters and execution plans, not
merely record that planning-tool artifacts exist. For each required quality gate,
three independent Socratic analyses examine the same structured input. A judge
compares the analyses by requirement meaning, identifies agreement, omissions,
and contradictions, and stores reproducible evidence. A Mediator resolves the
middle-confidence cases before the lifecycle can continue.

# Current Gaps To Close

1. `record_decision_a` accepts externally supplied analysis references and a
   score; it does not invoke three analyses, calculate a score, or invoke a
   Mediator.
2. `project-init → project-plan` only checks ordered integration evidence. It
   does not require validated charter/design/roadmap artifacts or prove that the
   plan consumed them.
3. A replan stores an evidence string but not a structured remediation packet:
   failed acceptance criteria, plan-versus-run difference, root cause, required
   change, risk, and validation evidence are absent.
4. `project-plan` has no explicit structured input contract, no plan revision
   lineage, and no judge gate before `project-run`.

# Required Behavior

## 1. Common Socrates-3 Quality Gate

- Run three independent analyses with distinct run IDs and role prompts.
- Each analysis must receive the same immutable, hash-bound input packet and
  must not read either sibling output before completion.
- Each analysis emits structured JSON/Markdown sections for: requirements,
  constraints, non-goals, risks, acceptance criteria, ambiguities, and cited
  input artifact hashes.
- Persist all three outputs below `.loop-engine/artifacts/`, including tool/run
  identity, input hash, timestamp, and SHA-256.
- A judge normalizes statements into semantic requirement IDs and classifies
  each as unanimous, two-of-three, unique, or contradictory.
- Calculate `consistency_score` as the sum of weights for unanimous material
  requirements divided by the sum of weights for all material requirements,
  multiplied by 100. Store the complete requirement matrix and weights; never
  store only a bare score.
- A security, privacy, irreversible-effect, compliance, budget, or core
  architecture contradiction is material regardless of numerical score.
- Below 50%: create focused clarification questions and enter `BLOCKED`.
- From 50% through 80%: run a Mediator synthesis. Continue only when it records
  every material difference as resolved; otherwise enter `BLOCKED`.
- Above 80% with no material contradiction: continue automatically.
- The judge and Mediator outputs are evidence artifacts, not unstored model
  conclusions. Tool failure/unavailability records `FAILED` or `UNAVAILABLE`
  and enters `BLOCKED`; there is no normal-Codex fallback.

## 2. Project-Init Input and Output Contract

Input packet contains the designated lifecycle input file plus its SHA-256 and
repository context facts used by the analyses.

After the common quality gate passes, generate and validate a hash-bound
`charter.md`, `design.md`, and `roadmap.md`. They must include goal, scope,
requirements, non-goals, assumptions, risks, safety/approval policy, measurable
success criteria, and open decisions.

`complete-init` must reject transitions unless these artifacts exist below the
canonical artifact root, validate against the init output schema, and are bound
to the accepted Socrates-3/judge result.

## 3. Project-Plan Input and Output Contract

Initial plan input contains the accepted init artifact hashes and the init judge
result. A replan input instead additionally requires a structured remediation
packet with:

- failed acceptance criteria and their evidence;
- planned-versus-actual run differences;
- root-cause or uncertainty classification;
- required correction, risk, and non-deferrable status;
- prior plan revision hash and review artifact hash.

Every plan iteration runs the same common Socrates-3 quality gate against its
own input packet. Prior iteration analysis/evidence may remain auditable but can
never satisfy a later iteration gate.

After the quality gate passes, create a versioned execution plan and validation
matrix. Each task must define scope, owner, dependencies, DoD, validation,
rollback, and source input/plan revision hashes.

`complete-plan` must reject transitions unless the plan input packet, quality
gate result, execution plan, and validation matrix are valid and bound to the
current `plan_iteration`.

## 4. State, CLI, and Plugin Contract

- Extend the canonical state schema with structured quality-gate records,
  input-packet hashes, judge result references, Mediator references, plan
  revision lineage, and structured remediation packets.
- Expose local `loop-engine` CLI commands needed to create, inspect, validate,
  and test these records. JSON output remains stable for successful commands.
- Keep the plugin CLI a thin wrapper over the local package; do not duplicate
  policy logic.
- Preserve atomic writes, redaction, fail-closed path validation, legacy state
  migration, safety approvals, integration ordering, replan cap, registry, and
  heartbeat behavior.

# Non-goals

- No internal/company package, repository, API, model endpoint, database, cloud
  service, remote agent controller, telemetry, or new runtime dependency.
- No automatic approval of an external, irreversible, security-sensitive,
  privacy-sensitive, compliance-sensitive, or budget-impacting action.
- No claim that a model analysis, judge, or Mediator result exists without a
  recorded artifact and invocation evidence.
- No change to the four-loop lifecycle model.

# Acceptance Criteria

1. Init invokes or records three independently identified Socratic analyses,
   produces a reproducible requirement matrix and consistency score, and blocks
   or mediates at the specified thresholds.
2. Init cannot transition until its accepted quality result and validated
   charter/design/roadmap artifacts are hash-bound to the input packet.
3. Initial planning consumes init artifact hashes; replan planning consumes a
   structured remediation packet and current plan iteration only.
4. Plan invokes the same Socrates-3/judge/Mediator gate for every iteration and
   cannot transition until its versioned plan/validation artifacts pass it.
5. Contradictions in critical categories block regardless of score; current DoD
   failures cannot be deferred.
6. Failed or unavailable required analysis/judge/Mediator tools fail closed and
   retain redacted diagnostic evidence.
7. Unit and CLI integration tests cover independent-run identity, input/hash
   mismatch, threshold boundaries, contradiction override, unresolved Mediator,
   stale plan evidence, malformed remediation packets, and normal/replan paths.
8. Existing migration, integration order, approval, registry, heartbeat, and
   package/CLI smoke tests remain passing.

# Validation

- Run the complete Python test suite.
- Run `loop-engine --help` and relevant new command help from a clean editable
  installation.
- Exercise one successful init/initial-plan path and one replan path in clean
  temporary project roots.
- Verify that every referenced artifact is inside `.loop-engine/artifacts/`, has
  the recorded SHA-256, and belongs to the active loop/iteration.
- Review the final diff for duplicate state-engine logic and stale claims that
  quality gates are merely recorded rather than executed.

# Safety

Do not commit, push, deploy, publish, contact external services, expose secrets,
or overwrite unrelated dirty-worktree changes without explicit user approval.
