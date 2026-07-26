# Goal

Improve the repository-owned Loop Engine without replacing its four-loop
lifecycle. Adopt only two concepts inspired by Ruflo:

1. an evidence-first **Epistemic Ledger** with local trajectory/outcome memory;
2. explicit task preconditions/effects plus bounded **agent health** controls.

Do not add a read-only drift audit, Ruflo itself, a daemon, swarm runtime,
vector database, RAG service, remote coordination, or background workers.

This file is an explicit alternative lifecycle input. Invoke it with:

```text
intent-ruflo-inspired-epistemic-planning-health.md를 기준으로 loop engine 수행 부탁해
```

# Product Intent

The Loop Engine remains the sole control plane. Its shared core is the only
authority that validates artifacts, changes lifecycle state, requests approval,
or produces `BLOCKED`, `REPLAN`, `COMPLETE`, or `DEFERRED_BACKLOG` outcomes.

The new capabilities produce and validate local, hash-bound artifacts. They may
surface relevant prior outcomes, unknowns, preconditions, or agent failures, but
they must never autonomously approve work, alter a plan, execute a task, or turn
a retrieval result into a verified fact.

# Current Gaps To Close

1. `assumption_log` exists in state but has no typed, hash-bound, lifecycle-wide
   contract for facts, assumptions, unknowns, conflicts, ownership, freshness,
   or resolution evidence.
2. Analysis `ambiguities` and remediation `root_cause_or_uncertainty` are
   unstructured lists/text. A high-impact unresolved unknown cannot reliably
   block a relevant plan, task, or review criterion.
3. Past successful and failed run/replan outcomes are audit evidence only. The
   engine has no local, provenance-preserving way to retrieve relevant patterns
   as non-authoritative planning guidance.
4. Plan tasks describe dependencies but do not model their required world state
   (preconditions), the claims they create/change (effects), or which claim is
   invalidated after failure.
5. The registry and heartbeat report active/stale agents but do not define
   bounded health policy, retry accounting, or quarantine for repeatedly failing
   task roles.

# Required Behavior

## 1. Epistemic Ledger

Create a versioned, hash-bound ledger artifact scoped to the active run and
plan iteration. It contains claims with stable `claim_id` values and supports
at least these classifications:

- `known`: evidence-backed fact;
- `assumption`: accepted provisional premise;
- `known_unknown`: explicitly unanswered, decision-relevant question;
- `suspected_blind_spot`: adversarially discovered possibility that is not yet
  asserted as fact;
- `resolved`, `invalidated`, and `superseded`: terminal/history states.

Each active claim must include statement, classification, source artifact
references and hashes, confidence, impact, volatility/freshness, owner,
resolution method, linked task/criterion IDs where applicable, status, and
timestamp. Conflicting claims must link each other. No claim may cite artifacts
outside the active run root or artifacts whose hashes do not match.

`known` requires recorded primary evidence or a successful validation receipt.
An LLM output, prior-memory retrieval, agent self-report, or high numeric
confidence alone cannot create a `known` claim.

An unresolved `known_unknown` or `suspected_blind_spot` with high impact must
either:

- become a required plan task and validation/acceptance criterion; or
- enter an existing human-approval `BLOCKED` gate when it affects safety,
  security/privacy/secrets, irreversible action, compliance, budget, intent,
  or core architecture.

Low-impact unknowns may remain in the ledger only when they have an owner and a
revisit/resolution trigger. They must not silently satisfy a current mandatory
criterion.

## 2. Local Trajectory and Outcome Memory

Persist a compact, immutable trajectory summary at terminal review and at each
replan. It must bind the input/plan/review hashes and contain only structured
outcome data: task type/tags, relevant claim classifications, preconditions,
actions/validation references, outcome, failure class, remediation, and a
quality/result signal derived from current review evidence.

Provide local CLI/core operations to:

- record a trajectory summary;
- retrieve a bounded list of comparable prior summaries by explicit tags and
  deterministic local matching; and
- record the retrieval query, candidate IDs, ranking rationale, and hashes in
  the current planning artifact.

Initial retrieval may use dependency-free exact/tag matching. Do not add vector
search, embeddings, a database, an external endpoint, or opaque learned ranking.
Retrieved summaries are planning hints only. They must be labeled
`non_authoritative`, never bypass a quality gate, and never be used as direct
evidence for `known`, validation PASS, or approval.

## 3. Task Preconditions and Effects

Extend the versioned execution-plan task schema. Every task must declare:

- stable task ID, existing scope/owner/dependencies/DoD/rollback/validation
  mappings;
- `precondition_claim_ids`: claims that must be `known` or explicitly accepted
  assumptions before execution;
- `effect_claims`: claims created, resolved, invalidated, or superseded by a
  successful task; and
- `failure_effects`: claims invalidated or unknowns opened if the task fails.

Before a task starts, the core validates its precondition claims against the
current ledger. Missing, stale, invalidated, or unresolved high-impact claims
cannot be treated as satisfied. The result is a normal validation failure or an
existing `BLOCKED` safety outcome; it is not a new lifecycle state.

Task completion and validation receipts update the next immutable ledger
revision. A task cannot self-certify a `known` effect without the declared
validation evidence. A replan consumes the current ledger and its changed or
invalidated claims alongside the existing remediation packet.

## 4. Bounded Agent Health

Keep the existing leader-owned topology, registry, lease, heartbeat, and
three-independent-analysis quality gate. Do not introduce self-organizing
swarms, consensus as a lifecycle authority, automatic agent spawning, or remote
agents.

Add a local agent-health record per active run with role/agent identity,
assigned scope, start/heartbeat/end timestamps, attempts, timeout, failure
fingerprint, status, and optional quarantine reason. Allowed outcomes include
healthy, timeout, failed, unavailable, completed, and quarantined.

Define deterministic policy:

- a stale heartbeat marks an agent unhealthy; it never implies success;
- retries are bounded and recorded per task/role;
- repeated equivalent failures can quarantine that role for the current run;
- an unavailable, timed-out, or quarantined required agent records redacted
  evidence and follows the existing fail-closed `BLOCKED` policy when no
  approved alternative exists;
- a coordinator may use an approved alternative only if its scope, identity,
  evidence, and independence requirements remain valid.

Health records are observability and safety evidence, not a scoring mechanism
for approval, quality-gate acceptance, or task completion.

## 5. Loop Integration

- **project-init**: build the initial ledger from validated input and repository
  context. Independent analyses classify facts, assumptions, unknowns, and
  blind-spot candidates; the existing judge/mediator process resolves only its
  declared differences. It does not convert uncertainty to fact without cited
  evidence.
- **project-plan**: retrieve non-authoritative prior trajectories, record their
  provenance, produce a new ledger revision, and create task preconditions and
  effects. Required unknown-resolution work is included in the plan and
  validation matrix.
- **project-run**: validate preconditions before each task, record agent-health
  evidence, and write ledger updates only from recorded execution/validation
  evidence.
- **project-review**: independently verify the ledger transitions, confirm that
  mandatory high-impact unknowns are resolved or correctly blocked, and create
  a trajectory summary for complete or replan outcomes.
- **project-replan**: retain historical ledgers/trajectories as audit-only;
  create a fresh plan-iteration ledger from remediation and current evidence.

# Non-goals

- No read-only drift audit or harness-readiness scoring.
- No Ruflo installation, code dependency, MCP server, daemon, hook, swarm,
  background worker, federation, remote agent controller, or external service.
- No database, embeddings, vector store, RAG, telemetry, model endpoint, or
  new runtime dependency.
- No replacement of `project-init -> project-plan -> project-run ->
  project-review`, existing Socrates-3 quality gates, approval policy, atomic
  writes, artifact hashes, redaction, state migration, or bounded replan.
- No autonomous plan mutation, task execution, safety approval, or promotion of
  an LLM/retrieval output to verified evidence.

# Acceptance Criteria

1. State, artifact contracts, and CLI expose versioned, hash-bound Epistemic
   Ledger records with validated claim IDs, classifications, provenance,
   conflicts, status, freshness, ownership, and resolution links.
2. A `known` claim is rejected without evidence of the required quality; stale
   or invalidated claims cannot satisfy task preconditions.
3. High-impact unresolved unknowns are traceable to a required task/criterion
   or existing `BLOCKED` approval path; they cannot disappear at completion.
4. Prior trajectory retrieval is local, bounded, deterministic, provenance
   recorded, and explicitly non-authoritative.
5. Every current plan task has validated precondition/effect/failure-effect
   mappings; plan, run, review, and replan preserve their lineage.
6. Required validations, not agent self-reports, control claim resolution and
   task completion.
7. Agent health uses bounded retries, stale detection, and current-run
   quarantine while preserving the existing leader/independence rules and
   fail-closed handling of required-agent failures.
8. Unit and CLI integration tests cover malformed ledger artifacts, hash/path
   mismatches, claim conflicts, stale/invalidated preconditions, high-impact
   unresolved unknowns, retrieval provenance, task effect updates, timeout,
   retry/quarantine, required-agent block, normal completion, and replan.
9. Existing migration, quality-gate, integration-order, registry/heartbeat,
   approval, run/review, and deferred-backlog tests remain passing.

# Validation

- Run the full Python unit/CLI suite.
- Exercise clean-root init/plan/run/review and replan fixtures with ledger,
  trajectory, precondition/effect, and health records.
- Verify every new artifact remains inside the active run artifact root, has a
  recorded SHA-256, and binds to the active loop/iteration/plan revision.
- Verify that a retrieved trajectory cannot satisfy an evidence, approval, or
  quality-gate requirement.
- Verify high-impact unresolved unknowns cannot reach `COMPLETE`.
- Review the final diff for policy duplication, stale claims, and accidental
  Ruflo/runtime/service dependencies.

# Safety

Do not commit, push, deploy, publish, contact external services, expose
secrets, or overwrite unrelated dirty-worktree changes without explicit user
approval.
