# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

PKG_NAME="openmsx-ld"
PKG_VERSION="RELEASE_21_0"
PKG_REV="0"
PKG_ARCH="any"
PKG_LICENSE="GPL"
PKG_SITE="https://github.com/openMSX/openMSX"
PKG_URL="${PKG_SITE}/archive/refs/tags/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_ttf libpng zlib tcl alsa-lib glew"
PKG_SHORTDESC="openMSX Laserdisc: Pioneer PX-7 emulation for Palcom LaserDisc games"
PKG_TOOLCHAIN="manual"

# All source modifications live in patches/ and are applied automatically
# by the build system after unpack:
#   openmsx-ld-0001-initializer-list-non-constexpr.patch
#   openmsx-ld-0002-gles2-mali.patch
#   openmsx-ld-0003-suppress-superimpose-define.patch
# Host-side build helpers live in buildtools/; scripts/ and config/ keep
# their existing meaning (device launcher scripts and gptk configs).

make_target() {
  local sysroot="${SYSROOT_PREFIX}"
  local real_cxx="${CXX%% *}"
  local wname="$(basename "${real_cxx}")"
  local cxx_dir="${PKG_BUILD}/.cxx"
  local cfg_dir="${PKG_BUILD}/derived/aarch64-linux-opt/config"

  # GLU stub header (openMSX probes for it, Mali sysroot has none)
  mkdir -p "${sysroot}/usr/include/GL"
  [ -f "${sysroot}/usr/include/GL/glu.h" ] || \
    cp "${PKG_DIR}/buildtools/glu.h" "${sysroot}/usr/include/GL/glu.h"

  # CXX wrapper: rewrites -I/usr/ and -L/usr/ into the sysroot,
  # configured via environment (see scripts/cxx-wrapper.py)
  mkdir -p "${cxx_dir}"
  install -m 0755 "${PKG_DIR}/buildtools/cxx-wrapper.py" "${cxx_dir}/${wname}"
  export OPENMSX_SYSROOT="${sysroot}"
  export OPENMSX_REAL_CXX="${real_cxx}"

  # Disable openMSX's host-probing, provide pre-probed results instead
  mkdir -p "${PKG_BUILD}/build" "${cfg_dir}"
  cp "${PKG_DIR}/buildtools/probe-noop.py" "${PKG_BUILD}/build/probe.py"
  cp "${PKG_DIR}/buildtools/systemfuncs.hh" "${cfg_dir}/systemfuncs.hh"
  sed "s|@SYSROOT@|${sysroot}|g" "${PKG_DIR}/buildtools/probed_defs.mk.in" \
    > "${cfg_dir}/probed_defs.mk"

  make -C ${PKG_BUILD} \
    OPENMSX_TARGET_CPU=${TARGET_ARCH} \
    OPENMSX_TARGET_OS=linux \
    CXX="${cxx_dir}/${wname}" \
    CXXFLAGS="${TARGET_CFLAGS}" \
    INSTALL_BASE=/usr \
    V=1
}

makeinstall_target() {
  local sysroot="${SYSROOT_PREFIX}"
  local real_cxx="${CXX%% *}"
  local wname="$(basename "${real_cxx}")"
  local cxx_dir="${PKG_BUILD}/.cxx"

  export OPENMSX_SYSROOT="${sysroot}"
  export OPENMSX_REAL_CXX="${real_cxx}"

  # Install data files via make install, then replace binary with openmsx-ld
  make -C ${PKG_BUILD} \
    OPENMSX_TARGET_CPU=${TARGET_ARCH} \
    OPENMSX_TARGET_OS=linux \
    CXX="${cxx_dir}/${wname}" \
    INSTALL_BASE=/usr \
    DESTDIR=${INSTALL} \
    install

  # Rename binary to openmsx-ld
  mv ${INSTALL}/usr/bin/openmsx ${INSTALL}/usr/bin/openmsx-ld

  # Generate SUPERIMPOSE=1 shaders for laserdisc video
  mkdir -p ${INSTALL}/usr/share/shaders_laserdisc
  cp ${INSTALL}/usr/share/shaders/*.frag ${INSTALL}/usr/share/shaders_laserdisc/ 2>/dev/null || true
  cp ${INSTALL}/usr/share/shaders/*.vert ${INSTALL}/usr/share/shaders_laserdisc/ 2>/dev/null || true
  python3 "${PKG_DIR}/buildtools/resolve_superimpose.py" \
    "${INSTALL}/usr/share/shaders_laserdisc" 1

  # Remove regular shaders - not needed, only shaders_laserdisc matters
  rm -rf ${INSTALL}/usr/share/shaders

  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/startopenmsx-ld.sh ${INSTALL}/usr/bin/startopenmsx-ld.sh
  chmod +x ${INSTALL}/usr/bin/startopenmsx-ld.sh

  mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk
  cp ${PKG_DIR}/config/openmsx-ld.gptk \
    ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk/openmsx-ld.gptk

  mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/libs
  for lib in libGLX.so.0 libGLdispatch.so.0; do
    if [ -f "${sysroot}/usr/lib/${lib}" ]; then
      cp "${sysroot}/usr/lib/${lib}" \
        "${INSTALL}/usr/config/emuelec/configs/openmsx/libs/${lib}"
    fi
  done
}
