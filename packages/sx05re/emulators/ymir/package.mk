# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="ymir"
PKG_VERSION="0fdabbdd41f17fd7fda58195130c3b43f7fd00e5"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/StrikerX3/Ymir"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain llvm:host dxc:host SDL3 vulkan-headers vulkan-loader alsa-lib openssl curl zlib zstd nlohmann-json"
PKG_LONGDESC="Ymir - Sega Saturn emulator (SDL3 frontend, Vulkan VDP renderer)"
PKG_TOOLCHAIN="cmake"
GET_HANDLER_SUPPORT="git"

pre_configure_target() {
  # Clang is upstream's compiler of choice (GCC 12 is older than any tested toolchain)
  cat > ${PKG_BUILD}/clang.cmake <<EOT
include(${CMAKE_CONF})
set(CMAKE_SYSROOT ${SYSROOT_PREFIX})
set(CMAKE_C_COMPILER ${TOOLCHAIN}/bin/clang)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN}/bin/clang++)
set(CMAKE_C_COMPILER_TARGET ${TARGET_NAME})
set(CMAKE_CXX_COMPILER_TARGET ${TARGET_NAME})
set(CMAKE_ASM_COMPILER_TARGET ${TARGET_NAME})
set(CMAKE_C_COMPILER_EXTERNAL_TOOLCHAIN ${TOOLCHAIN})
set(CMAKE_CXX_COMPILER_EXTERNAL_TOOLCHAIN ${TOOLCHAIN})
EOT
  # clang rejects GCC's -mabi=lp64 and big.LITTLE -mtune syntax
  CFLAGS="$(echo "${CFLAGS//-mabi=lp64/}" | sed 's/-mtune=[^ ]*//g')"
  CXXFLAGS="$(echo "${CXXFLAGS//-mabi=lp64/}" | sed 's/-mtune=[^ ]*//g')"

  # Dependencies upstream takes from vcpkg and the tree does not have (versions from its vcpkg baseline)
  cat > ${PKG_BUILD}/deps.cmake <<'EOT'
include(FetchContent)
set(BUILD_SHARED_LIBS OFF)
set(JUST_INSTALL_CEREAL ON)
set(RTMIDI_BUILD_TESTING OFF)
set(RTMIDI_API_JACK OFF)
FetchContent_Declare(cereal GIT_REPOSITORY https://github.com/USCiLab/cereal.git GIT_TAG v1.3.2 OVERRIDE_FIND_PACKAGE)
FetchContent_Declare(cxxopts GIT_REPOSITORY https://github.com/jarro2783/cxxopts.git GIT_TAG v3.3.1 OVERRIDE_FIND_PACKAGE)
FetchContent_Declare(date GIT_REPOSITORY https://github.com/HowardHinnant/date.git GIT_TAG v3.0.5 OVERRIDE_FIND_PACKAGE)
FetchContent_Declare(tomlplusplus GIT_REPOSITORY https://github.com/marzer/tomlplusplus.git GIT_TAG v3.4.0 OVERRIDE_FIND_PACKAGE)
# Source in a dir named rtmidi: Ymir includes <rtmidi/RtMidi.h>
FetchContent_Declare(rtmidi GIT_REPOSITORY https://github.com/thestk/rtmidi.git GIT_TAG 6.0.0 SOURCE_DIR ${CMAKE_BINARY_DIR}/_deps/rtmidi/rtmidi OVERRIDE_FIND_PACKAGE)
FetchContent_Declare(semver GIT_REPOSITORY https://github.com/Neargye/semver.git GIT_TAG v1.0.1)
# vulkan.hpp of the tree (1.3.241) lacks vk::True & co.: headers of upstream's Vulkan SDK, loader stays the system one
FetchContent_Declare(vulkan_headers GIT_REPOSITORY https://github.com/KhronosGroup/Vulkan-Headers.git GIT_TAG v1.4.357 GIT_SHALLOW TRUE SOURCE_SUBDIR none)
FetchContent_MakeAvailable(cereal cxxopts date tomlplusplus rtmidi semver vulkan_headers)
set(Vulkan_INCLUDE_DIR ${vulkan_headers_SOURCE_DIR}/include CACHE PATH "" FORCE)
add_library(RtMidi::rtmidi ALIAS rtmidi)
target_include_directories(rtmidi INTERFACE $<BUILD_INTERFACE:${CMAKE_BINARY_DIR}/_deps/rtmidi>)
# Ymir includes semver.hpp without linking a target
include_directories(${semver_SOURCE_DIR}/include)
EOT

  PKG_CMAKE_OPTS_TARGET="-DCMAKE_TOOLCHAIN_FILE=${PKG_BUILD}/clang.cmake \
                         -DCMAKE_PROJECT_Ymir_INCLUDE=${PKG_BUILD}/deps.cmake \
                         -DCMAKE_BUILD_TYPE=Release \
                         -DDXC_EXECUTABLE=${TOOLCHAIN}/bin/dxc \
                         -DYmir_DEV_BUILD=OFF \
                         -DYmir_ENABLE_TESTS=OFF \
                         -DYmir_ENABLE_SANDBOX=OFF \
                         -DYmir_ENABLE_YMDASM=OFF \
                         -DYmir_ENABLE_IPO=OFF \
                         -DYmir_ENABLE_DEVLOG=OFF \
                         -DYmir_ENABLE_IMGUI_DEMO=OFF \
                         -DYmir_ENABLE_UPDATE_CHECKS=OFF"
}

make_target() {
  ninja ${NINJA_OPTS} ymir-sdl3
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp apps/ymir-sdl3/ymir-sdl3 ${INSTALL}/usr/bin/
  cp ${PKG_DIR}/scripts/ymirstart.sh ${INSTALL}/usr/bin/
}
