# Main Prompt Plan

## Request Summary

Harden the Loop Engine run/review evidence contracts from the active plan revision.

## Overall Goal

Make current-plan prompt, execution, receipt, and review evidence fail closed.

## Constraints and Assumptions

Baseline is the current `main` worktree. Use normal Codex; Superpowers execution is disabled. Do not commit, push, deploy, or contact external services.

## Step Map

1. Harden plan/package/receipt/run validation.
2. Harden review, remediation, defer, and HIL resume validation.
3. Align CLI, templates, skills, and reference contracts.
4. Add focused lifecycle tests and run regression checks.

Each step depends on its predecessor; every change must be backed by focused tests before the final suite.
