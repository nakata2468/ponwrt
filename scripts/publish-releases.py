#!/usr/bin/env python3
"""Publish one GitHub Release per device entry in a split-release index."""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def run(gh: str, args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [gh, *args],
        check=True,
        text=True,
        capture_output=capture,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--tag-base", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--prerelease", action="store_true")
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()

    gh = shutil.which(args.gh) or args.gh
    if not gh:
        raise SystemExit("GitHub CLI not found")

    index_path = pathlib.Path(args.index).resolve()
    root = index_path.parent
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = index.get("releases") or []
    target_name = index.get("target") or "target"
    if not entries:
        raise SystemExit("Release index is empty")

    planned: list[tuple[dict, str, pathlib.Path, pathlib.Path]] = []
    for entry in entries:
        tag = f"{args.tag_base}-{entry['tag_suffix']}"
        release_dir = root / entry["directory"]
        archive = release_dir / entry["archive"]
        checksum = release_dir / "sha256sums"
        if not archive.is_file() or not checksum.is_file():
            raise SystemExit(f"Release assets missing for {entry['profile']}")
        planned.append((entry, tag, archive, checksum))

    existing_raw = run(
        gh,
        ["release", "list", "--repo", args.repo, "--limit", "1000", "--json", "tagName"],
        capture=True,
    ).stdout
    existing = {item["tagName"] for item in json.loads(existing_raw)}
    conflicts = [tag for _, tag, _, _ in planned if tag in existing]
    if conflicts:
        raise SystemExit("Refusing partial publish; releases already exist: " + ", ".join(conflicts))

    for entry, tag, archive, checksum in planned:
        title = f"PonWrt {args.tag_base} - {entry['display_name']}"
        notes = (
            f"PonWrt {args.tag_base} firmware for **{entry['display_name']}**.\n\n"
            f"- Target: `{target_name}`\n"
            f"- Profile: `{entry['profile']}`\n"
            f"- Source commit: `{args.target}`\n"
            f"- Images: {entry['image_count']}\n"
            f"- SHA256: `{entry['sha256']}`\n"
        )
        command = [
            "release", "create", tag,
            str(archive), str(checksum),
            "--repo", args.repo,
            "--target", args.target,
            "--title", title,
            "--notes", notes,
            "--latest=false",
        ]
        if args.prerelease:
            command.append("--prerelease")
        result = run(gh, command, capture=True)
        print(result.stdout.strip())
        print(f"Published {tag}: {entry['display_name']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())