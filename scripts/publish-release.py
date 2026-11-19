#!/usr/bin/env python3
"""Publish one GitHub Release containing one firmware asset per device."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
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


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--prerelease", action="store_true")
    parser.add_argument("--gh", default="gh")
    parser.add_argument("--dry-run", action="store_true")
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

    existing_raw = run(
        gh,
        ["release", "list", "--repo", args.repo, "--limit", "1000", "--json", "tagName"],
        capture=True,
    ).stdout
    existing = {item["tagName"] for item in json.loads(existing_raw)}
    if args.tag in existing:
        raise SystemExit(f"Release tag already exists: {args.tag}")

    archives: list[pathlib.Path] = []
    checksum_lines: list[str] = []
    summary_lines: list[str] = []
    for entry in entries:
        archive = root / entry["directory"] / entry["archive"]
        if not archive.is_file():
            raise SystemExit(f"Missing firmware archive: {archive}")
        archives.append(archive)
        checksum_lines.append(f"{entry['sha256']} *{archive.name}")
        summary_lines.append(
            f"- **{entry['display_name']}** — `{entry['profile']}` — `{entry['sha256']}`"
        )

    combined_checksum = root / "sha256sums"
    combined_checksum.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    index_asset = root / "release-index.json"
    shutil.copy2(index_path, index_asset)

    assets: list[pathlib.Path] = list(archives)
    config_source = root / "config.buildinfo"
    if config_source.is_file():
        config_asset = root / f"Config-PonWrt-{safe_name(args.tag)}-{target_name}.txt"
        shutil.copy2(config_source, config_asset)
        assets.append(config_asset)
    assets.extend([combined_checksum, index_asset])

    notes = (
        f"PonWrt {args.tag} firmware for Airoha {target_name}.\n\n"
        f"Target: `airoha/{target_name}`\n\n"
        f"Source commit: `{args.target}`\n\n"
        "Device firmware assets:\n\n"
        + "\n".join(summary_lines)
        + "\n"
    )

    command = [
        "release", "create", args.tag,
        *(str(path) for path in assets),
        "--repo", args.repo,
        "--target", args.target,
        "--title", f"PonWrt {args.tag}",
        "--notes", notes,
    ]
    if args.prerelease:
        command.append("--prerelease")
    if args.dry_run:
        print(f"Dry run: would publish {args.tag} with {len(archives)} device archives")
        for asset in assets:
            print(f"  {asset.name}")
        return 0
    result = run(gh, command, capture=True)
    print(result.stdout.strip())
    print(f"Published {args.tag} with {len(archives)} device firmware assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())