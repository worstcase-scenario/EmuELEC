# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present

PKG_NAME="exa-rs"
PKG_VERSION="b1d69b78d2ac2073df1c2ccfe7254e720a4b278e"
PKG_ARCH="any"
PKG_LICENSE="MIT"

PKG_SITE="https://github.com/thieman/exa-rs"
PKG_URL="${PKG_SITE}.git"

PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/libretro"
PKG_SHORTDESC="exa-rs libretro core (TEC Redshift / EXAPUNKS)"
PKG_LONGDESC="Libretro core for the TEC Redshift, the fictional handheld from Zachtronics' EXAPUNKS."
PKG_TOOLCHAIN="manual"

make_target() {
  export PATH="${HOME}/.cargo/bin:${PATH}"
  export CARGO_HOME="${PKG_BUILD}/.cargo"
  export CARGO_TARGET_DIR="${PKG_BUILD}/target"
  export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER="${CC}"
  rustup target add aarch64-unknown-linux-gnu
  cargo build --lib --release --target aarch64-unknown-linux-gnu
}

makeinstall_target() {
  mkdir -p "${INSTALL}/usr/lib/libretro"
  cp "${PKG_BUILD}/target/aarch64-unknown-linux-gnu/release/libexa.so" \
     "${INSTALL}/usr/lib/libretro/exa_libretro.so"
}