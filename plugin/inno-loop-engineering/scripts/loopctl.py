#!/usr/bin/env python3
"""Compatibility entry point for repository-owned ``loop-engine`` CLI."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from loop_engine.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
