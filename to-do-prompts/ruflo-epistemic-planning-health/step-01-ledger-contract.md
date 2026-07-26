# Step 01 Prompt — Ledger Contract

## Goal

Make Epistemic Ledger claims complete, hash-bound, and provenance-safe.

## Baseline

Use current `main`; inspect `intent-ruflo-inspired-epistemic-planning-health.md`
and the current ledger code in `loop_engine/core.py`.

## Scope

Claim schema/state/template/CLI tests and artifact-contract documentation.

## Instructions

Require timestamp, freshness/volatility, conflict IDs, and source type. Verify
conflicts reference active claims. Distinguish primary evidence and validation
receipt sources; reject LLM/retrieval/self-report-only known claims. Preserve
legacy runs without a ledger.

## Constraints

No external store or model. Do not alter lifecycle authority.

## Expected Deliverable

Updated core validators, docs/template, and focused tests.

## Completion Criteria

- Invalid/missing provenance, conflict, and freshness values reject.
- Active known claims require qualifying evidence.
- Legacy no-ledger paths remain valid.

## Next Step Handoff

Expose stable claim records for task lifecycle enforcement.
