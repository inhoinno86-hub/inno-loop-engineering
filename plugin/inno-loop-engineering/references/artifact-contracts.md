# Artifact Contracts

Every state record has `run_id`, `input_hash`, `artifact_version`, `checkpoint`, `decision_log`, `assumption_log`, `verification_evidence`, and `remediation_packet`.

Plans, prompts, and reports are versioned artifacts. A plan update invalidates derived prompts that refer to its previous hash.

The full-loop skill writes `charter.md`, `design.md`, `roadmap.md`, `execution-plan.md`, `validation-matrix.md`, `run-log.md`, and `review.md` under `.inno-loop/artifacts/`. Evidence references use paths relative to the project root.
