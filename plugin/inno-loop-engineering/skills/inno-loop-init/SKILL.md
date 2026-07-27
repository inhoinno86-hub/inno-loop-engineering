---
name: inno-loop-init
description: Initialize a validated inno-loop project lifecycle from intent.
---

# Inno Loop Init

Run `scripts/loopctl.py --project-root <path> init --intent-file <path>`. Before
the stage executor can invoke `complete-init`, this loop must record `USED`
evidence for Ouroboros `interview`, Superpowers `brainstorming`, and
`writing-plans` using `record-integration --loop project-init`; otherwise the
transition is rejected. Record the accepted input packet, quality gate,
charter/design/roadmap, and a `record-stage-submission` manifest containing
those references. If any required tool is unavailable or fails, record it and
report `BLOCKED` without normal-Codex fallback.

Use only validated input. The command creates the active run state in
`project-init`. The worker must not call `plan` or `complete-init`; the
supervisor validates the submission and performs the transition. If input
validation fails, report `BLOCKED`; do not attempt to bypass it.
