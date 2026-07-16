# State Machine

Primary path: `DRAFT -> CHARTER_APPROVED -> DESIGN_APPROVED -> ROADMAP_APPROVED -> PLAN_APPROVED -> PROMPTS_READY -> EXECUTING -> VERIFYING -> COMPLETE`.

Exception path: `EXECUTING|VERIFYING -> REWORK|REPLAN|BLOCKED`; `REWORK -> EXECUTING`; `REPLAN -> ROADMAP_APPROVED`; `BLOCKED -> resume_state`; `COMPLETE -> ROADMAP_APPROVED` after closeout approval.

Approval states require corresponding Decision Log evidence. Same normalized failure three times produces `BLOCKED`. Five total rework iterations require user review and prevent execution until approval is recorded. `REPLAN` invalidates active plan and prompts. `COMPLETE` requires evidence for every Definition of Done item. Unknown schema versions and illegal transitions fail closed.
