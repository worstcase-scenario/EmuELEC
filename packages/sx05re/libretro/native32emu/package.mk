# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC/EmuELEC)

PKG_NAME="native32emu"
PKG_VERSION="1.0.0"
PKG_LICENSE="BSD-3-Clause"
PKG_SITE="https://github.com/jiangxincode/Native32Emu"
PKG_URL="${PKG_SITE}/archive/refs/tags/v${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="Native32 game emulator (libretro core) for Sunplus DVD-player games"
PKG_TOOLCHAIN="manual"
GET_HANDLER_SUPPORT="archive"
PKG_SECTION="emuelec/libretro"

# Requires Rust >= 1.88 on the build host.
# Install via: rustup target add aarch64-unknown-linux-gnu
make_target() {
  export RUSTC="${HOME}/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc"
  export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER="${CC}"

  CARGO_HOME="${HOME}/.cargo" \
  RUSTUP_HOME="${HOME}/.rustup" \
  CARGO_TARGET_DIR="${CARGO_TARGET_DIR}" \
    "${HOME}/.cargo/bin/cargo" build --release --target aarch64-unknown-linux-gnu
}

makeinstall_target() {
  LIBRETRO_DIR="${INSTALL}/usr/lib/libretro"
  mkdir -p "${LIBRETRO_DIR}"

  cp "${CARGO_TARGET_DIR}/aarch64-unknown-linux-gnu/release/libnative32emu.so" \
     "${LIBRETRO_DIR}/native32emu_libretro.so"
}