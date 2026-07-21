---
name: inno-loop-init
description: Initialize a validated inno-loop project lifecycle from intent.
---

# Inno Loop Init

Run `scripts/loopctl.py --project-root <path> init --intent <text>` or `init --intent-file <path>`.

Use only validated input. The command creates `.inno-loop/state.json` in `project-init`. If input validation fails, report `BLOCKED`; do not attempt to bypass it.
