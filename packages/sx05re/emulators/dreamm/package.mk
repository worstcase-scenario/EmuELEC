# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2024-present Harakiri (https://github.com/worstcase-scenario)

PKG_NAME="dreamm"
PKG_VERSION="4.0"
PKG_SHA256="a22761289bcd4bb1c49f9de5b374836facbeb76b31d721c57a707f05bfbc6ae4"
PKG_ARCH="aarch64"
PKG_LICENSE="Freeware"
PKG_SITE="https://dreamm.aarongiles.com/"
PKG_URL="https://dreamm.aarongiles.com/releases/dreamm-${PKG_VERSION}-linux-arm64.tgz"
PKG_SOURCE_NAME="dreamm-${PKG_VERSION}-linux-arm64.tgz"
PKG_DEPENDS_TARGET="toolchain SDL2"
PKG_LONGDESC="DREAMM - DOS Recreation Engine And Multimedia Microcomputer, a purpose-built emulator for LucasArts games"
PKG_TOOLCHAIN="manual"

unpack() {
  mkdir -p ${PKG_BUILD}
  tar -xf ${SOURCES}/${PKG_NAME}/${PKG_SOURCE_NAME} -C ${PKG_BUILD}
}

pre_make_target() {
  cp -f ${PKG_DIR}/sources/dreamm_cursor.c ${PKG_BUILD}/
}

make_target() {
  cd ${PKG_BUILD}
  ${CC} --sysroot=${SYSROOT_PREFIX} \
    -shared -fPIC -O2 \
    -o dreamm_cursor.so dreamm_cursor.c -ldl
  ${STRIP} dreamm_cursor.so
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/config/emuelec/bin
    cp -f ${PKG_BUILD}/dreamm ${INSTALL}/usr/config/emuelec/bin/
    cp -f ${PKG_BUILD}/dreamm_cursor.so ${INSTALL}/usr/config/emuelec/bin/
    cp -f ${PKG_DIR}/scripts/dreammstart.sh ${INSTALL}/usr/config/emuelec/bin/
    chmod 0755 ${INSTALL}/usr/config/emuelec/bin/dreamm
    chmod 0755 ${INSTALL}/usr/config/emuelec/bin/dreammstart.sh
}