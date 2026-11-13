# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="azahar-sa"
PKG_VERSION="b9e75554390d6b66d419146860f5bc2bf9052034"
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/Diegrosan/azahar"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain SDL2"
PKG_LONGDESC="Azahar Nintendo 3DS emulator (SDL2 frontend, Vulkan)"
PKG_TOOLCHAIN="cmake"
GET_HANDLER_SUPPORT="git"

PKG_CMAKE_OPTS_TARGET="-DCMAKE_BUILD_TYPE=Release \
                       -DENABLE_QT=OFF \
                       -DENABLE_QT_TRANSLATION=OFF \
                       -DENABLE_SDL2=ON \
                       -DENABLE_SDL2_FRONTEND=ON \
                       -DUSE_SYSTEM_SDL2=ON \
                       -DENABLE_VULKAN=ON \
                       -DENABLE_OPENGL=OFF \
                       -DENABLE_LIBRETRO=OFF \
                       -DENABLE_TESTS=OFF \
                       -DENABLE_ROOM=OFF \
                       -DENABLE_WEB_SERVICE=OFF \
                       -DENABLE_SCRIPTING=OFF \
                       -DENABLE_GDBSTUB=OFF \
                       -DENABLE_OPENAL=OFF \
                       -DENABLE_CUBEB=ON \
                       -DENABLE_LIBUSB=OFF \
                       -DENABLE_FFMPEG=OFF \
                       -DENABLE_DISCORD_RPC=OFF \
                       -DENABLE_LTO=OFF \
                       -DCITRA_USE_PRECOMPILED_HEADERS=OFF \
                       -DCITRA_WARNINGS_AS_ERRORS=OFF"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_BUILD}/.${TARGET_NAME}/bin/Release/azahar ${INSTALL}/usr/bin/
  cp ${PKG_DIR}/scripts/azaharstart.sh ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/azaharstart.sh
  mkdir -p ${INSTALL}/usr/config/emuelec/configs/gptokeyb
  cp ${PKG_DIR}/config/azahar.gptk ${INSTALL}/usr/config/emuelec/configs/gptokeyb/
}
