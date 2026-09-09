PKG_NAME="simcoupe"
PKG_VERSION="1.2"
PKG_REV="1"
PKG_ARCH="any"
PKG_LICENSE="GPL"
PKG_SITE="https://github.com/simonowen/simcoupe"
PKG_URL="$PKG_SITE/archive/refs/heads/master.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 zlib libpng"
PKG_PRIORITY="optional"
PKG_SECTION="emuelec/emulators"
PKG_SHORTDESC="SimCoupe - SAM Coupe emulator"
PKG_LONGDESC="SimCoupe is a SAM Coupe emulator for various platforms"
PKG_TOOLCHAIN="cmake"

pre_configure_target() {
  PKG_CMAKE_OPTS_TARGET="-DCMAKE_BUILD_TYPE=Release"
}

makeinstall_target() {
  # Binary + Wrapper
  mkdir -p ${INSTALL}/usr/bin
  cp -f $PKG_BUILD/.$TARGET_NAME/simcoupe ${INSTALL}/usr/bin/simcoupe
  chmod +x ${INSTALL}/usr/bin/simcoupe

  cp -f ${PKG_DIR}/scripts/simcoupestart.sh ${INSTALL}/usr/bin/simcoupestart.sh
  chmod +x ${INSTALL}/usr/bin/simcoupestart.sh

  # SAASound
  mkdir -p ${INSTALL}/usr/lib
  cp -f $PKG_BUILD/.$TARGET_NAME/_deps/saasound-build/libSAASound.so* ${INSTALL}/usr/lib/ 2>/dev/null || :

  # ROM resources
  mkdir -p ${INSTALL}/usr/share/simcoupe
  cp -f $PKG_BUILD/Resource/*.rom  ${INSTALL}/usr/share/simcoupe/ 2>/dev/null || :
  cp -f $PKG_BUILD/Resource/*.zx82 ${INSTALL}/usr/share/simcoupe/ 2>/dev/null || :
  cp -f $PKG_BUILD/Resource/*.bin  ${INSTALL}/usr/share/simcoupe/ 2>/dev/null || :

  # GPTK file
  if [ -f "${PKG_DIR}/config/simcoupe.gptk" ]; then
    mkdir -p ${INSTALL}/usr/config/emuelec/configs/gptokeyb
    cp -f "${PKG_DIR}/config/simcoupe.gptk" \
      "${INSTALL}/usr/config/emuelec/configs/gptokeyb/simcoupe.gptk"
  fi

}
