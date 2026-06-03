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

_openmsx_patch() {
  local b="$1"

  grep -rl 'static constexpr std::initializer_list' "${b}/src/" | \
    xargs sed -i 's/static constexpr std::initializer_list/static const std::initializer_list/g'

  # Patch 2: suppress SUPERIMPOSE header prepend (needed for laserdisc video)
  sed -i "s/tmpStrCat(\"#define SUPERIMPOSE \", char('0' + i), '\\\\n')/std::string()/g" \
    "${b}/src/video/scalers/GLScaler.cc"

  sed -i 's/^#define OPENGL_VERSION OPENGL_2_1$/#define OPENGL_VERSION OPENGL_ES_2_0/' \
    "${b}/src/video/GLUtil.hh"

  local g="${b}/src/video/GLUtil.cc"
  sed -i 's/source += "#ifdef GL_FRAGMENT_PRECISION_HIGH.*//g' "${g}"
  sed -i '/"  precision highp float;/d' "${g}"
  sed -i '/"#else/d' "${g}"
  sed -i '/"  precision mediump float;/d' "${g}"
  sed -i 's/"#endif.*/source += "precision highp float;\\n";/' "${g}"

  sed -i \
    's/"#ifdef GL_ES\\n"[[:space:]]*$//;s/"    precision mediump float;\\n"[[:space:]]*$//;s/"#endif\\n"[[:space:]]*$//' \
    "${b}/src/3rdparty/imgui/imgui_impl_opengl3.cc"

  sed -i 's/systemFileContext().resolve(tmpStrCat("shaders/preferSystemFileContext().resolve(tmpStrCat("shaders/g' \
    "${b}/src/video/GLUtil.cc"
}

make_target() {
  local sysroot="${SYSROOT_PREFIX}"
  local real_cxx="${CXX%% *}"
  local wname="$(basename "${real_cxx}")"
  local cxx_dir="${PKG_BUILD}/.cxx"
  local cfg_dir="${PKG_BUILD}/derived/aarch64-linux-opt/config"

  mkdir -p "${sysroot}/usr/include/GL"
  [ -f "${sysroot}/usr/include/GL/glu.h" ] || \
    printf '#ifndef __glu_h__\n#define __glu_h__\n/* GLU stub */\n#endif\n' \
      > "${sysroot}/usr/include/GL/glu.h"

  mkdir -p "${cxx_dir}"
  cat > "${cxx_dir}/${wname}" << PYWRAP
#!/usr/bin/env python3
import sys, os
sysroot = "${sysroot}"
real    = "${real_cxx}"
args = []
for a in sys.argv[1:]:
    if   a.startswith('-I/usr/'): a = '-I' + sysroot + a[2:]
    elif a.startswith('-L/usr/'): a = '-L' + sysroot + a[2:]
    args.append(a)
os.execv(real, [real] + args)
PYWRAP
  chmod +x "${cxx_dir}/${wname}"

  cat > "${PKG_BUILD}/build/probe.py" << 'NOOP'
import sys
sys.exit(0)
NOOP

  mkdir -p "${cfg_dir}"
  cat > "${cfg_dir}/systemfuncs.hh" << SYSFUNCS
#define HAVE_FTRUNCATE 1
#define HAVE_MMAP 1
SYSFUNCS

  cat > "${cfg_dir}/probed_defs.mk" << PROBEDEFS
HAVE_ALSA_H:=true
HAVE_ALSA_LIB:=true
ALSA_CFLAGS:=
ALSA_LDFLAGS:=-lasound
HAVE_FREETYPE_H:=true
HAVE_FREETYPE_LIB:=true
FREETYPE_CFLAGS:=-I${sysroot}/usr/include/freetype2 -I${sysroot}/usr/include
FREETYPE_LDFLAGS:=-L${sysroot}/usr/lib -lfreetype
HAVE_GL_H:=true
HAVE_GL_LIB:=true
GL_CFLAGS:=
GL_LDFLAGS:=-lGL
HAVE_GLEW_H:=true
HAVE_GLEW_LIB:=true
GLEW_CFLAGS:=
GLEW_LDFLAGS:=-lGLEW -lGL
HAVE_OGG_H:=true
HAVE_OGG_LIB:=true
OGG_CFLAGS:=
OGG_LDFLAGS:=-logg
HAVE_PNG_H:=true
HAVE_PNG_LIB:=true
PNG_CFLAGS:=-I${sysroot}/usr/include/libpng16
PNG_LDFLAGS:=-lpng16
HAVE_SDL2_H:=true
HAVE_SDL2_LIB:=true
SDL2_CFLAGS:=-I${sysroot}/usr/include/SDL2 -D_REENTRANT
SDL2_LDFLAGS:=-lSDL2
HAVE_SDL2_TTF_H:=true
HAVE_SDL2_TTF_LIB:=true
SDL2_TTF_CFLAGS:=-I${sysroot}/usr/include/SDL2
SDL2_TTF_LDFLAGS:=-lSDL2_ttf
HAVE_TCL_H:=true
HAVE_TCL_LIB:=true
TCL_CFLAGS:=
TCL_LDFLAGS:=-ltcl8.6
HAVE_THEORA_H:=true
HAVE_THEORA_LIB:=true
THEORA_CFLAGS:=
THEORA_LDFLAGS:=-ltheoradec
HAVE_VORBIS_H:=true
HAVE_VORBIS_LIB:=true
VORBIS_CFLAGS:=
VORBIS_LDFLAGS:=-lvorbis
HAVE_ZLIB_H:=true
HAVE_ZLIB_LIB:=true
ZLIB_CFLAGS:=
ZLIB_LDFLAGS:=-lz
HAVE_FTRUNCATE:=true
HAVE_MMAP:=true
PROBEDEFS

  _openmsx_patch "${PKG_BUILD}"

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
  python3 - "${INSTALL}/usr/share/shaders_laserdisc" << 'PYSHADER_LD'
import sys, os, re
sdir = sys.argv[1]
for fn in os.listdir(sdir):
    if not (fn.endswith('.frag') or fn.endswith('.vert')): continue
    fpath = os.path.join(sdir, fn)
    src = open(fpath).read()
    if '#if' not in src: continue
    src = re.sub(r'#if SUPERIMPOSE[^\n]*\n(.*?)(?:#else[^\n]*\n(.*?))?#endif[^\n]*\n',
        lambda m: (m.group(1) or '').strip()+'\n', src, flags=re.DOTALL)
    src = re.sub(r'#define SUPERIMPOSE [01]\n', '', src)
    open(fpath, 'w').write(src)
    print('Resolved LD:', fn)
PYSHADER_LD

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

