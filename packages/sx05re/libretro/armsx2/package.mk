# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="armsx2"
PKG_VERSION="091a8b3e1bce77352549a2b862f2c21770a515e2"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/ARMSX2/ARMSX2"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain llvm:host zlib curl fontconfig systemd dbus"
PKG_LONGDESC="ARMSX2 - PlayStation 2 emulator for ARM64 (libretro core, Vulkan)"
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

  PKG_CMAKE_OPTS_TARGET="-DCMAKE_TOOLCHAIN_FILE=${PKG_BUILD}/clang.cmake \
                         -DCMAKE_PREFIX_PATH=${DEPS} \
                         -DENABLE_QT_UI=OFF \
                         -DENABLE_SDL_FRONTEND=OFF \
                         -DENABLE_LIBRETRO=ON \
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
  ninja ${NINJA_OPTS} pcsx2-libretro
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/lib/libretro
  cp $(find . -name armsx2_libretro.so | head -1) ${INSTALL}/usr/lib/libretro/
}
