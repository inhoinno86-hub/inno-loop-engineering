# Approval Policy

Approval is required only for `external_irreversible`, `security_privacy_secrets`, `budget_limit_breach`, `intent_or_core_architecture_change`, and `repeated_evaluation_failure`.

`uncertain_risk` is a fail-closed classification result, not an approval category. It creates `BLOCKED` until a human routes the issue.

An approval request records `action`, `impact`, `alternatives`, `requested_decision`, and evidence references. Timeout never means approval.

Every terminal `BLOCKED` event creates an immutable pending alert. A persistent
runner may deliver it only through a host-owned alert adapter; delivery is
idempotently acknowledged with a receipt. HIL alerts require immediate delivery;
non-HIL terminal failures are still delivered as an execution-stopped alert.

File budgets compare plan-owned changes against a `project-run` baseline. Existing
dirty paths and lifecycle evidence paths are not a budget breach. A resume record
must bind to the exact block and include remediation status, remediation evidence,
and next-attempt policy. Replan-bound overrides require a project-owner policy
that explicitly supplies a replacement bound or `unlimited`.
