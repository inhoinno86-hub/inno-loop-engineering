---
name: inno-loop-review
description: Complete or replan an inno-loop review from evidence.
---

# Inno Loop Review

First enter review with `review --evidence <run-reference>`.

**Outcomes:**

- `review-complete --evidence <reference>` — only when every required criterion and validation is evidenced.
- `replan --evidence <remediation-reference>` — for any unmet current criterion; routes only to `project-plan`.
- `defer` — for out-of-scope items only. Record impact, rationale, owner, and `revisit_trigger` in the deferred backlog. Do not defer critical, security, privacy, budget, or DoD failures.

**Approval reminder:** Do not block on `uncertain_risk` without first calling `approval_request` with `category: external_irreversible` or `category: security_privacy_secrets`.
