# Loop Engine Shared Core Implementation Plan

## Planning Metadata

- Date: 2026-07-24
- Feature name: loop-engine-shared-core
- Planning artifact: PLAN-2026-07-24-loop-engine-shared-core.md
- Planning mode: Superpowers
- Superpowers planning: enabled
- Superpowers execution: disabled
- Superpowers brainstorming: used
- Ouroboros: requested and used
- Notes: Explicit `$inno-loop` invocation authorizes init/plan integrations and lifecycle execution only.

## Goal

Ship repository-owned Python package and `loop-engine` CLI using canonical
`.loop-engine` state, with safe legacy compatibility and complete local tests.

## Design

1. Move pure state, migration, artifact, integration, registry, and heartbeat
   policy into an installable package. Keep CLI presentation thin.
2. Enforce canonical path discovery: canonical state wins only when it is the
   sole state; migrate sole legacy state atomically with backup/provenance; fail
   closed on dual paths.
3. Gate lifecycle transitions on ordered, fresh evidence; persist Decision-A
   artifacts/results and replan remediation bindings.
4. Exercise public command paths from clean temporary roots and update docs only
   after matching runtime behavior exists.

## Ordered Work

1. Add package metadata and `loop_engine` modules; expose `loop-engine`.
2. Implement canonical/legacy state discovery, atomic migration, validation,
   lifecycle authorization, strict integration evidence, Decision-A, registry,
   and heartbeat APIs.
3. Convert plugin `loopctl.py` to a compatibility wrapper using the package;
   update skills/contracts/readme to canonical behavior.
4. Add tests for every acceptance case, then run unit suite, package install,
   CLI smoke tests, static compilation, and stale-reference scan.

## Validation

- `python3 -m unittest discover -s tests -v`
- editable install into a temporary virtual environment, then `loop-engine --help`
- lifecycle, migration, registry, and heartbeat CLI smoke checks in a temporary root
- `python3 -m compileall` and stale `.inno-loop`/external-package claim review

## Risk Policy

No commit, push, deployment, publication, external contact, secret exposure, or
unapproved destructive action. Existing dirty worktree edits are preserved.

## Progress Log

- 2026-07-24: Interview completed with ambiguity score 0.028; design selected.

## Decision Log

- Canonical state/artifact root is `.loop-engine`; legacy support is migration-only.
