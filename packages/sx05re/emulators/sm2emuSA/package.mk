# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="sm2emuSA"
PKG_VERSION="be696244fc425f55e3c0cab9bc43c03d44b621aa"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/Zer0one/sm2-emu-libretro"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain shaderc:host vulkan-headers vulkan-loader ${OPENGLES} libdrm alsa-lib systemd fontconfig"
PKG_LONGDESC="SM2-Emu - Sega Model 2 emulator (standalone, SDL3, Vulkan and OpenGL ES)"
PKG_TOOLCHAIN="cmake"
GET_HANDLER_SUPPORT="git"

PKG_CMAKE_OPTS_TARGET="-DSM2_BUILD_VULKAN=ON \
                       -DSM2_BUILD_OPENGL_DESKTOP=OFF \
                       -DSM2_BUILD_OPENGL_ES=ON \
                       -DSM2_GLSLC=${TOOLCHAIN}/bin/glslc \
                       -DSDL_UNIX_CONSOLE_BUILD=ON \
                       -DSDL_X11=OFF \
                       -DSDL_WAYLAND=OFF \
                       -DSDL_KMSDRM=ON \
                       -DCMAKE_BUILD_TYPE=Release"

# m68kmake is an ExternalProject built for the host, but it inherits the
# target CC/CFLAGS from the environment -> force the host compiler
pre_configure_target() {
  sed -i "s|\"-DCMAKE_BUILD_TYPE=Release\"\$|\"-DCMAKE_BUILD_TYPE=Release\" \"-DCMAKE_C_COMPILER=${HOST_CC}\" \"-DCMAKE_C_FLAGS=\" \"-DCMAKE_EXE_LINKER_FLAGS=\"|" ${PKG_BUILD}/cmake/Dependencies.cmake
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/share/sm2emuSA ${INSTALL}/usr/bin
  cp bin/sm2-emu ${PKG_BUILD}/data/games.xml ${INSTALL}/usr/share/sm2emuSA
  cp ${PKG_DIR}/scripts/sm2emustart.sh ${INSTALL}/usr/bin
}
