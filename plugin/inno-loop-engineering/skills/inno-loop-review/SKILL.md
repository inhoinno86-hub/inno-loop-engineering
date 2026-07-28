---
name: inno-loop-review
description: Complete or replan an inno-loop review from evidence.
---

# Inno Loop Review

The continuation supervisor enters review with `review --run-report <relative
run-report artifact>` after validating the run-stage submission.
Record a review artifact bound to the active plan, validation matrix, prompt
package, run report, and independent reviewer IDs. It must contain one cited
criterion verdict per rubric ID.

Record a stage submission that references the review artifact. For an unmet
protected criterion it must also reference a recorded remediation packet; for
only nonmandatory, noncritical findings it must reference a backlog item. The
supervisor uses the core result to select `review-complete`, `replan`, or
`defer`; a worker must not select the transition itself.

Review also evaluates protected init intent-baseline requirements separately
from plan criteria. An evidenced `execution_nonconformance` or allowed
diagnostic `indeterminate` finding uses an execution-remediation packet and is
selected by the supervisor as `retry-run`; plan defects and protected intent
failures use plan remediation and `replan`.

Do not turn critical, security, privacy, budget, or DoD failures into deferred backlog.
