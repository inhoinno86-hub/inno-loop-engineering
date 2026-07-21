---
name: inno-loop-run
description: Start the bounded inno-loop execution phase after planning evidence exists.
---

# Inno Loop Run

Run `scripts/loopctl.py --project-root <path> run --evidence <plan-reference>` only after a versioned plan and validation matrix exist.

External effects, secrets, uncertain risk, and policy-limit breaches require a pending approval request and remain `BLOCKED`. Superpowers is optional and requires task-scoped opt-in.
