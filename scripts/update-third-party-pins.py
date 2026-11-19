#!/usr/bin/env python3
"""Resolve the latest third-party package commits and update import pins."""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess

IMPORT_SCRIPT = pathlib.Path(__file__).with_name("import-third-party-packages.sh")
REPO_LINE = re.compile(r'^([A-Z0-9_]+)_REPO="([^"]+)"$', re.MULTILINE)
REFS = {
    "OPENCLASH": "refs/heads/dev",
}


def latest_commit(repo: str, ref: str) -> str:
    result = subprocess.run(
        ["git", "ls-remote", repo, ref],
        check=True,
        text=True,
        capture_output=True,
    )
    for line in result.stdout.splitlines():
        sha, found_ref = line.split(maxsplit=1)
        if found_ref == ref:
            return sha
    raise RuntimeError(f"No commit returned for {repo} {ref}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    text = IMPORT_SCRIPT.read_text(encoding="utf-8")
    repos = REPO_LINE.findall(text)
    if not repos:
        raise SystemExit("No third-party repositories found in import script")

    updates: list[tuple[str, str, str]] = []
    for prefix, repo in repos:
        exact = re.search(
            rf'^{re.escape(prefix)}_SHA="([0-9a-f]{{40}})"$',
            text,
            re.MULTILINE,
        )
        if not exact:
            raise SystemExit(f"Missing SHA variable for {prefix}")
        old = exact.group(1)
        new = latest_commit(repo, REFS.get(prefix, "HEAD"))
        updates.append((prefix, old, new))
        print(f"{prefix}: {old} -> {new}")

    changed = [item for item in updates if item[1] != item[2]]
    if not changed:
        print("All third-party package pins are already current.")
        return 0
    if args.check:
        print(f"Check mode: {len(changed)} pin(s) would be updated.")
        return 0

    for prefix, _, new in changed:
        text, count = re.subn(
            rf'^{re.escape(prefix)}_SHA="[0-9a-f]{{40}}"$',
            f'{prefix}_SHA="{new}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise SystemExit(f"Failed to update {prefix}_SHA")
    IMPORT_SCRIPT.write_text(text, encoding="utf-8")
    print(f"Updated {len(changed)} third-party package pin(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())