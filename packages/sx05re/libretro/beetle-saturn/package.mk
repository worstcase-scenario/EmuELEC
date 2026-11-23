# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present Team EmuELEC (https://emuelec.org)

PKG_NAME="beetle-saturn"
PKG_VERSION="5231aa238ff2bf61b1ed88775711b71692c8e37c"
PKG_REV="1"
PKG_ARCH="any"
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/sonninnos/beetle-saturn-libretro/"
PKG_URL="$PKG_SITE/archive/$PKG_VERSION.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_SHORTDESC=" Standalone  hard fork of Mednafen Saturn to the libretro API.  "
PKG_TOOLCHAIN="make"
PKG_BUILD_FLAGS="+speed" 
CXXFLAGS="-O3 -march=armv8-a+crc+fp+simd -mtune=cortex-a73.cortex-a53 -flto"

makeinstall_target() {
  mkdir -p $INSTALL/usr/lib/libretro
  cp mednafen_saturn_*.so $INSTALL/usr/lib/libretro/
}
