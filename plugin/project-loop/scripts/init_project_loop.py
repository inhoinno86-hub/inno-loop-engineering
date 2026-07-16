#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = PLUGIN_ROOT / "assets" / "templates"
TARGETS = {
    "charter.md": Path("docs/project/CHARTER.md"),
    "design.md": Path("docs/project/DESIGN.md"),
    "roadmap.md": Path("docs/project/ROADMAP.md"),
    "status.md": Path("docs/project/STATUS.md"),
    "state.json": Path(".project-loop/state.json"),
}


def timestamp():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def render(source, project_id, now):
    text = source.read_text(encoding="utf-8")
    text = text.replace("__PROJECT_ID__", project_id).replace("__TIMESTAMP__", now)
    return text.replace("__DATE__", now[:10])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.project_id):
        print("invalid project id: use lowercase kebab-case", file=sys.stderr)
        return 2
    root = Path(args.project_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    created, preserved, replaced = [], [], []
    now = timestamp()
    for template, relative in TARGETS.items():
        target = root / relative
        existing = target.exists() and target.read_text(encoding="utf-8").strip()
        if existing and not args.overwrite:
            preserved.append(str(relative))
            continue
        atomic_write(target, render(TEMPLATES / template, args.project_id, now))
        (replaced if existing else created).append(str(relative))
    print(json.dumps({"created": created, "preserved": preserved, "replaced": replaced}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
