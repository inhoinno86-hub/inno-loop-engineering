---
name: inno-loop-run
description: Start the bounded inno-loop execution phase after planning evidence exists.
---

# Inno Loop Run

After a versioned plan and validation matrix exist, create and record a
plan-bound execution-policy artifact, then create and record a prompt-package
manifest produced by `make-prompts`. Execute the accepted package with
`exec-prompts`; record every validation receipt and a structured run report.
Then record a `record-stage-submission --artifact <manifest>` whose only
artifact reference is that run report. The continuation supervisor validates the
manifest and calls `review --run-report <relative run-report artifact>`; the
worker must not invoke the lifecycle transition itself.

The package, receipts, and report must bind to the active plan and validation
matrix hashes. A prior plan revision's package is audit-only and cannot advance
the current run. Superpowers execution practices require task-scoped explicit
opt-in; absent opt-in uses normal Codex execution with the same evidence.

External effects, secrets, uncertain risk, and policy-limit breaches require a pending approval request and remain `BLOCKED`. Superpowers is optional and requires task-scoped opt-in.
