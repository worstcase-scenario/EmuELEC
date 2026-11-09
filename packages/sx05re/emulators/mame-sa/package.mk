# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="mame-sa"
PKG_VERSION="mame0289"
PKG_ARCH="aarch64"
PKG_SHA256="0929cc749afabcef892900e10dd90bd8b05f94a7dde8f367ac6a5d2082589f84"
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/mamedev/mame"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_ttf alsa-lib zlib flac sqlite expat fontconfig"
PKG_LONGDESC="MAME standalone (SDL2 OSD, KMSDRM)"
PKG_TOOLCHAIN="make"

pre_configure_target() {
  PKG_MAKE_OPTS_TARGET="OSD=sdl TARGETOS=linux CROSS_BUILD=1 PLATFORM=arm64 \
    SUBTARGET=mame TOOLS=0 NOWERROR=1 OPTIMIZE=2 PYTHON_EXECUTABLE=python3 \
    SDL_INSTALL_ROOT=${SYSROOT_PREFIX}/usr \
    NO_X11=1 NO_USE_XINPUT=1 USE_WAYLAND=0 NO_OPENGL=1 USE_QTDEBUG=0 \
    NO_USE_PORTAUDIO=1 NO_USE_PULSEAUDIO=1 NO_USE_PIPEWIRE=1 \
    USE_SYSTEM_LIB_EXPAT=1 USE_SYSTEM_LIB_ZLIB=1 \
    USE_SYSTEM_LIB_FLAC=1 USE_SYSTEM_LIB_SQLITE3=1"
  unset ARCH DISTRO PROJECT
}

make_target() {
  env -u CFLAGS -u CXXFLAGS -u CPPFLAGS -u LDFLAGS \
    make -C 3rdparty/genie/build/gmake.linux -f genie.make CC=${HOST_CC} config=release
  make ${PKG_MAKE_OPTS_TARGET} OVERRIDE_CC=${CC} OVERRIDE_CXX=${CXX} OVERRIDE_LD=${LD} AR=${AR} -j6
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin ${INSTALL}/usr/share/mame
  cp mame ${INSTALL}/usr/bin/mame-sa
  cp -r bgfx hash plugins language ${INSTALL}/usr/share/mame/
  cp ${PKG_DIR}/scripts/mamesastart.sh ${INSTALL}/usr/bin/
}
