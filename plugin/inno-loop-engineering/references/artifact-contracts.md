# Artifact Contracts

Every state record has `run_id`, `input_hash`, `artifact_version`, `checkpoint`, `lifecycle_authorization`, `last_review_outcome`, `replan_history`, `max_replans`, `decision_log`, `assumption_log`, `verification_evidence`, `integration_evidence`, `input_packets`, `quality_gates`, `init_outputs`, `plan_revisions`, `execution_policy`, `prompt_package`, `run_report`, `validation_receipts`, `review_artifact`, and `remediation_packet`. Each run stores state and artifacts under `.loop-engine/runs/<run-id>/`; `current.json` selects the active run.

An explicit inno-loop request records `lifecycle_authorization` for its internally generated execution plan. It permits progression through plan, run, review, and replan without a separate plan-approval prompt. It never bypasses a safety `BLOCKED` gate.

For an inno-loop invocation, `project-init` and `project-plan` each record successful `ouroboros-interview`, `superpowers-brainstorming`, and `superpowers-writing-plans` entries. Each entry has its loop, tool name, status, relative artifact reference, and content hash. Missing or failed required integrations leave the lifecycle `BLOCKED`; no normal-Codex fallback is valid.

Before either loop can complete, an immutable JSON input packet, three independent analysis artifacts, and a judge artifact must be recorded below the active run artifact root. Each analysis has a distinct run ID, the packet hash, cited input hashes, empty `sibling_output_hashes`, tool/timestamp identity, and `requirements`, `constraints`, `non_goals`, `risks`, `acceptance_criteria`, and `ambiguities` sections. The judge stores analysis hashes and a weighted requirement matrix. Its score is recomputed from unanimous material weight; a critical-category contradiction blocks regardless of score. Scores 50–80 additionally require a Mediator bound to the judge hash and resolving every material difference.

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

The full-loop skill writes `charter.md`, `design.md`, `roadmap.md`, `execution-plan.md`, `validation-matrix.md`, `run-log.md`, and `review.md` under `.loop-engine/artifacts/`. Evidence references use paths relative to the project root.
