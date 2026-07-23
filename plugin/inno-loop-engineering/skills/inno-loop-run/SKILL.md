---
name: inno-loop-run
description: Start the bounded inno-loop execution phase after planning evidence exists.
---

# Inno Loop Run

Run `scripts/loopctl.py --project-root <path> run --evidence <plan-reference>` only after a versioned plan and validation matrix exist.

External effects, secrets, uncertain risk, and policy-limit breaches require a pending approval request and remain `BLOCKED`. Superpowers is optional and requires task-scoped opt-in.

## Sub-agent Lifecycle

After `loopctl.py run` starts, register each sub-agent and maintain heartbeat:

```bash
# On sub-agent dispatch
loop-engine registry add --project {name} --agent-id {id} --parent root --depth 1 --task-scope {scope}
loop-engine heartbeat touch --project {name} --agent-id {id}

# On sub-agent complete
loop-engine registry update --project {name} --agent-id {id} --status completed
```

Repeat `heartbeat touch` at regular intervals while the sub-agent is active.
