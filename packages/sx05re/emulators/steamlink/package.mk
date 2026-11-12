# SPDX-License-Identifier: GPL-2.0

PKG_NAME="steamlink"
PKG_VERSION="1.0"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL-2.0"
PKG_SITE="https://help.steampowered.com/faqs/view/6424-467A-31D9-C6CB"
PKG_DEPENDS_TARGET="toolchain ${OPENGLES} curl libdrm gl4es libepoxy libinput mtdev double-conversion md4c krb5 ffmpeg-steamlink"
PKG_LONGDESC="Steam Link for Amlogic-no. Valve's Raspberry Pi arm64 build is downloaded on first start (not redistributable); shims adapt it to the Amlogic vendor DRM driver and the Mali blob."
PKG_TOOLCHAIN="manual"

make_target() {
  ${CC} ${CFLAGS} -shared -fPIC -o libdrm_shim.so ${PKG_DIR}/sources/drm_shim.c -ldl -lpthread
  # linked against libEGL: SDL loads it as its EGL library and resolves all other EGL symbols through it
  ${CC} ${CFLAGS} -shared -fPIC -o libegl_shim.so ${PKG_DIR}/sources/egl_shim.c -lEGL -ldl
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/lib/steamlink
  cp -f libdrm_shim.so libegl_shim.so ${INSTALL}/usr/lib/steamlink/

  mkdir -p ${INSTALL}/usr/bin
  cp -f ${PKG_DIR}/scripts/steamlinkstart.sh ${INSTALL}/usr/bin/steamlinkstart.sh
  chmod +x ${INSTALL}/usr/bin/steamlinkstart.sh

  # entry for the EmulationStation system
  mkdir -p ${INSTALL}/usr/share/steamlink
  touch "${INSTALL}/usr/share/steamlink/Steam Link.steamlink"
  cp -f ${PKG_DIR}/config/gamelist.xml ${PKG_DIR}/config/steamlink.png ${INSTALL}/usr/share/steamlink/
}
