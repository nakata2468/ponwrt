#!/usr/bin/env bash
# Import the third-party packages selected by configs/release.config.
# Commits are pinned so a cloud build does not silently change packages.
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FOOTSTRAP_REPO="https://github.com/VizzleTF/luci-theme-footstrap.git"
FOOTSTRAP_SHA="5207d769d599094125bedd5adf5fc391d9487960"
OPENCLASH_REPO="https://github.com/vernesong/OpenClash.git"
OPENCLASH_SHA="9e16fae39fac577a8f4c72be35a3fd3c3faeec4d"
LUCKY_REPO="https://github.com/sirpdboy/luci-app-lucky.git"
LUCKY_SHA="31f068051de9798c0fb8f3e1d8e32310b4063e5d"
VIKING_REPO="https://github.com/VIKINGYFY/packages.git"
VIKING_SHA="38588f3bd89489a4ef9b6f8b2cb6bddb3b3865dd"
AUTOREBOOT_REPO="https://github.com/immortalwrt/luci.git"
AUTOREBOOT_SHA="ad75cde88e694b511100576bfbe0a280e5efe6ef"
NPU_REPO="https://github.com/rchen14b/luci-app-airoha-npu.git"
NPU_SHA="14521b8414da1e98517a295d8ec267087c7dde8e"

prepare_repo() {
  local dir="$1"
  local repo="$2"
  local sha="$3"
  rm -rf -- "$dir"
  git init -q "$dir"
  git -C "$dir" remote add origin "$repo"
  git -C "$dir" fetch --depth=1 --filter=blob:none origin "$sha"
  git -C "$dir" checkout --detach "$sha"
}

prepare_sparse_repo() {
  local dir="$1"
  local repo="$2"
  local sha="$3"
  shift 3
  rm -rf -- "$dir"
  git init -q "$dir"
  git -C "$dir" remote add origin "$repo"
  git -C "$dir" sparse-checkout init --cone
  git -C "$dir" sparse-checkout set "$@"
  git -C "$dir" fetch --depth=1 --filter=blob:none origin "$sha"
  git -C "$dir" checkout --detach "$sha"
}

remove_matches() {
  local pattern="$1"
  local base
  for base in "$ROOT/package" "$ROOT/feeds/luci" "$ROOT/feeds/packages"; do
    [ -e "$base" ] || continue
    find "$base" -maxdepth 7 \( -type d -o -type l \) -iname "*${pattern}*" \
      -prune -exec rm -rf -- {} + 2>/dev/null || true
  done
}

echo "Importing pinned third-party packages..."

prepare_repo "$TMP/footstrap" "$FOOTSTRAP_REPO" "$FOOTSTRAP_SHA"
if [ ! -f "$TMP/footstrap/luci-theme-footstrap/Makefile" ]; then
  echo "ERROR: luci-theme-footstrap/Makefile was not found" >&2
  exit 1
fi
remove_matches "footstrap"
cp -a "$TMP/footstrap/luci-theme-footstrap" "$ROOT/package/luci-theme-footstrap"

prepare_repo "$TMP/openclash" "$OPENCLASH_REPO" "$OPENCLASH_SHA"
OPENCLASH_SOURCE="$(find "$TMP/openclash" -maxdepth 3 -type d -name 'luci-app-openclash' | head -n1)"
if [ -z "$OPENCLASH_SOURCE" ]; then
  echo "ERROR: luci-app-openclash directory was not found" >&2
  exit 1
fi
remove_matches "openclash"
cp -a "$OPENCLASH_SOURCE" "$ROOT/package/luci-app-openclash"

prepare_repo "$TMP/lucky" "$LUCKY_REPO" "$LUCKY_SHA"
for name in lucky luci-app-lucky; do
  if [ ! -f "$TMP/lucky/$name/Makefile" ]; then
    echo "ERROR: Lucky package $name/Makefile was not found" >&2
    exit 1
  fi
done
remove_matches "luci-app-lucky"
remove_matches "lucky-packages"
mkdir -p "$ROOT/package/lucky-packages"
cp -a "$TMP/lucky/lucky" "$ROOT/package/lucky-packages/lucky"
cp -a "$TMP/lucky/luci-app-lucky" "$ROOT/package/lucky-packages/luci-app-lucky"

prepare_sparse_repo "$TMP/viking" "$VIKING_REPO" "$VIKING_SHA" \
  gecoosac luci-app-gecoosac luci-app-wolultra
for name in gecoosac luci-app-gecoosac luci-app-wolultra; do
  if [ ! -f "$TMP/viking/$name/Makefile" ]; then
    echo "ERROR: VIKINGYFY package $name/Makefile was not found" >&2
    exit 1
  fi
done
remove_matches "gecoosac"
remove_matches "luci-app-wolplus"
remove_matches "luci-app-wolultra"
mkdir -p "$ROOT/package/viking-packages"
for name in gecoosac luci-app-gecoosac luci-app-wolultra; do
  cp -a "$TMP/viking/$name" "$ROOT/package/viking-packages/$name"
done

prepare_sparse_repo "$TMP/autoreboot" "$AUTOREBOOT_REPO" "$AUTOREBOOT_SHA" \
  applications/luci-app-autoreboot
if [ ! -f "$TMP/autoreboot/applications/luci-app-autoreboot/Makefile" ]; then
  echo "ERROR: luci-app-autoreboot/Makefile was not found" >&2
  exit 1
fi
remove_matches "luci-app-autoreboot"
cp -a "$TMP/autoreboot/applications/luci-app-autoreboot" "$ROOT/package/luci-app-autoreboot"
sed -i 's|include ../../luci.mk|include $(TOPDIR)/feeds/luci/luci.mk|' \
  "$ROOT/package/luci-app-autoreboot/Makefile"

prepare_repo "$TMP/npu" "$NPU_REPO" "$NPU_SHA"
if [ ! -f "$TMP/npu/Makefile" ]; then
  echo "ERROR: luci-app-airoha-npu/Makefile was not found" >&2
  exit 1
fi
remove_matches "luci-app-airoha-npu"
cp -a "$TMP/npu" "$ROOT/package/luci-app-airoha-npu"
rm -rf -- "$ROOT/package/luci-app-airoha-npu/luci-app-airoha-npu"

# The floating ImmortalWrt feeds can contain Kconfig cycles in packages that are
# not part of this firmware. Remove only their installed feed symlinks.
remove_feed_link() {
  local relative="$1"
  local path="$ROOT/package/feeds/$relative"
  if [ -L "$path" ]; then
    rm -f -- "$path"
    echo "Excluded unused feed package: $relative"
  elif [ -e "$path" ]; then
    echo "ERROR: refusing to remove non-feed path $path" >&2
    exit 1
  fi
}

remove_feed_link "packages/mpd"
remove_feed_link "packages/squeezelite"
remove_feed_link "luci/luci-app-homeproxy"
remove_feed_link "luci/luci-app-ipsec-vpnd"
remove_feed_link "luci/luci-app-passwall"

# libevdev is used by libudev-zero/usbutils. Airoha has no OpenWrt
# input-support target feature, but libevdev itself is a userspace library.
LIBEVDEV_MAKEFILE="$ROOT/feeds/packages/libs/libevdev/Makefile"
if [ -f "$LIBEVDEV_MAKEFILE" ] && grep -Fq '  DEPENDS:=input-support' "$LIBEVDEV_MAKEFILE"; then
  sed -i 's/^  DEPENDS:=input-support$/  DEPENDS:=/' "$LIBEVDEV_MAKEFILE"
fi

# Force OpenWrt to rebuild package metadata after importing local package trees.
rm -rf -- "$ROOT/tmp"

echo "Third-party package import completed."