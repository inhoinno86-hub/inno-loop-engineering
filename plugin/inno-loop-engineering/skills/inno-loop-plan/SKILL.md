---
name: inno-loop-plan
description: Move a validated inno-loop project from init to planning with evidence.
---

# Inno Loop Plan

Once in `project-plan`, run Ouroboros `interview`, Superpowers `brainstorming`,
and `writing-plans`; record all three as `USED` through `record-integration
--loop project-plan`. Record the accepted input packet, quality gate,
execution plan, validation matrix, and a `record-stage-submission` manifest
containing those references. The worker must not call `run` or `complete-plan`:
the supervisor validates the submission and performs the transition. Unavailable
or failed tools are `BLOCKED` and cannot fall back to normal Codex planning.

This transition is valid only from `project-plan`. The submission binds the
current plan hash and validation matrix before `project-run` begins.
