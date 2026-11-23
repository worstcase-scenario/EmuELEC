# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="keisho"
PKG_VERSION="d7c7dd885bcf46bfc67c30ce70fa6fedb0866168"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/dmanlfc/sm2-emu"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain shaderc:host vulkan-headers vulkan-loader ${OPENGLES} libdrm alsa-lib systemd fontconfig SDL3"
PKG_LONGDESC="Keisho (formerly SM2-Emu) - Sega Model 1, 2 and 3 emulator (standalone, SDL3, Vulkan and OpenGL ES)"
PKG_TOOLCHAIN="cmake"
GET_HANDLER_SUPPORT="git"

PKG_CMAKE_OPTS_TARGET="-DSM2_BUILD_VULKAN=ON \
                       -DSM2_BUILD_OPENGL_DESKTOP=OFF \
                       -DSM2_BUILD_OPENGL_ES=ON \
                       -DSM2_GLSLC=${TOOLCHAIN}/bin/glslc \
                       -DCMAKE_BUILD_TYPE=Release"

# m68kmake is an ExternalProject built for the host, but it inherits the
# target CC/CFLAGS from the environment -> force the host compiler
pre_configure_target() {
  sed -i "s|\"-DCMAKE_BUILD_TYPE=Release\"\$|\"-DCMAKE_BUILD_TYPE=Release\" \"-DCMAKE_C_COMPILER=${HOST_CC}\" \"-DCMAKE_C_FLAGS=\" \"-DCMAKE_EXE_LINKER_FLAGS=\"|" ${PKG_BUILD}/cmake/Dependencies.cmake
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/share/keisho ${INSTALL}/usr/bin
  cp bin/keisho ${PKG_BUILD}/data/games.xml ${INSTALL}/usr/share/keisho
  cp -r ${PKG_BUILD}/data/lang ${INSTALL}/usr/share/keisho
  cp ${PKG_DIR}/scripts/keishostart.sh ${INSTALL}/usr/bin
}
