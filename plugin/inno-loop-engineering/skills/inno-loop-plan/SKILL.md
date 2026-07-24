---
name: inno-loop-plan
description: Move a validated inno-loop project from init to planning with evidence.
---

# Inno Loop Plan

Run `scripts/loopctl.py --project-root <path> plan --evidence <reference>` only after required `project-init` integration evidence exists. Once in `project-plan`, run Ouroboros `interview`, Superpowers `brainstorming`, and `writing-plans`; record all three as `USED` through `record-integration --loop project-plan` before calling `run`. Unavailable or failed tools are `BLOCKED` and cannot fall back to normal Codex planning.

This transition is valid only from `project-init`. Record the plan hash and validation matrix outside the command before starting `project-run`.
