# SPDX-License-Identifier: GPL-2.0-or-later
# EmuELEC / LibreELEC package for WASM-4 libretro core

PKG_NAME="wasm4"
PKG_VERSION="68cbe429fcbab3e80537282d2c21566f5ea216ea"
PKG_ARCH="any"
PKG_LICENSE="ISC"
PKG_SITE="https://git.libretro.com/libretro/wasm4"
PKG_URL="${PKG_SITE}.git"
PKG_SHA256=""
PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="libretro"
PKG_SHORTDESC="WASM-4 libretro core"
PKG_LONGDESC="WASM-4 is a fantasy console based on WebAssembly. This package builds the libretro core (lr-wasm4)."
PKG_IS_ADDON="no"
PKG_TOOLCHAIN="cmake"

PKG_GIT_CLONE_SINGLE="yes"

PKG_CMAKE_OPTS_TARGET="-DLIBRETRO=ON \
                       -DWASM3=ON \
                       -DCMAKE_BUILD_TYPE=Release"

pre_configure_target() {
  PKG_CMAKE_SCRIPT="${PKG_BUILD}/runtimes/native/CMakeLists.txt"
}

makeinstall_target() {
  mkdir -p "${INSTALL}/usr/lib/libretro"
  

  local core=""
  

  if [ -f "${PKG_BUILD}/.${TARGET_NAME}/wasm4_libretro.so" ]; then
    core="${PKG_BUILD}/.${TARGET_NAME}/wasm4_libretro.so"
  elif [ -f "${PKG_BUILD}/build/wasm4_libretro.so" ]; then
    core="${PKG_BUILD}/build/wasm4_libretro.so"
  else

    core="$(find "${PKG_BUILD}" -name 'wasm4_libretro.so' | head -n1)"
  fi
  
  if [ -z "${core}" ] || [ ! -f "${core}" ]; then
    echo "ERROR: wasm4_libretro.so not found" >&2
    echo "Searched in:" >&2
    echo "  ${PKG_BUILD}/.${TARGET_NAME}/" >&2
    echo "  ${PKG_BUILD}/build/" >&2
    echo "" >&2
    echo "Available .so files:" >&2
    find "${PKG_BUILD}" -name "*.so" >&2
    return 1
  fi
  
  echo "Installing core from: ${core}"
  cp "${core}" "${INSTALL}/usr/lib/libretro/wasm4_libretro.so"
}