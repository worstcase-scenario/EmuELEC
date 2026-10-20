# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="armsx2SA"
PKG_VERSION="091a8b3e1bce77352549a2b862f2c21770a515e2"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/ARMSX2/ARMSX2"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain llvm:host zlib curl fontconfig systemd dbus"
PKG_LONGDESC="ARMSX2 - PlayStation 2 emulator for ARM64 (standalone SDL3 frontend, Vulkan via VK_KHR_display)"
PKG_TOOLCHAIN="cmake"

pre_configure_target() {
  DEPS="${PKG_BUILD}/deps"

  # Toolchain wrapper: lets find_package see the static deps prefix
  cat > ${PKG_BUILD}/cross.cmake <<EOF
include(${CMAKE_CONF})
list(APPEND CMAKE_FIND_ROOT_PATH "${DEPS}")
set(CMAKE_PROJECT_INCLUDE "${PKG_BUILD}/imports.cmake")
EOF
  # Static FreeType links ZLIB::ZLIB, PNG::PNG and HarfBuzz::HarfBuzz, which its consumers never define
  cat > ${PKG_BUILD}/imports.cmake <<EOF
find_package(ZLIB)
find_package(PNG)
if(EXISTS "${DEPS}/lib/libharfbuzz.a" AND NOT PROJECT_NAME STREQUAL "freetype" AND NOT TARGET HarfBuzz::HarfBuzz)
  add_library(HarfBuzz::HarfBuzz STATIC IMPORTED)
  set_target_properties(HarfBuzz::HarfBuzz PROPERTIES
    IMPORTED_LOCATION "${DEPS}/lib/libharfbuzz.a"
    INTERFACE_INCLUDE_DIRECTORIES "${DEPS}/include/harfbuzz")
endif()
EOF

  # Upstream dependency script, static mode; libbacktrace needs --host for cross
  sed -i 's|./configure --prefix="$INSTALLDIR"|./configure --host='"${TARGET_NAME}"' --prefix="$INSTALLDIR"|' \
    ${PKG_BUILD}/.github/workflows/scripts/linux/build-dependencies-runner.sh

  mkdir -p ${PKG_BUILD}/deps-build
  (cd ${PKG_BUILD}/deps-build && \
    CMAKE_TOOLCHAIN_FILE=${PKG_BUILD}/cross.cmake ARMSX2_DEPS_STATIC=1 \
    ${PKG_BUILD}/.github/workflows/scripts/linux/build-dependencies-runner.sh "${DEPS}")

  # ARM64 JIT needs __attribute__((preserve_most)), which GCC lacks: core itself is built with clang from llvm:host
  cat > ${PKG_BUILD}/clang.cmake <<EOF
include(${PKG_BUILD}/cross.cmake)
set(CMAKE_SYSROOT ${SYSROOT_PREFIX})
set(CMAKE_C_COMPILER ${TOOLCHAIN}/bin/clang)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN}/bin/clang++)
set(CMAKE_C_COMPILER_TARGET ${TARGET_NAME})
set(CMAKE_CXX_COMPILER_TARGET ${TARGET_NAME})
set(CMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN ${TOOLCHAIN})
set(CMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN ${TOOLCHAIN})
EOF
  # clang rejects GCC's -mabi=lp64 (the aarch64 default anyway) and big.LITTLE -mtune syntax
  CFLAGS="${CFLAGS//-mabi=lp64/}"; CFLAGS="${CFLAGS//cortex-a73.cortex-a53/cortex-a55}"
  CXXFLAGS="${CXXFLAGS//-mabi=lp64/}"; CXXFLAGS="${CXXFLAGS//cortex-a73.cortex-a53/cortex-a55}"
  # Amlogic-no is Cortex-A55 (ARMv8.2): enable LSE atomics, which the toolchain's -march=armv8-a leaves out
  CFLAGS="${CFLAGS//-march=armv8-a/-march=armv8.2-a}"
  CXXFLAGS="${CXXFLAGS//-march=armv8-a/-march=armv8.2-a}"

  PKG_CMAKE_OPTS_TARGET="-DCMAKE_TOOLCHAIN_FILE=${PKG_BUILD}/clang.cmake \
                         -DCMAKE_PREFIX_PATH=${DEPS} \
                         -DENABLE_QT_UI=OFF \
                         -DENABLE_SDL_FRONTEND=ON \
                         -DENABLE_LIBRETRO=OFF \
                         -DENABLE_GSRUNNER=OFF \
                         -DENABLE_TESTS=OFF \
                         -DENABLE_RECOMPILER_TEST_HOOKS=OFF \
                         -DENABLE_SETCAP=OFF \
                         -DUSE_BACKTRACE=OFF \
                         -DX11_API=OFF \
                         -DWAYLAND_API=OFF \
                         -DDISABLE_ADVANCE_SIMD=TRUE \
                         -DHOST_PAGE_SIZE=4096 \
                         -DHOST_CACHE_LINE_SIZE=64 \
                         -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON"
}

make_target() {
  ninja ${NINJA_OPTS} pcsx2-sdl
}

makeinstall_target() {
  # armsx2-sdl expects its resources directory next to the binary
  mkdir -p ${INSTALL}/usr/share/armsx2SA
  cp bin/armsx2-sdl ${INSTALL}/usr/share/armsx2SA/
  cp -r bin/resources ${INSTALL}/usr/share/armsx2SA/
  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/armsx2start.sh ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/armsx2start.sh
  cp ${PKG_DIR}/config/PCSX2.ini ${INSTALL}/usr/share/armsx2SA/
}