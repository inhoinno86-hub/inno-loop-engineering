# Step 03 Prompt

## Goal

Add deterministic regression coverage and verify repaired lifecycle behavior.

## Baseline

Use steps 1-2 and current `main.md`.

## Scope

Update `plugin/inno-loop-engineering/tests/test_loop_engine.py`; run relevant unittest commands and inspect final diff.

## Instructions

1. Test no implicit adapter and truthful preflight failure.
2. Test v2 capability success/failure with no integration side effect.
3. Test integration payload includes source/authorization/init or remediation lineage and packet when available.
4. Keep existing transient retry and init iteration coverage, adapting fixtures to v2.
5. Run full plugin test discovery without bytecode/cache writes where possible, then inspect diff/status.

## Constraints

No live Codex/Ouroboros invocation in tests. Do not modify unrelated dirty files.

## Expected Deliverable

Focused regression tests and recorded verification output.

## Completion Criteria

- Tests fail under old implicit-bridge behavior and pass with repaired boundary.
- Test suite passes.
- Diff contains only package, bridge repair, docs, and tests.

## Next Step Handoff

None; report verification and remaining live-runtime test gap.
