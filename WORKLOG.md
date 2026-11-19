# PonWrt Work Log

## 2026-11-19 - Operating record and compile automation

### Repository state

- GitHub fork: `nakata2468/ponwrt`
- Upstream: `pbs05/ponwrt`
- Branch: `master`
- Remotes:
  - `origin` = `https://github.com/nakata2468/ponwrt.git`
  - `upstream` = `https://github.com/pbs05/ponwrt.git`
- Last verified upstream source commit: `f6977f2` (`ci: show the tag in release workflow runs`, 2026-11-16).
- Successful cloud build: Actions run `44013844185`, commit `2fe6eab`.
- Release design commit: `bc87224` (`ci: publish all device assets in one release`).

### Current firmware scope

- Build target: Airoha AN7581 only.
- AN7583 is intentionally removed from the build matrix. `configs/an7583.config` remains in the repository for future use.
- Runtime package overlay mirrors the requested package set from `Kahen/PonWrt-CI-UBI`:
  - LuCI full collection and Simplified Chinese.
  - OpenClash, Lucky, GecoosAC, WOL Ultra, Samba4, UPnP, auto-reboot, Airoha NPU.
  - USB/filesystem/kernel diagnostics, PON stack and bridge offload packages.
- `fitblk` is validated as module `m`, matching current upstream Kconfig behavior.
- Unused feed packages that caused Kconfig cycles are excluded:
  - Qt5 Base
  - fwknop / luci-app-fwknopd
  - mpd, squeezelite
  - known unused LuCI proxy/theme cycles

### Release format

The current format is one GitHub Release per build with all device firmware in the same Assets list.

Current release:

- Tag: `2026-11-17`
- Title: `PonWrt 2026-11-17`
- Status: prerelease
- Firmware assets: 13 model-specific `ponwrt-an7581-<profile>.tar.zst`
- Extra assets:
  - `Config-PonWrt-2026-11-17-an7581.txt`
  - `sha256sums`
  - `release-index.json`
- Total assets: 16
- URL: https://github.com/nakata2468/ponwrt/releases/tag/2026-11-17

Each firmware archive contains only its profile's sysupgrade and initramfs images plus filtered `profiles.json`, config/buildinfo, feeds/buildinfo and version/buildinfo.

The previous monolithic 1.28 GB archive and the temporary one-release-per-device releases were removed after the consolidated release was verified.

### Important scripts

- `scripts/sync-upstream.ps1`
  - Fetches `upstream/master`.
  - Reports `NO_UPSTREAM_CHANGES` with exit code `2` if there is nothing to merge.
  - Performs a normal merge when upstream has new commits.
- `scripts/update-third-party-pins.py`
  - Queries each third-party repository's selected latest branch/HEAD via `git ls-remote`.
  - Rewrites the pinned SHA values in `scripts/import-third-party-packages.sh`.
  - Supports `--check` for read-only inspection.
- `scripts/import-third-party-packages.sh`
  - Imports pinned third-party packages and applies known feed-compatibility exclusions.
- `scripts/split-release.py`
  - Reads the real `profiles.json` and creates one archive per device profile.
- `scripts/publish-release.py`
  - Creates one GitHub Release containing all device archives, config, checksums and index.
- `scripts/validate-packages.py`
  - Fails the build if requested package symbols do not resolve exactly as configured.

### Third-party update policy

Pinned third-party sources:

- `VizzleTF/luci-theme-footstrap`
- `vernesong/OpenClash` (`dev` branch)
- `sirpdboy/luci-app-lucky`
- `VIKINGYFY/packages`
- `immortalwrt/luci` for auto-reboot
- `rchen14b/luci-app-airoha-npu`

Official feeds in `feeds.conf.default` are floating and are refreshed on every cloud build by `./scripts/feeds update -a`. Third-party packages are pinned for reproducibility and are updated only by Command 2.

### Agreed future commands

`编译固件`:

1. Sync upstream using `scripts/sync-upstream.ps1`.
2. If no upstream commits exist, report that and stop without compiling.
3. If upstream commits exist, merge preserving local configuration, push, and run a complete cloud build.

`编译固件，并更新所有的软件包`:

1. Merge upstream.
2. Run `scripts/update-third-party-pins.py`.
3. Commit and push updated pinned SHAs.
4. Allow official feeds to refresh during the cloud build.
5. Run and monitor a complete cloud build with the latest package versions.
6. Diagnose and fix compatibility failures until the build succeeds or a concrete upstream incompatibility is proven.

The full operational instructions are stored in `AGENTS.md`.

### Verification already performed

- Third-party imports were fetched successfully at the pinned revisions.
- `an7581.config + release.config` merged successfully.
- Package validation passed: 127 enabled, 1 module (`fitblk`), 3 disabled.
- Real `profiles.json` split produced 13 device archives.
- All 13 SHA256 values matched.
- Each sampled archive contained only its target profile.
- GitHub Actions run `44013844185` completed successfully.
- The consolidated release was verified with 13 firmware archives and 3 metadata assets.
- On 2026-11-19, `scripts/update-third-party-pins.py --check` found newer commits for `VIKINGYFY/packages` and `immortalwrt/luci` (auto-reboot). These pins were intentionally not changed while recording the workflow; Command 2 will apply and validate them.