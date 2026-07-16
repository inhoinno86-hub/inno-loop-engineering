# Agent Contracts

- Coordinator: main thread. Owns sequencing, integration, verification, transitions, and user reporting.
- Investigator: read-only search, dependency analysis, or failure diagnosis.
- Implementer: one bounded plan task; writes assigned files only.
- Spec Reviewer: read-only comparison against approved plan.
- Quality Reviewer: read-only correctness, maintainability, tests, and risk review.

Create subagents only when user request or active approved skill permits delegation. Never use overlapping parallel writers. Workers do not coordinate directly or change workflow state. Coordinator re-reads affected files and independently verifies claims. Keep nesting depth at one.
