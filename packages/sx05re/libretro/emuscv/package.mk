# SPDX-License-Identifier: GPL-3.0-or-later

# EmuELEC package for EmuSCV (Super Cassette Vision) libretro core

PKG_NAME="emuscv"
PKG_VERSION="master"
PKG_SHA256="ee222ae388d4e8016a8abbb10016ca2c6d93eed5a82612f4ec0fa6b1b952edee"
PKG_LICENSE="GPLv3"
PKG_SITE="https://gitlab.com/MaaaX-EmuSCV/libretro-emuscv"
PKG_URL="${PKG_SITE}/-/archive/${PKG_VERSION}/libretro-emuscv-${PKG_VERSION}.tar.gz"
PKG_SOURCE_DIR="libretro-emuscv-${PKG_VERSION}"

PKG_ARCH="any"
PKG_SECTION="emuelec/libretro"
PKG_DEPENDS_TARGET="toolchain zlib"
PKG_SHORTDESC="EmuSCV Super Cassette Vision libretro core"
PKG_LONGDESC="EmuSCV is an EPOCH/YENO Super Cassette Vision emulator implemented as a libretro core."
PKG_TOOLCHAIN="make"

PKG_IS_CORE="yes"

pre_make_target() {
  cd "${PKG_BUILD}"

  if [ -f Makefile.libretro ]; then
    sed -i 's|-I/usr/include/SDL2||g' Makefile.libretro || true
  fi

  mkdir -p .cross-bin

  cat > .cross-bin/sdl2-config << 'EOF'

SYSROOT="${SYSROOT_PREFIX:-/usr}"

case "$1" in
  --cflags)
    echo "-I${SYSROOT}/usr/include/SDL2"
    ;;
  --libs)
    echo "-L${SYSROOT}/usr/lib -lSDL2"
    ;;
  *)
    exit 0
    ;;
esac
EOF

  chmod +x .cross-bin/sdl2-config

  if [ -f src/common.h ]; then
    sed -i 's@#include <sys/io.h>@// #include <sys/io.h>@' src/common.h || true
  fi

  if [ -f src/vm/debugger.cpp ]; then
    sed -i 's@#include <sys/io.h>@// #include <sys/io.h>@' src/vm/debugger.cpp || true
  fi
}

make_target() {
  cd "${PKG_BUILD}"

  export PATH="${PKG_BUILD}/.cross-bin:${PATH}"

  case "${TARGET_ARCH}" in
    aarch64|arm)
      PLATFORM="unix"
      ;;
    *)
      PLATFORM="unix"
      ;;
  esac

  make -C "${PKG_BUILD}" \
       -f Makefile.libretro \
       CC="${CC}" \
       CXX="${CXX}" \
       AR="${AR}" \
       platform="${PLATFORM}"
}

makeinstall_target() {
  mkdir -p "${INSTALL}/usr/lib/libretro"
  cp "${PKG_BUILD}/emuscv_libretro.so" \
     "${INSTALL}/usr/lib/libretro/"
}
