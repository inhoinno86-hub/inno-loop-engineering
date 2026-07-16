#!/usr/bin/env python3
import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_project_loop import load_state, validate


def redact(value):
    return re.sub(r"(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*\S+", r"\1=<redacted>", str(value))


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def render(root):
    state = load_state(root)
    errors = validate(root, state)
    evidence = "\n".join(f"- `{redact(item)}`" for item in state.get("evidence_refs", [])) or "- None recorded"
    blockers = f"- {redact(state.get('blocked_reason'))}" if state.get("blocked_reason") else "- None"
    risks = "\n".join(f"- {redact(item)}" for item in errors) or "- No structural inconsistency detected"
    decision = "- Resolve validation inconsistencies" if errors else ("- User review required" if state.get("user_review_required") else "- None")
    next_action = {"DRAFT": "Complete and approve Charter", "BLOCKED": "Resolve blocker and explicitly resume", "COMPLETE": "Approve milestone closeout"}.get(state["state"], "Follow the next legal state transition")
    return f"""# Project Loop Status

- Artifact Status: DERIVED
- Last Updated: {datetime.now().astimezone().date().isoformat()}

## Current State
`{state['state']}`

## Active Milestone
{redact(state.get('active_milestone') or 'None')}

## Evidence
{evidence}

## Blockers
{blockers}

## Risks
{risks}

## Decisions Needed
{decision}

## Next Action
{next_action}

## Decision Log
Derived artifact; decisions belong in authoritative project documents.
"""


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    try:
        output = root / "docs/project/STATUS.md"
        atomic_write(output, render(root))
        print(output)
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
