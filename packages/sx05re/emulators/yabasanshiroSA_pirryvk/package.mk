# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="yabasanshiroSA_pirryvk"
PKG_VERSION="e4ae72beb7eb0220abc3aa8778b34b956691db92"
PKG_ARCH="aarch64"
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/mariano-london/yabasanshiro-pirry-vulkan"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain SDL2 libdrm boost openal-soft ${OPENGLES} zlib vulkan-headers vulkan-loader shaderc yabasanshiroSA_pirry"
PKG_LONGDESC="yabasanshiro-pirry-vulkan 0.9.0, yabasanshiro-pirry with Vulkan renderer (test release)"
PKG_TOOLCHAIN="cmake-make"
GET_HANDLER_SUPPORT="git"

post_unpack() {
  # use host versions
  sed -i "s|COMMAND m68kmake|COMMAND ${PKG_BUILD}/m68kmake_host|" ${PKG_BUILD}/yabause/src/musashi/CMakeLists.txt
  sed -i "s|COMMAND ./bin2c|COMMAND ${PKG_BUILD}/bin2c_host|" ${PKG_BUILD}/yabause/src/retro_arena/nanogui-sdl/CMakeLists.txt
}

pre_make_target() {
  ${HOST_CC} ${PKG_BUILD}/yabause/src/retro_arena/nanogui-sdl/resources/bin2c.c -o ${PKG_BUILD}/bin2c_host
  ${HOST_CC} ${PKG_BUILD}/yabause/src/musashi/m68kmake.c -o ${PKG_BUILD}/m68kmake_host
}

pre_configure_target() {
  # The system SDL2 is Mali fbdev without Vulkan: link a private static SDL2 with KMSDRM + Vulkan
  SDL2P="${PKG_BUILD}/sdl2-inst"
  cmake -S $(get_build_dir SDL2) -B ${PKG_BUILD}/sdl2-build -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE=${CMAKE_CONF} -DCMAKE_INSTALL_PREFIX=${SDL2P} -DCMAKE_BUILD_TYPE=Release \
        -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TEST=OFF \
        -DSDL_MALI=OFF -DSDL_KMSDRM=ON -DSDL_VULKAN=ON -DSDL_OPENGLES=ON \
        -DSDL_X11=OFF -DSDL_WAYLAND=OFF -DSDL_ALSA=ON -DSDL_PULSEAUDIO=ON -DSDL_HIDAPI_JOYSTICK=OFF
  ninja -C ${PKG_BUILD}/sdl2-build ${NINJA_OPTS} install

  PKG_CMAKE_OPTS_TARGET="${PKG_BUILD}/yabause \
                         -DYAB_PORTS=retro_arena \
                         -DYAB_WANT_DYNAREC_DEVMIYAX=ON \
                         -DYAB_WANT_ARM7=OFF \
                         -DCMAKE_TOOLCHAIN_FILE=${PKG_BUILD}/yabause/src/retro_arena/n2.cmake \
                         -DYAB_WANT_VULKAN=ON \
                         -DYAB_VK_SDL=ON \
                         -DSDL2_DIR=${SDL2P}/lib/cmake/SDL2 \
                         -DSDL2_INCLUDE_DIR=${SDL2P}/include/SDL2 \
                         -DSDL2_LIBRARY=${SDL2P}/lib/libSDL2.a;-lasound;-ldl;-lpthread;-lm \
                         -DSHADERC_LIBRARIES=${SYSROOT_PREFIX}/usr/lib/libshaderc_combined.a \
                         -DSHADERC_INCLUDE_DIR=${SYSROOT_PREFIX}/usr/include \
                         -DOPENGL_INCLUDE_DIR=${SYSROOT_PREFIX}/usr/include \
                         -DOPENGL_opengl_LIBRARY=${SYSROOT_PREFIX}/usr/lib \
                         -DOPENGL_glx_LIBRARY=${SYSROOT_PREFIX}/usr/lib \
                         -DLIBPNG_LIB_DIR=${SYSROOT_PREFIX}/usr/lib \
                         -Dpng_STATIC_LIBRARIES=${SYSROOT_PREFIX}/usr/lib/libpng16.a \
                         -DCMAKE_BUILD_TYPE=Release"
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  # started by yabasanshiro_pirry.sh (package yabasanshiroSA_pirry) with argument "vk"
  cp -a ${PKG_BUILD}/src/retro_arena/yabasanshiro ${INSTALL}/usr/bin/yabasanshiro_pirryvk
}
