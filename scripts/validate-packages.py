#!/usr/bin/env python3
"""Fail the build if the requested PonWrt package set was not resolved."""
from __future__ import annotations

import pathlib
import re
import sys

CONFIG_LINE = re.compile(r"^(CONFIG_[A-Za-z0-9_-]+)=(.*)$")
UNSET_LINE = re.compile(r"^# (CONFIG_[A-Za-z0-9_-]+) is not set$")


def parse_config(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        match = CONFIG_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
            continue
        match = UNSET_LINE.match(line)
        if match:
            values[match.group(1)] = "n"
    return values


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: validate-packages.py ACTUAL_CONFIG REQUESTED_CONFIG")

    actual = parse_config(pathlib.Path(sys.argv[1]))
    requested = parse_config(pathlib.Path(sys.argv[2]))
    errors: list[str] = []

    for symbol, wanted in requested.items():
        got = actual.get(symbol)
        if wanted == "y":
            if got != "y":
                errors.append(f"{symbol}: requested y, resolved {got or 'missing'}")
        elif wanted == "m":
            if got != "m":
                errors.append(f"{symbol}: requested m, resolved {got or 'missing'}")
        elif wanted == "n":
            if got in {"y", "m"}:
                errors.append(f"{symbol}: requested n, resolved {got}")

    if errors:
        print("Requested configuration was not fully resolved:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    enabled = sum(value == "y" for value in requested.values())
    modules = sum(value == "m" for value in requested.values())
    disabled = sum(value == "n" for value in requested.values())
    print(f"Verified {enabled} enabled, {modules} module, and {disabled} disabled requested symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())