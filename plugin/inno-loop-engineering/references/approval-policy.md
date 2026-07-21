# Approval Policy

Approval is required only for `external_irreversible`, `security_privacy_secrets`, `budget_limit_breach`, `intent_or_core_architecture_change`, and `repeated_evaluation_failure`.

`uncertain_risk` is a fail-closed classification result, not an approval category. It creates `BLOCKED` until a human routes the issue.

An approval request records `action`, `impact`, `alternatives`, `requested_decision`, and evidence references. Timeout never means approval.
