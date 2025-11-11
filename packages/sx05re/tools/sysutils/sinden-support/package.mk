# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="sinden-support"
PKG_VERSION="1.0"
PKG_LICENSE="GPL2"
PKG_SITE="https://sindenlightgun.com"
PKG_URL=""
PKG_DEPENDS_TARGET="toolchain systemd Python3 pyudev python-evdev"
PKG_LONGDESC="User-space helpers that integrate the proprietary Sinden Lightgun runtime with EmuELEC."
PKG_TOOLCHAIN="manual"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/sinden-controller ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/sinden-driver ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/sinden-hotplug ${INSTALL}/usr/bin

  chmod 0755 \
    ${INSTALL}/usr/bin/sinden-controller \
    ${INSTALL}/usr/bin/sinden-driver \
    ${INSTALL}/usr/bin/sinden-hotplug

  mkdir -p ${INSTALL}/usr/lib/systemd/system
  cp ${PKG_DIR}/system.d/*.service ${INSTALL}/usr/lib/systemd/system

  mkdir -p ${INSTALL}/usr/lib/udev/rules.d
  cp ${PKG_DIR}/udev.d/*.rules ${INSTALL}/usr/lib/udev/rules.d

  mkdir -p ${INSTALL}/usr/lib/tmpfiles.d
  cp ${PKG_DIR}/tmpfiles.d/*.conf ${INSTALL}/usr/lib/tmpfiles.d

  mkdir -p ${INSTALL}/usr/share/sinden
  cp -a ${PKG_DIR}/share/. ${INSTALL}/usr/share/sinden
}

post_install() {
  :
}
