# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

PKG_NAME="bigpemu"
PKG_VERSION="121"
PKG_SHA256="ac524e91fa6e90d9256d247d410279315fff9b61b6317c5f23172225139cceb1"
PKG_ARCH="aarch64"
PKG_LICENSE="Proprietary"
PKG_SITE="https://www.richwhitehouse.com/jaguar"
PKG_URL="https://www.richwhitehouse.com/jaguar/builds/BigPEmu_LinuxARM64_v${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/emulators"
PKG_SHORTDESC="BigPEmu - Atari Jaguar Emulator"
PKG_TOOLCHAIN="manual"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin/bigpemu
  cp -rv ${PKG_BUILD}/* ${INSTALL}/usr/bin/bigpemu/
  chmod +x ${INSTALL}/usr/bin/bigpemu/bigpemu

  cp -f ${PKG_DIR}/scripts/bigpemustart.sh ${INSTALL}/usr/bin/bigpemustart.sh
  chmod +x ${INSTALL}/usr/bin/bigpemustart.sh
}