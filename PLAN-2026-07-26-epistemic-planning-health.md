# Epistemic Planning and Agent Health Implementation Plan

## Planning Metadata

- Date: 2026-07-26
- Feature name: epistemic-planning-health
- Planning artifact: PLAN-2026-07-26-epistemic-planning-health.md
- Planning mode: normal Codex
- Superpowers planning: disabled
- Superpowers execution: disabled
- Superpowers brainstorming: not used
- Ouroboros: not requested / not used
- Notes: `vault-update` was explicitly requested but its advertised SKILL.md is
  unavailable at `/home/inno/.agents/skills/vault-update/SKILL.md`. The plan
  uses normal Codex implementation and does not invoke that missing workflow.

## Goal

Implement the approved Ruflo-inspired, local-only additions defined by
`intent-ruflo-inspired-epistemic-planning-health.md`:

1. evidence-first Epistemic Ledger plus non-authoritative local trajectory
   retrieval;
2. task preconditions/effects plus bounded agent-health policy;
3. no Obsidian vault sync work in this implementation.

## Context Discovered

- `loop_engine.core` owns state, artifact hashes, lifecycle transitions,
  registry, heartbeat, fail-closed blocks, and review/replan enforcement.
- Existing `assumption_log` is untyped and does not control task readiness.
- The execution plan already has stable task, criterion, and validation IDs,
  so claim links can be validated against the active plan revision.
- The existing untracked `scripts/sync_to_obsidian.py` imports an unrelated
  package; the user explicitly excluded it from this implementation scope.
- No vault root/configuration exists in this repository. External writes must
  require an explicit user-provided path; no guessed vault location is allowed.

## Non-goals

- Ruflo installation or dependency; daemon, MCP, hooks, swarm, federation,
  remote agents, background workers, RAG, embeddings, vector DB, telemetry,
  or external model calls.
- Read-only drift audit/harness-readiness scoring.
- Any change to the four-loop lifecycle or existing human-approval categories.
- Automatic promotion of a retrieval result, agent output, or self-report to a
  verified fact.
- Automatic sync to an external vault without an explicit vault path.

## Constraints and Safety Rules

- Keep `loop_engine.core` as the sole lifecycle and approval authority.
- Persist new artifacts under the active run artifact root; validate paths and
  hashes; preserve atomic writes and migration compatibility.
- Make memory retrieval deterministic, local, bounded, and explicitly
  non-authoritative.
- High-impact unresolved unknowns must be plan/validation obligations or use
  an existing `BLOCKED` approval path.
- Required-agent timeout/quarantine must fail closed when no valid alternative
  remains; no automatic agent spawning or implicit approval.
- Preserve unrelated dirty-worktree changes. Commit only files belonging to
  this approved scope, after review and verification.

## Files Expected to Change

- `loop_engine/core.py`
- `loop_engine/cli.py`
- `plugin/inno-loop-engineering/tests/test_loop_engine.py`
- `plugin/inno-loop-engineering/tests/test_loopctl.py` as needed
- `plugin/inno-loop-engineering/references/artifact-contracts.md`
- `plugin/inno-loop-engineering/references/state-machine.md`
- `plugin/inno-loop-engineering/assets/templates/state.json`
- `README.md` and relevant lifecycle skill documents only after runtime support
  exists

## Implementation Tasks

1. Define additive state/artifact schemas for ledger revisions, claims,
   trajectory summaries/retrieval records, and agent-health records. Add
   normalizers so historic runs remain readable.
2. Implement path/hash/lineage validators and CLI commands for recording and
   inspecting these artifacts. Enforce claim status, source evidence,
   task/criterion links, high-impact unknown routing, and immutable revision
   history.
3. Extend plan/run/review/replan validators with task preconditions, success
   effects, failure effects, evidence-based claim transition rules, and terminal
   trajectory summaries. Keep retrieval output advisory only.
4. Extend registry/heartbeat with bounded retry, timeout, health outcome, and
   current-run quarantine records while retaining leader ownership and existing
   independence constraints.
5. Update tests, contracts, templates, README, and skills to match implemented
   behavior. Add tests for source/path/hash violations, stale claims, high-risk
   unknowns, retrieval non-authority, effect transitions, timeout/quarantine,
   and required-agent block behavior.
6. Run full unit tests, compilation, CLI help/smoke checks, clean-root lifecycle
   fixtures, diff review, then selectively stage and commit only approved files.

## Validation

- `python3 -m unittest discover -s plugin/inno-loop-engineering/tests -v`
- `python3 -m compileall loop_engine plugin/inno-loop-engineering`
- `loop-engine --help` plus each new command help
- clean temporary-root initial, replan, blocked, and complete lifecycle fixtures
- `git diff --check` and final selective staged-diff review

## Rollback Plan

- Keep state schema additions optional/defaulted and preserve historical
  artifacts as audit-only.
- Revert only files changed for this scope; no destructive cleanup of unrelated
  working-tree changes.

## Progress Log

- 2026-07-26: User approved Epistemic Ledger/trajectory memory and
  precondition/effect plus agent-health scope; explicitly excluded drift audit.
- 2026-07-26: Discovered the existing sync script is copied from an unrelated
  repository and the requested vault-update skill source is unavailable.
- 2026-07-26: User excluded `scripts/sync_to_obsidian.py` from the current
  implementation scope.
- 2026-07-26: Added additive ledger, deterministic local trajectory retrieval,
  plan precondition/effect validation, bounded agent-health records, CLI
  surface, contracts, template fields, and focused unit tests.
- 2026-07-26: Verified with full unit suite (19 tests), compilation, CLI help,
  and `git diff --check`.

## Decision Log

- The Loop Engine core remains the sole decision/control authority; add-ons
  create validated artifacts only.
- Local exact/tag retrieval is the initial memory mechanism; it is not evidence
  and cannot affect approval or quality-gate pass status.
- Vault synchronization requires an explicit external root and managed-path
  containment.
