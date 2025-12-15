# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present
PKG_NAME="jollycv"
PKG_VERSION="5b01c1e43f9040bfae25cc9f9dfb14d73951ec3c"
PKG_SHA256=""
PKG_LICENSE="BSD-3-Clause"
PKG_SITE="https://github.com/libretro/jollycv"
PKG_URL="https://github.com/libretro/jollycv/archive/${PKG_VERSION}.tar.gz"
PKG_ARCH="any"
PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/libretro"
PKG_SHORTDESC="JollyCV libretro core (ColecoVision/CreatiVision/My Vision)"
PKG_LONGDESC="Libretro core port of JollyCV (ColecoVision/CreatiVision/My Vision)."
PKG_TOOLCHAIN="make"
PKG_MAKE_OPTS_TARGET="-C libretro platform=unix"

makeinstall_target() {
  mkdir -p "${INSTALL}/usr/lib/libretro"
  cp -v libretro/*.so "${INSTALL}/usr/lib/libretro/" 2>/dev/null || \
  cp -v libretro/jollycv_libretro.so "${INSTALL}/usr/lib/libretro/" 2>/dev/null || \
  {
    echo "ERROR: No .so file found"
    echo "=== Libretro directory contents ==="
    ls -la libretro/
    echo "=== Searching for .so files ==="
    find . -name "*.so" -type f
    return 1
  }
}