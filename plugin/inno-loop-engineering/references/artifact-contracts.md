# Artifact Contracts

Every state record has `run_id`, `input_hash`, `artifact_version`, `checkpoint`, `lifecycle_authorization`, `last_review_outcome`, `replan_history`, `max_replans`, `decision_log`, `assumption_log`, `epistemic_ledgers`, `trajectory_summaries`, `trajectory_retrievals`, `agent_health`, `verification_evidence`, `integration_evidence`, `input_packets`, `quality_gates`, `init_outputs`, `plan_revisions`, `execution_policy`, `prompt_package`, `run_report`, `validation_receipts`, `review_artifact`, and `remediation_packet`. Each run stores state and artifacts under `.loop-engine/runs/<run-id>/`; `current.json` selects the active run.

An explicit inno-loop request records `lifecycle_authorization` for its internally generated execution plan. It permits progression through plan, run, review, and replan without a separate plan-approval prompt. It never bypasses a safety `BLOCKED` gate.

For an inno-loop invocation, `project-init` and `project-plan` each record successful `ouroboros-interview`, `superpowers-brainstorming`, and `superpowers-writing-plans` entries. Each entry has its loop, tool name, status, relative artifact reference, and content hash. Missing or failed required integrations leave the lifecycle `BLOCKED`; no normal-Codex fallback is valid.

The continuation supervisor obtains those integrations through a host bridge. Protocol v1 requests include `protocol_version`, `request_id`, run/loop/iteration/attempt, active artifact root, required integration order, and the current input-packet ref/hash when one exists. A response must echo its protocol/version request ID and contain that same ordered result set. The supervisor writes a request/response receipt, verifies every referenced artifact through the shared core, and retries only transport/timeout/schema failures within its configured bound. The configured bridge is reused automatically at every init, plan, and replan stage. A missing host bridge blocks before a child worker can manufacture planning evidence.

Before either loop can complete, an immutable JSON input packet, three independent analysis artifacts, and a judge artifact must be recorded below the active run artifact root. A packet may define canonical requirements with stable IDs, source references, materiality, and category. When present, every analyst assesses every canonical requirement; distinct `requirements`, `risk`, and `adversarial` perspectives are evidence lenses, not competing requirement scopes. The judge stores analysis hashes and a matrix covering exactly that canonical set. Its consistency score remains a diagnostic; it must not block a canonical gate solely because perspectives surface different implementation details. Critical contradictions and unresolved human decisions block; implementation-contract-needed findings become plan obligations. Legacy packets without canonical requirements retain the historical threshold behavior.

The runtime agent adapter is leader-owned: it dispatches the three analysis
agents with the same packet and no sibling outputs, persists their returned JSON
under the active artifact root, then dispatches a distinct judge only after the
analysis hashes exist. The shared core never invents or selects a model; it
verifies the returned artifact provenance and decision only.

Init outputs bind the input-packet and judge hashes. Initial plan packets include all accepted init-output hashes; later plan packets additionally bind the active structured remediation packet. Every plan revision stores packet/judge/execution-plan/validation-matrix hashes and cannot satisfy another iteration.

`REPLAN` is nonterminal: it records a structured remediation packet with failed acceptance criteria/evidence, planned-versus-actual differences, root-cause or uncertainty, required correction, risk, non-deferrable status, and prior plan/review hashes; then it increments `replan_count`, advances `plan_iteration`, and re-enters `project-plan` immediately. Project-plan integration evidence is scoped to that iteration, so every retry must produce new planning artifacts. After `max_replans` automatic returns (default 3), another required return becomes `BLOCKED`.

Plans, prompts, and reports are versioned artifacts. An execution policy and
prompt package bind to the active execution-plan and validation-matrix hashes.
Run reports and validation receipts also bind to the prompt hash. A plan update
invalidates derived prompts and run/review evidence that refer to its previous
hash; they remain audit-only.

An Epistemic Ledger is an optional, hash-bound artifact scoped to the current
loop/iteration. It records `known`, `assumption`, `known_unknown`, and
`suspected_blind_spot` claims with evidence provenance, impact, owner, status,
task/criterion links. Claims also record timestamp, freshness (`stable`,
`volatile`, or `expired`) and links to conflicting active claims. Every source
declares whether it is primary evidence, a validation receipt, LLM output,
retrieval, or self-report. Active `known` claims require hash-verified primary
evidence or validation-receipt sources; LLM/retrieval/self-report alone is not
enough. When a plan has a current ledger, its execution plan binds the ledger
hash and every task declares precondition, success-effect, and failure-effect
claim IDs; high-impact active unknowns must map to both a task and criterion.

Trajectory summaries are immutable terminal/replan artifacts. Retrieval uses
only deterministic local tag matching, records its candidate hashes, and is
always `non_authoritative`: it cannot satisfy evidence, quality, or approval.
Agent-health records add bounded timeout/failure attempts and quarantine to the
registry. A required unhealthy agent follows the existing fail-closed block
policy; no self-organizing replacement is created.

The full-loop skill writes `charter.md`, `design.md`, `roadmap.md`, `execution-plan.md`, `validation-matrix.md`, `run-log.md`, and `review.md` under `.loop-engine/artifacts/`. Evidence references use paths relative to the project root.
