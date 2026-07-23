---
name: inno-loop-plan
description: Move a validated inno-loop project from init to planning with evidence.
---

# Inno Loop Plan

If entering from `replan`, read `remediation_packet` from `.loop-engine/state.json` for context before proceeding.

After recording charter/design/roadmap evidence, run:

```bash
scripts/loopctl.py --project-root <path> plan --evidence <reference>
```

This transition is valid only from `project-init`. Record the plan hash and validation matrix outside the command before starting `project-run`.
