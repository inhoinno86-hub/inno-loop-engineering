---
name: inno-loop-init
description: Initialize a validated inno-loop project lifecycle from intent.
---

# Inno Loop Init

## 1. Socratic Dialogue — N=3 Parallel

Dispatch 3 independent Socrates instances against the same `user_intent` (no shared session history).
Each instance extracts: core requirements, constraints, success criteria.

Compute `consistency_score = matching_items / total_items` across the 3 outputs.

- `consistency_score < 50%` → BLOCKED (HLT-1); request clarification from user.
- `consistency_score 50–80%` → invoke Mediator consensus before proceeding.
- `consistency_score > 80%` → proceed autonomously.

## 2. Init Command

After consensus is reached, run:

```bash
scripts/loopctl.py --project-root <path> init --intent <text>
# or
scripts/loopctl.py --project-root <path> init --intent-file <path>
```

State is written to `.loop-engine/state.json` at stage `project-init`.

If input validation fails, report `BLOCKED`; do not bypass.
