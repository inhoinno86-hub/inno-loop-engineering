# State Machine

Current loops are `project-init`, `project-plan`, `project-run`, and `project-review`.

| From | Event | To | Required evidence |
| --- | --- | --- | --- |
| project-init | complete-init | project-plan | accepted init quality gate, hash-bound input packet, charter/design/roadmap, ordered integrations |
| project-plan | complete-plan | project-run | current-iteration quality gate, hash-bound plan packet, versioned plan and validation matrix, ordered integrations |
| project-run | complete-run | project-review | execution evidence |
| project-review | complete | COMPLETE | all criterion evidence |
| project-review | replan | project-plan | remediation packet; immediately continue the lifecycle |
| project-review | defer | DEFERRED_BACKLOG | nonblocking backlog fields |
| any loop | block | BLOCKED | block reason and evidence |

Only an explicit resume event can leave `BLOCKED`. Human-decision blocks require recorded approval evidence.
