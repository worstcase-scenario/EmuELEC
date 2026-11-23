# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="geartowns"
PKG_VERSION="88f4fa628bb9434afb56442e8b1c149b76e33a78"
PKG_LICENSE="GPLv3"
PKG_SITE="https://github.com/drhelius/Geartowns"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="Geartowns - Fujitsu FM Towns emulator (libretro core)"
PKG_TOOLCHAIN="make"

make_target() {
  make -C platforms/libretro platform=unix
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/lib/libretro
  cp platforms/libretro/geartowns_libretro.so ${INSTALL}/usr/lib/libretro/
}
