# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025-present Team EmuELEC (https://github.com/EmuELEC)

PKG_NAME="x16"
PKG_VERSION="r49"
PKG_SHA256=""
PKG_LICENSE="BSD-2-Clause"
PKG_SITE="https://github.com/X16Community/x16-emulator"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 zlib"
PKG_LONGDESC="Emulator for the Commander X16 8-bit computer"
PKG_TOOLCHAIN="manual"

make_target() {
  cd ${PKG_BUILD}
  sed -i 's/-O3 -Wall -Werror -g/-O3 -Wall/; s/-O3 -Wall -Werror -I/-O3 -Wall -I/' Makefile
  make x16emu CC="${CC}" CXX="${CXX}" SDL2CONFIG="pkg-config sdl2"
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  install -m 0755 ${PKG_BUILD}/x16emu ${INSTALL}/usr/bin/
  mkdir -p ${INSTALL}/usr/share/x16-emulator
  install -m 0644 ${PKG_DIR}/files/rom.bin ${INSTALL}/usr/share/x16-emulator/
  install -m 0755 ${PKG_DIR}/scripts/x16emustart.sh ${INSTALL}/usr/bin/
}
