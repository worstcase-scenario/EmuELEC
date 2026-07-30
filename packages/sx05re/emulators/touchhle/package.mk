# SPDX-License-Identifier: GPL-2.0-or-later
PKG_NAME="touchhle"
#PKG_VERSION="0f2c163005d7511030be57b70396f4910bbc6d1a"
PKG_VERSION="f666045f18d2937c65ba3bcb90047aa77296ec87"
PKG_SITE="https://github.com/touchHLE/touchHLE"
PKG_URL="${PKG_SITE}.git"
PKG_LICENSE="MPLv2"
PKG_ARCH="aarch64"
PKG_TOOLCHAIN="manual"
PKG_DEPENDS_TARGET="toolchain SDL2 openal-soft"

# Requires a host rustup toolchain (EmuELEC's bundled Rust 1.67.1 is too old):
#   curl https://sh.rustup.rs -sSf | sh
#   rustup target add aarch64-unknown-linux-gnu

RUST_TARGET="aarch64-unknown-linux-gnu"

make_target() {
  unset CMAKE

  # Use host rustup toolchain, not EmuELEC's bundled rust/cargo
  export PATH="$HOME/.cargo/bin:$PATH"
  export RUSTUP_HOME="$HOME/.rustup"
  export CARGO_HOME="$HOME/.cargo"
  unset RUSTC_BOOTSTRAP

  # Pin output location (build system cwd tricks / cargo_home config must not move it)
  export CARGO_TARGET_DIR="${PKG_BUILD}/target"

  export PKG_CONFIG_ALLOW_CROSS=1

  # Link and build C/C++ with the EmuELEC target toolchain (sysroot provides
  # SDL2/openal); env var beats the Ubuntu cross-gcc in ~/.cargo/config.toml.
  # Build scripts / host tools use the host compiler.
  export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER="${CC}"
  export CC_aarch64_unknown_linux_gnu="${CC}"
  export CXX_aarch64_unknown_linux_gnu="${CXX}"
  export AR_aarch64_unknown_linux_gnu="${AR}"
  export HOST_CC="/usr/bin/gcc"
  export HOST_CXX="/usr/bin/g++"

  ${HOME}/.cargo/bin/cargo build --target ${RUST_TARGET} --release --no-default-features
}

# -----------------------------
# Install
# -----------------------------
makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp -f ${PKG_BUILD}/target/${RUST_TARGET}/release/touchHLE \
    ${INSTALL}/usr/bin/touchhle-sa

  # External launcher from package scripts dir
  cp -f ${PKG_DIR}/scripts/start_touchhle.sh ${INSTALL}/usr/bin/

  # Runtime data: synced to /storage/.config/touchhle on first run by the launcher
  mkdir -p ${INSTALL}/usr/config/touchhle
  cp -r ${PKG_BUILD}/touchHLE_dylibs ${INSTALL}/usr/config/touchhle/
  cp -r ${PKG_BUILD}/touchHLE_fonts ${INSTALL}/usr/config/touchhle/
  cp -f ${PKG_BUILD}/touchHLE_default_options.txt ${INSTALL}/usr/config/touchhle/
  cp -f ${PKG_BUILD}/touchHLE_options.txt ${INSTALL}/usr/config/touchhle/  
  chmod +x ${INSTALL}/usr/bin/*
}