# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

PKG_NAME="openmsx-ld"
PKG_VERSION="f3b2a5915f410687104a6b0b94800634ce550a22"
PKG_SHA256="360cda04176ab7de0f26ebf83cf1a7d5faec60176e862b30aca390146e544da4"
PKG_REV="0"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL"
PKG_SITE="https://github.com/worstcase-scenario/openMSX"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_ttf libpng zlib tcl alsa-lib glew gl4es libogg libvorbis libtheora"
PKG_SHORTDESC="openMSX Laserdisc: Pioneer PX-7 emulation for Palcom LaserDisc games"
PKG_TOOLCHAIN="manual"

pre_configure_target() {
  # gl4es installs libGL only into the image, not the sysroot (see its
  # package.mk). openMSX needs it at build time for the GL renderer.
  cp -f $(get_build_dir gl4es)/lib/libGL.so.1 ${SYSROOT_PREFIX}/usr/lib/libGL.so
  ln -sf libGL.so ${SYSROOT_PREFIX}/usr/lib/libGL.so.1
  cp -rf $(get_build_dir gl4es)/include/* ${SYSROOT_PREFIX}/usr/include/
}

PKG_MAKE_OPTS_TARGET="OPENMSX_TARGET_CPU=${TARGET_ARCH} \
                      OPENMSX_TARGET_OS=linux \
                      OPENMSX_FLAVOUR=opt \
                      INSTALL_BASE=/usr \
                      INSTALL_SHARE_DIR=/usr/share/openmsx-ld \
                      INSTALL_DOC_DIR=/usr/share/doc/openmsx-ld"

make_target() {
  LIBTOOL_SYSROOT_PATH="${SYSROOT_PREFIX}" \
    make -C ${PKG_BUILD} ${PKG_MAKE_OPTS_TARGET}
}

makeinstall_target() {
  LIBTOOL_SYSROOT_PATH="${SYSROOT_PREFIX}" \
    make -C ${PKG_BUILD} ${PKG_MAKE_OPTS_TARGET} DESTDIR=${INSTALL} install

  mv ${INSTALL}/usr/bin/openmsx ${INSTALL}/usr/bin/openmsx-ld
  install -m 0755 ${PKG_DIR}/scripts/startopenmsx-ld.sh ${INSTALL}/usr/bin/

  mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk
  cp ${PKG_DIR}/config/openmsx-ld.gptk \
    ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk/
}