# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2020-present Shanti Gilbert (https://github.com/shantigilbert)

PKG_NAME="dosbox-staging"
PKG_VERSION="8888ea1b2578a0ee099600eb6aba1eb85542078f" # v0.83.1
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/dosbox-staging/dosbox-staging"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain alsa-lib SDL2 SDL2_image libpng zlib zlib-ng opusfile speexdsp fluidsynth munt iir1 asio"
PKG_LONGDESC="DOS/x86 emulator focusing on ease of use"
PKG_GIT_CLONE_BRANCH="release/0.83.x"
GET_HANDLER_SUPPORT="git"
PKG_TOOLCHAIN="cmake"

# system libraries as in the release-linux preset; no desktop OpenGL, no ManyMouse
PKG_CMAKE_OPTS_TARGET="-DIS_PRESET_USED=TRUE \
                       -DUSE_SYSTEM_LIBS=ON \
                       -DOPT_TESTS=OFF \
                       -DOPT_MANYMOUSE=OFF \
                       -DCMAKE_DISABLE_FIND_PACKAGE_OpenGL=ON"

pre_configure_target() {
  # asio is header-only and not installed to the sysroot (PKG_BUILD_FLAGS="-sysroot")
  export CXXFLAGS="${CXXFLAGS} -I$(get_build_dir asio)/asio/include"
}

post_makeinstall_target() {
  rm -rf ${INSTALL}/usr/share/{applications,doc,icons,man,metainfo}
  mkdir -p ${INSTALL}/usr/config/dosbox
  cp -a ${PKG_DIR}/scripts/* ${INSTALL}/usr/bin/
  cp -a ${PKG_DIR}/config/* ${INSTALL}/usr/config/dosbox/
}
