# PonWrt Fork Operating Rules

This file records the agreed build procedure for this repository. Follow it whenever the user issues either of the two exact compile commands below.

## Project facts

- Fork: `nakata2468/ponwrt`
- Upstream: `pbs05/ponwrt`
- Default branch: `master`
- Current build target: Airoha AN7581 only. Do not add AN7583 unless explicitly requested.
- Main package overlay: `configs/release.config`
- Third-party package importer: `scripts/import-third-party-packages.sh`
- Cloud workflow: `.github/workflows/release.yml`
- GitHub CLI on this Windows host: `C:\Program Files\GitHub CLI\gh.exe`
- One cloud build produces one GitHub Release. The Release Assets list contains one archive per AN7581 device, plus config, checksum, and index files.
- Preserve the repository-owned configuration and release design when merging upstream. Never discard local commits or force-push unless the user explicitly requests it.

## Command 1: `编译固件`

Meaning: perform a normal compile, first merging any new upstream commits. If upstream has no new commits, stop without compiling.

Required procedure:

1. Read `WORKLOG.md` and run `git status --short --branch`.
2. Do not start with uncommitted changes. Preserve or commit existing work first.
3. Run:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-upstream.ps1
   ```
4. If the script exits with code `2` or prints `NO_UPSTREAM_CHANGES`:
   - Tell the user that there are no new upstream commits.
   - Stop immediately.
   - Do not trigger GitHub Actions and do not compile.
5. If upstream has new commits:
   - A normal merge is created by the script.
   - If conflicts occur, resolve them while preserving `configs/release.config`, the AN7581-only matrix, the third-party importer, and the single-Release multi-asset design.
   - Run syntax and diff checks, commit the merge/resolutions, and push to `origin/master`.
6. Do not update pinned third-party package SHAs for this command.
7. Trigger `Release PonWrt` with a new tag and wait for the complete cloud build.
8. Tag selection:
   - Use the current client date as `YYYY-MM-DD`.
   - If that tag already exists, use `YYYY-MM-DD-r2`, then `-r3`, etc.
   - Default `prerelease=true` unless the user explicitly asks for a formal release.
9. Monitor the run to completion. If it fails, diagnose and fix the project failure, then rerun with a new tag. Report the Release URL and result.

## Command 2: `编译固件，并更新所有的软件包`

Meaning: merge upstream, refresh all configured software packages, commit the updated pins, and run a complete compile to prove the latest versions work.

Required procedure:

1. Read `WORKLOG.md` and run `git status --short --branch`.
2. Run the upstream sync script:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-upstream.ps1
   ```
   - Exit code `2` means no upstream source changes. In this command, continue anyway because package updates may exist.
   - Resolve and commit any upstream merge conflict before continuing.
3. Refresh all pinned third-party packages:
   ```powershell
   python scripts/update-third-party-pins.py
   ```
   If `python` is unavailable, use the Python executable available in the Codex runtime.
4. Official feeds (`packages`, `luci`, `routing`, `telephony`, `video`, `pon_drivers`, `pon_userspace`) are intentionally floating. Every build already runs `./scripts/feeds update -a`; do not pin them unless the user asks.
5. Inspect `git diff` after updating pins. Commit and push the updated SHAs:
   ```powershell
   git add scripts/import-third-party-packages.sh
   git commit -m "chore: update third-party packages"
   git push origin master
   ```
   If there are no pin changes and no upstream merge changes, tell the user pins are already current, but still compile because floating official feeds can have changed.
6. Trigger `Release PonWrt` with a new tag using the same tag rules as Command 1 and `prerelease=true` by default.
7. Wait for the complete build. This command is not complete until the workflow succeeds and the consolidated Release exists.
8. If a latest package breaks the build:
   - Inspect the failed step and package dependencies.
   - Fix the import/configuration issue without silently removing requested packages.
   - If a specific upstream package is incompatible, explain the incompatibility and choose a safe compatible revision only when necessary.
   - Commit fixes, push, and run another complete build with a new tag.
9. Report changed pins, build commit, Actions URL, Release URL, and the final asset count.

## Current release design

- Tag example: `2026-11-19`
- Release title: `PonWrt 2026-11-19`
- The Assets list must contain:
  - 13 per-device `ponwrt-an7581-<profile>.tar.zst` archives
  - `Config-PonWrt-<tag>-an7581.txt`
  - `sha256sums`
  - `release-index.json`
- Each device archive contains only that profile's sysupgrade and initramfs recovery images plus build metadata.
- Do not revert to one monolithic AN7581 archive.
- Do not create one Release per device unless the user explicitly changes the requirement again.

## Validation and safety

- Check `git diff --check`, Python syntax, shell syntax, and workflow registration after changes.
- Test release splitting against a real `profiles.json` when changing packaging logic.
- Never commit keys, tokens, firmware images, feeds, build directories, or temporary archives.
- Never delete releases, tags, or assets unless the user explicitly asks.
- Keep `configs/an7583.config` in the repository even though AN7583 is not currently built.
- Use `WORKLOG.md` for dated state and operational history.