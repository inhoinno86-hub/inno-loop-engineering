---
name: inno-loop-init
description: Initialize a validated inno-loop project lifecycle from intent.
---

# Inno Loop Init

Run `scripts/loopctl.py --project-root <path> init --intent <text>` or `init --intent-file <path>`. Before `plan`, this loop must record `USED` evidence for Ouroboros `interview`, Superpowers `brainstorming`, and `writing-plans` using `record-integration --loop project-init`; otherwise the transition is rejected. If any required tool is unavailable or fails, record it and report `BLOCKED` without normal-Codex fallback.

Use only validated input. The command creates `.inno-loop/state.json` in `project-init`. If input validation fails, report `BLOCKED`; do not attempt to bypass it.
