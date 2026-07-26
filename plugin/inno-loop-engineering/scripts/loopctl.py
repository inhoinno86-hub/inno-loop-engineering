#!/usr/bin/env python3
"""Compatibility entry point for installed ``loop-engine`` CLI.

Plugin caches contain skills and wrappers, not the repository's Python package.
Delegate to the installed shared-core executable instead of importing from the
cache-local ``loop_engine.py`` compatibility module.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        os.execvp("loop-engine", ["loop-engine", *sys.argv[1:]])
    except FileNotFoundError:
        print("loop-engine executable is required; install the shared core first", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
