# Socratic Quality Gates Implementation Plan

## Planning Metadata

- Date: 2026-07-25
- Feature name: socratic-quality-gates
- Planning artifact: PLAN-2026-07-25-socratic-quality-gates.md
- Planning mode: Superpowers
- Superpowers planning: enabled
- Superpowers execution: disabled
- Superpowers brainstorming: used
- Ouroboros: requested and used
- Notes: Explicit Loop Engine lifecycle request authorizes init/plan integrations and execution of this lifecycle plan.

## Goal

Make `project-init` and every `project-plan` iteration execute and persist a
hash-bound Socrates-3 quality gate, then refuse lifecycle transitions unless
their accepted gate and bound output artifacts validate.

## Design Summary

Use an append-only, canonical JSON provenance packet bound to `(run_id, loop,
plan_iteration, packet_hash)`. A local runner interface creates three isolated
analysis artifacts from that packet, then judge and (when required) Mediator
artifacts. The core validates all persisted evidence and performs the threshold
decision; unavailable or failed required runner stages record redacted evidence
and block. Any semantic/provenance change creates a new packet and gate.

## Constraints

- No network service, model endpoint, new runtime dependency, or automatic risk approval.
- Preserve atomic writes, redaction, path validation, migration, integration ordering, registry, heartbeat, and replan cap.
- Plugin scripts remain compatibility wrappers over `loop_engine`.
- Keep existing unrelated dirty-worktree changes intact.

## Files

- Modify: `loop_engine/core.py` — schemas, runner protocol, artifact creation, quality decision, transition binding.
- Modify: `loop_engine/cli.py` — stable JSON commands for running and inspecting quality gates.
- Modify: `plugin/inno-loop-engineering/scripts/loopctl.py`, `scripts/loop_engine.py` only if wrapper coverage requires it.
- Modify: `plugin/inno-loop-engineering/tests/test_loop_engine.py`, `tests/test_loopctl.py`.
- Modify: README and artifact/state contract references to match actual runtime behavior.

## Tasks

### Task 1: Define provenance and quality records

- Add schema-versioned packet manifests with source role/path/hash and immutable tuple bindings.
- Normalize/migrate missing new fields without mutating valid historical evidence.
- Reject cross-run, cross-loop, cross-iteration, path-escape, duplicate-role, and hash-mismatch artifacts.
- Test canonical serialization and replay rejection.

### Task 2: Add fail-closed local quality-gate execution

- Introduce a dependency-free runner contract that receives only the immutable packet and role/run identity.
- Persist analysis/judge/Mediator invocation receipts and output hashes under the active artifact root.
- Create exactly three isolated analyses; judge derives the requirement matrix and weighted score; Mediator is called only for 50–80 without critical contradiction.
- Persist failure/unavailability diagnostics redacted, then block.
- Test identity/isolation, 49/50/80/81 boundaries, critical contradiction, and unresolved Mediator.

### Task 3: Bind init completion to accepted output artifacts

- Generate/validate canonical `charter`, `design`, and `roadmap` records with all required fields.
- Require packet/gate/run/iteration bindings and recompute hashes before `complete-init`.
- Test stale or malformed output rejection.

### Task 4: Bind initial plan and replan completion

- Require accepted init provenance for initial planning.
- Require structured remediation, previous plan revision, and review artifact provenance for replan input.
- Enforce current plan iteration and per-task source hashes in execution plans and validation matrices.
- Test stale plan evidence and malformed remediation packets.

### Task 5: Expose thin CLI and documentation

- Add JSON-stable commands to create, run, inspect, and validate gate records.
- Keep plugin CLI delegation-only; update help and documented artifact contracts.
- Test public command help from editable install.

### Task 6: End-to-end verification

- Run full Python suite.
- Exercise successful init/initial-plan and replan paths in clean roots.
- Verify every referenced artifact is inside the active run artifact root and hash-correct.
- Review diff for duplicate policy logic and stale evidence-only claims.

## Validation

- `python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v`
- clean editable-install `loop-engine --help` plus new command help
- clean-root initial-plan and replan CLI flows
- `python3 -m compileall loop_engine plugin/inno-loop-engineering`

## Rollback

Revert only files changed by this lifecycle. State migration remains additive;
no existing run state or artifacts are deleted.

## Progress Log

- 2026-07-25: Interview completed. All eight acceptance criteria mandatory; risk approval is human-only; every provenance/material change requires a fresh gate.

## Decision Log

- A material plan edit changes packet bytes, source semantics, or its binding tuple; cosmetic changes do not.
- The runner is dependency-free and fail-closed; it records invocation evidence rather than claiming unrecorded model conclusions.
