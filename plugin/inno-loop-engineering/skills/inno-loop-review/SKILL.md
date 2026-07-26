---
name: inno-loop-review
description: Complete or replan an inno-loop review from evidence.
---

# Inno Loop Review

First enter review with `review --run-report <relative run-report artifact>`.
Record a review artifact bound to the active plan, validation matrix, prompt
package, run report, and independent reviewer IDs. It must contain one cited
criterion verdict per rubric ID.

Use `review-complete --artifact <reference>` only after the core recomputes
that every mandatory criterion and required validation is `PASS`. For an unmet
current criterion use `replan --evidence <remediation-reference>`; it routes
only to `project-plan`. Use `defer --artifact <backlog reference>` only for a
validated nonmandatory, noncritical finding.

Do not turn critical, security, privacy, budget, or DoD failures into deferred backlog.
