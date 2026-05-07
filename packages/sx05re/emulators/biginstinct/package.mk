# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

PKG_NAME="biginstinct"
PKG_VERSION="10"
PKG_SHA256="5c29befbabefa6f65c60149de670e382101a315f41a20cdd2e738d59268c1629"
PKG_ARCH="aarch64"
PKG_LICENSE="Proprietary"
PKG_SITE="https://www.richwhitehouse.com/ki"
PKG_URL="https://www.richwhitehouse.com/ki/builds/BigInstinct_LinuxARM64_v${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/emulators"
PKG_SHORTDESC="BigInstinct - Killer Instinct Arcade Emulator"
PKG_TOOLCHAIN="manual"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin/biginstinct
  cp -rv ${PKG_BUILD}/* ${INSTALL}/usr/bin/biginstinct/
  chmod +x ${INSTALL}/usr/bin/biginstinct/biginstinct

  cp -f ${PKG_DIR}/scripts/biginstinctstart.sh ${INSTALL}/usr/bin/biginstinctstart.sh
  chmod +x ${INSTALL}/usr/bin/biginstinctstart.sh
}