#!/usr/bin/env python3
"""Split an OpenWrt target directory into one release archive per device profile."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_title(data: dict) -> str:
    titles = data.get("titles") or []
    if not titles:
        return ""
    title = titles[0]
    parts = [title.get("vendor"), title.get("model"), title.get("variant")]
    return " ".join(str(part).strip() for part in parts if part).strip()


def find_shared_metadata(source: pathlib.Path, target_name: str) -> list[pathlib.Path]:
    candidates = [
        source / "version.buildinfo",
        source / "feeds.buildinfo",
        source / "config.buildinfo",
        source / f"ponwrt-airoha-{target_name}.manifest",
        source / f"openwrt-airoha-{target_name}.manifest",
    ]
    return [path for path in candidates if path.is_file()]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: split-release.py TARGET_DIR OUTPUT_DIR")

    source = pathlib.Path(sys.argv[1]).resolve()
    output = pathlib.Path(sys.argv[2]).resolve()
    profiles_path = source / "profiles.json"
    if not profiles_path.is_file():
        raise SystemExit(f"profiles.json not found: {profiles_path}")

    document = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = document.get("profiles") or {}
    if not profiles:
        raise SystemExit("profiles.json contains no profiles")

    target_name = source.name
    work_root = output / ".split-work"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    output.mkdir(parents=True, exist_ok=True)

    shared_metadata = find_shared_metadata(source, target_name)
    index: list[dict[str, str]] = []

    for profile_name, profile in sorted(profiles.items()):
        images = profile.get("images") or []
        if not images:
            continue

        profile_dir = output / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        staging_root = work_root / profile_name
        staging_target = staging_root / target_name
        staging_target.mkdir(parents=True)

        filtered = dict(document)
        filtered["profiles"] = {profile_name: profile}
        (staging_target / "profiles.json").write_text(
            json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        for image in images:
            image_name = image.get("name")
            if not image_name:
                raise SystemExit(f"Profile {profile_name} has an image without a name")
            image_path = source / image_name
            if not image_path.is_file():
                raise SystemExit(f"Missing image for {profile_name}: {image_path}")
            shutil.copy2(image_path, staging_target / image_name)

        for metadata in shared_metadata:
            shutil.copy2(metadata, staging_target / metadata.name)

        archive_name = f"ponwrt-{target_name}-{profile_name}.tar.zst"
        archive_path = profile_dir / archive_name
        subprocess.run(
            ["tar", "--zstd", "-cf", str(archive_path), "-C", str(staging_root), target_name],
            check=True,
        )
        checksum = sha256_file(archive_path)
        checksum_path = profile_dir / "sha256sums"
        checksum_path.write_text(f"{checksum} *{archive_name}\n", encoding="utf-8")

        display_name = profile_title(profile) or profile_name
        index.append(
            {
                "profile": profile_name,
                "display_name": display_name,
                "tag_suffix": profile_name,
                "directory": profile_name,
                "archive": archive_name,
                "sha256": checksum,
                "image_count": str(len(images)),
            }
        )
        print(f"Created {archive_name}: {display_name} ({len(images)} images)")

    shutil.rmtree(work_root)
    if not index:
        raise SystemExit("No device images were packaged")

    index_path = output / "index.json"
    index_path.write_text(json.dumps({"target": target_name, "releases": index}, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(index)} device profiles; index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())