# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC/EmuELEC)

PKG_NAME="lightspark"
PKG_VERSION="53eac9d5d4066568c97dac1a03be95c2e144478a"
PKG_ARCH="aarch64"
PKG_LICENSE="LGPL"
PKG_SITE="https://github.com/lightspark/lightspark"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain SDL2 ffmpeg glew cairo pango curl zlib libjpeg-turbo \
                    fontconfig pcre2 xz rtmpdump SDL2_mixer"
PKG_LONGDESC="Lightspark - Open Source Flash Player (SWF standalone)"
PKG_TOOLCHAIN="cmake"

# Patches (applied automatically by the build system after unpack):
#   lightspark-0001-softcursor-swapbuffers-hook.patch - creates softcursor.h
#     and hooks it into DoSwapBuffers
#   lightspark-0002-packed-depth-stencil-static.patch - fixes upstream GLES
#     build error: non-static member assigned in static createSDLGLContext;
#     also guards the desktop-only GL_EXT extension check in InitOpenGL

PKG_CMAKE_OPTS_TARGET="
  -DCMAKE_BUILD_TYPE=Release
  -DCOMPILE_LIGHTSPARK=ON
  -DCOMPILE_TIGHTSPARK=OFF
  -DCOMPILE_NPAPI_PLUGIN=OFF
  -DCOMPILE_PPAPI_PLUGIN=OFF
  -DENABLE_GLES2=ON
  -DENABLE_LLVM=OFF
  -DENABLE_TEST_RUNNER=OFF
  -DENABLE_MEMORY_USAGE_PROFILING=OFF
  -DOPENGL_INCLUDE_DIR=${SYSROOT_PREFIX}/usr/include
  -DCMAKE_INSTALL_PREFIX=/usr
"

makeinstall_target() {
  local RELEASE_DIR="${PKG_BUILD}/.${TARGET_NAME}/aarch64/Release"

  mkdir -p ${INSTALL}/usr/bin
  cp -v "${RELEASE_DIR}/bin/lightspark" ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/lightspark

  mkdir -p ${INSTALL}/usr/lib
  cp -av "${RELEASE_DIR}/lib/." ${INSTALL}/usr/lib/

  cp -v ${PKG_DIR}/scripts/lightsparkstart.sh ${INSTALL}/usr/bin/lightsparkstart.sh
  chmod +x ${INSTALL}/usr/bin/lightsparkstart.sh

  if [ -f "${PKG_DIR}/config/lightspark.gptk" ]; then
    mkdir -p ${INSTALL}/usr/config/emuelec/configs/lightspark/gptk
    cp -f "${PKG_DIR}/config/lightspark.gptk" \
      "${INSTALL}/usr/config/emuelec/configs/lightspark/gptk/lightspark.gptk"
  fi
}