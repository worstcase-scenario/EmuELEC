# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present EmuELEC
# Tsugaru standalone FM Towns emulator (Tsugaru_CUI) with SDL2 backend.

PKG_NAME="tsugaru"
PKG_VERSION="0e31cb4065fd5b7888cb6c13d19f358925f9366e"
PKG_SHA256="7622a544c2d052a2e159c10e31eca46dd8e15cfdc5ebe29c65cd2b948ab3c5d2"
PKG_LICENSE="BSD-3-Clause"
PKG_SITE="https://github.com/captainys/TOWNSEMU"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"

PKG_DEPENDS_TARGET="toolchain SDL2 alsa-lib"
PKG_LONGDESC="Tsugaru FM Towns emulator (standalone CUI with SDL2 display)"
PKG_TOOLCHAIN="manual"

# Replace fssimplewindow (GLX/X11) with SDL2 backend.
# SDL2Connection implements Outside_World using SDL2 for video/input and SDL2
# audio for CDDA/FMPCM/Beep. Drops X11, OpenGL, GLU dependencies entirely.

pre_configure_target() {
  # Copy SDL2 backend and i486 patch script into the source tree
  cp "${PKG_DIR}/files/sdl2_connection.h" \
     "${PKG_BUILD}/src/externals/connect_fssimplewindow/sdl2_connection.h"
  cp "${PKG_DIR}/files/sdl2_connection.cpp" \
     "${PKG_BUILD}/src/externals/connect_fssimplewindow/sdl2_connection.cpp"
  cp "${PKG_DIR}/files/patch_i486.py" /tmp/tsugaru_patch_i486.py

  # Patch main_cui/main.cpp: replace FsSimpleWindowConnection with SDL2Connection
  sed -i 's|#include "fssimplewindow_connection.h"|#include "sdl2_connection.h"|g' \
    "${PKG_BUILD}/src/main_cui/main.cpp"
  sed -i 's|new FsSimpleWindowConnection|new SDL2Connection|g' \
    "${PKG_BUILD}/src/main_cui/main.cpp"

  # Patch connect_fssimplewindow CMakeLists to build our SDL2 file instead
  # and remove GLX/X11/GL dependencies
  cat > "${PKG_BUILD}/src/externals/connect_fssimplewindow/CMakeLists.txt" << 'EOF'
set(TARGET_NAME fssimplewindow_connection)

find_package(SDL2 REQUIRED)

# Only compile sdl2_connection.cpp — not fssimplewindow_connection.cpp (needs GLX).
# Define FSSIMPLEWINDOW_DONT_INCLUDE_OPENGL_HEADERS to prevent GL header inclusion
# if fssimplewindow.h is transitively included.
add_library(${TARGET_NAME}
    sdl2_connection.h
    sdl2_connection.cpp
)
target_compile_definitions(${TARGET_NAME} PUBLIC
    FSSIMPLEWINDOW_DONT_INCLUDE_OPENGL_HEADERS
)
target_include_directories(${TARGET_NAME} PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${SDL2_INCLUDE_DIRS}
)
target_link_libraries(${TARGET_NAME}
    outside_world
    ${SDL2_LIBRARIES}
    pthread
)
EOF

  # Patch fssimplewindow CMakeLists to use nownd (no X11/GL needed)
  cat > "${PKG_BUILD}/src/externals/fssimplewindow/src/CMakeLists.txt" << 'EOF'
set(TARGET_NAME fssimplewindow)
add_library(${TARGET_NAME}
    fssimplewindowcommon.cpp
    nownd/fssimplenowindow.cpp
)
target_include_directories(${TARGET_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
# No GL/GLU/X11 dependencies for the nownd backend
EOF

  # Stub out ysgamepad (gamepad support via SDL2 is in sdl2_connection.cpp)
  # fssimplewindow_connection.h references YsGamePadReading — provide a minimal stub
  cat > "${PKG_BUILD}/src/externals/connect_fssimplewindow/ysgamepad_stub.h" << 'EOF'
#pragma once
struct YsGamePadReading {
    float axis[4] = {};
    unsigned int button = 0;
};
EOF

  # Restore externals/CMakeLists.txt with yssimplesound — TownsSound uses
  # YsSoundPlayer::SoundData directly for internal audio processing and WAV I/O.
  # Our SDL2Connection replaces only the playback API, not the data layer.
  cat > "${PKG_BUILD}/src/externals/CMakeLists.txt" << 'EOF'
add_subdirectory(connect_fssimplewindow)
add_subdirectory(fssimplewindow/src)
add_subdirectory(yssimplesound/src)
add_subdirectory(d77)
add_subdirectory(yspng)
add_subdirectory(yssocket/src)
EOF

  # CRTC ShowPage bug: port 0xFDA0 is HSYNC/VSYNC timing control but Tsugaru
  # also uses some of its bits as showPageFDA0. The FreeTOWNS BIOS writes 0x00
  # to 0xFDA0 for HSYNC setup, which sets showPageFDA0=false → black screen.
  # Fix: use only showPage0448 (the proper FM Towns page enable register).
  sed -i 's/return (showPageFDA0\[page\] && showPage0448\[page\]);/return showPage0448[page];/' \
    "${PKG_BUILD}/src/towns/crtc/crtc.h"

  # DEFAULT_FIDELITY aborts when clocksPassed==0 (unimplemented opcode timing).
  # This kills the BIOS at FFFE07D5 opcode 0xD0 before video init.
  # HIGHFIDELITY handles 0xD0 but gets stuck at FFFE2397 (different bug).
  # Fix: use a default of 4 clocks instead of aborting, so DEFAULT_FIDELITY
  # can boot the FreeTOWNS BIOS without hitting the HIGHFIDELITY deadlock.
  python3 /tmp/tsugaru_patch_i486.py "${PKG_BUILD}"
  # The shell then interprets the semicolon as a command separator, causing
  # "no input files" errors. Patch the top-level CMakeLists.txt to collapse
  # semicolons to spaces before any targets are defined.
  sed -i '1 a\
foreach(lang C CXX)\
  string(REPLACE ";" " " CMAKE_${lang}_FLAGS "${CMAKE_${lang}_FLAGS}")\
  set(CMAKE_${lang}_FLAGS "${CMAKE_${lang}_FLAGS}" CACHE STRING "" FORCE)\
endforeach()' "${PKG_BUILD}/src/CMakeLists.txt"

  # Run cmake from the src/ subdirectory where CMakeLists.txt lives
  mkdir -p "${PKG_BUILD}/.cmake-build"
  cmake -GNinja \
    -DCMAKE_TOOLCHAIN_FILE="${CMAKE_CONF}" \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=17 \
    -DYS_LITTLE_ENDIAN=1 \
    -DYS_TWOS_COMPLEMENT=1 \
    -B "${PKG_BUILD}/.cmake-build" \
    -S "${PKG_BUILD}/src"
}

make_target() {
  ninja -C "${PKG_BUILD}/.cmake-build" -j$(nproc) Tsugaru_CUI
}

makeinstall_target() {
  mkdir -p "${INSTALL}/emuelec/bin"
  cp -f "${PKG_BUILD}/.cmake-build/main_cui/Tsugaru_CUI" "${INSTALL}/emuelec/bin/tsugaru"
  chmod +x "${INSTALL}/emuelec/bin/tsugaru"
}