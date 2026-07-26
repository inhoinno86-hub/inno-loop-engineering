# Main Prompt Plan

## Request Summary

Execute the remaining requirements in
`intent-ruflo-inspired-epistemic-planning-health.md`. The prior implementation
added a partial ledger, trajectory retrieval, task declaration checks, and agent
health. Complete the missing lifecycle enforcement without adding Ruflo,
networked services, drift audit, vector search, or external dependencies.

## Overall Goal

Make known/unknown claims, evidence freshness, task preconditions/effects,
terminal/replan trajectories, and required-agent health first-class,
hash-bound, fail-closed Loop Engine controls.

## Constraints and Assumptions

- Baseline is current `main` (`b917a27`) unless explicitly changed.
- Preserve the four-loop state machine and legacy artifacts/runs.
- The existing untracked `scripts/sync_to_obsidian.py` is out of scope.
- Retrieval stays deterministic, local, bounded, and non-authoritative.
- Do not commit/push unless separately requested after review.

## Step Map

1. `step-01-ledger-contract.md` — finish the claim schema and provenance rules.
2. `step-02-plan-run-effects.md` — enforce preconditions and evidence-based
   effect transitions through plan/run/replan.
3. `step-03-trajectory-review.md` — require/record complete trajectory lineage
   for review outcomes and retrieval provenance.
4. `step-04-agent-health-validation.md` — integrate stale heartbeat, retry,
   quarantine, documentation, and end-to-end validation.

## Step Details

| Step | Purpose | Inputs | Outputs | Dependency | Completion criteria |
| --- | --- | --- | --- | --- | --- |
| 01 | Complete claim contract | intent, core state/artifacts | validated ledger schema | baseline | all required claim fields/provenance rules tested |
| 02 | Bind tasks to claims | step 01 ledger | plan/run/replan enforcement | 01 | stale/unknown preconditions and effects cannot bypass evidence |
| 03 | Persist outcome memory | review/replan artifacts | mandatory trajectory and safe retrieval records | 02 | terminal/replan summary lineage and non-authority tested |
| 04 | Make health operational | registry/heartbeat and prior steps | stale/retry/quarantine policy plus docs/tests | 01–03 | required unhealthy agents block; full suite passes |

The steps move from data validity to lifecycle enforcement, then persistent
outcome memory and operational health. This ordering prevents an execution or
review path from consuming a partially validated claim model.

## Completion Criteria Summary

- Claims include freshness, timestamps, conflicts, and evidence classification.
- High-impact unknowns cannot bypass plan/review completion.
- Effects are applied only from matching validation evidence; replan consumes a
  fresh ledger revision.
- Terminal and replan outcomes have hash-bound trajectory summaries; retrieval
  cannot satisfy facts, approvals, or gates.
- Stale required agents transition to fail-closed health outcomes with bounded
  retry/quarantine.
- Unit suite, compilation, CLI smoke checks, and diff review pass.
