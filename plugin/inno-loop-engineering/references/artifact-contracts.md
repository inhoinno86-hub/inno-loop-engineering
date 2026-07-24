# Artifact Contracts

Every state record has `run_id`, `input_hash`, `artifact_version`, `checkpoint`, `lifecycle_authorization`, `last_review_outcome`, `replan_history`, `max_replans`, `decision_log`, `assumption_log`, `verification_evidence`, `integration_evidence`, and `remediation_packet`.

An explicit inno-loop request records `lifecycle_authorization` for its internally generated execution plan. It permits progression through plan, run, review, and replan without a separate plan-approval prompt. It never bypasses a safety `BLOCKED` gate.

For an inno-loop invocation, `project-init` and `project-plan` each record successful `ouroboros-interview`, `superpowers-brainstorming`, and `superpowers-writing-plans` entries. Each entry has its loop, tool name, status, relative artifact reference, and content hash. Missing or failed required integrations leave the lifecycle `BLOCKED`; no normal-Codex fallback is valid.

`REPLAN` is nonterminal: it records the remediation packet and review result, increments `replan_count`, advances `plan_iteration`, and re-enters `project-plan` immediately. Project-plan integration evidence is scoped to that iteration, so every retry must produce new planning artifacts. After `max_replans` automatic returns (default 3), another required return becomes `BLOCKED`.

Plans, prompts, and reports are versioned artifacts. A plan update invalidates derived prompts that refer to its previous hash.

The full-loop skill writes `charter.md`, `design.md`, `roadmap.md`, `execution-plan.md`, `validation-matrix.md`, `run-log.md`, and `review.md` under `.inno-loop/artifacts/`. Evidence references use paths relative to the project root.
