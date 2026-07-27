# State Machine

Current loops are `project-init`, `project-plan`, `project-run`, and `project-review`.

| From | Event | To | Required evidence |
| --- | --- | --- | --- |
| project-init | complete-init | project-plan | accepted init quality gate, hash-bound input packet, charter/design/roadmap, ordered integrations |
| project-plan | complete-plan | project-run | current-iteration quality gate, hash-bound plan packet, versioned plan/validation matrix, ordered integrations, and (when recorded) current Epistemic Ledger task/criterion mappings |
| project-run | complete-run | project-review | current plan-bound policy, prompt package, run report, and required validation receipts |
| project-review | complete | COMPLETE | recomputed mandatory rubric and validation passes from current immutable evidence |
| project-review | replan | project-plan | remediation packet; immediately continue the lifecycle |
| project-review | defer | DEFERRED_BACKLOG | nonblocking backlog fields |
| any loop | block | BLOCKED | block reason and evidence |

Continuation workers record a hash-bound `stage-submission` with artifact
references for their current loop. The stage executor validates the submission
against fresh active state and invokes the event in this table; workers do not
invoke lifecycle transition commands directly.

Only an explicit resume event can leave `BLOCKED`. Human-decision blocks require recorded approval evidence.

An active high-impact unknown cannot reach plan completion without a mapped task
and acceptance criterion. A required agent that reaches timeout, failure,
unavailability, or quarantine produces the existing fail-closed `BLOCKED`
outcome unless a separately valid approved alternative is recorded.
