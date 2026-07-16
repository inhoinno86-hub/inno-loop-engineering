# Document Contracts

| Artifact | Authority |
|---|---|
| `docs/project/CHARTER.md` | problem, users, goals, non-goals, success measures, constraints |
| `docs/project/DESIGN.md` | architecture, alternatives, interfaces, risks, decisions |
| `docs/project/ROADMAP.md` | milestones, dependencies, outcomes, Definition of Done |
| root `PLAN-2026-07-16-example-feature.md` | approved implementation scope for one milestone; actual date and feature vary |
| `to-do-prompts/*` | derived execution prompts; never new requirements |
| `.project-loop/state.json` | machine-readable state and counters |
| `docs/project/STATUS.md` | derived human-readable snapshot |

Every managed Markdown artifact includes `Artifact Status`, `Last Updated`, and `Decision Log`. Approval entries use `APPROVED -`. An active plan contains global Planning Metadata, Progress Log, Decision Log, validation commands, and rollback plan.

`to-do-prompts/main.md` includes `Active plan:` and `Plan SHA-256:`. Active root plan wins every conflict; regenerate derived prompts after plan change.
