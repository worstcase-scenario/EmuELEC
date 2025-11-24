# SPDX-License-Identifier: GPL-2.0
# EmuELEC / LibreELEC style package for libretro FreeChaF core

PKG_NAME="freechaf"
PKG_VERSION="cdb8ad6fcecb276761b193650f5ce9ae8b878067"
PKG_SHA256="4e8be1cb01f974e2bc34e87d80a8c75cf6345a7542a11d61fb1150e0421dda1d"
PKG_ARCH="any"
PKG_LICENSE="GPLv3"
PKG_SITE="https://github.com/libretro/FreeChaF"
PKG_URL="$PKG_SITE/archive/$PKG_VERSION.tar.gz"

PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/libretro"
PKG_SHORTDESC="FreeChaF libretro core (Fairchild Channel F)"
PKG_LONGDESC="FreeChaF is a libretro emulation core for the Fairchild Channel F / Video Entertainment System."

PKG_TOOLCHAIN="make"

pre_configure_target() {
  cd "$PKG_BUILD"


  if [ ! -d "src/deps/libretro-common" ] || [ ! -f "src/deps/libretro-common/include/libretro.h" ]; then
    echo "freechaf: fetching libretro-common sources..."
    rm -rf src/deps/libretro-common
    mkdir -p src/deps/libretro-common


    LIBRETRO_COMMON_TAR="https://github.com/libretro/libretro-common/archive/refs/heads/master.tar.gz"


    if ! wget -O libretro-common.tar.gz "$LIBRETRO_COMMON_TAR"; then
      curl -L -o libretro-common.tar.gz "$LIBRETRO_COMMON_TAR"
    fi

    tar -xzf libretro-common.tar.gz --strip-components=1 -C src/deps/libretro-common
    rm -f libretro-common.tar.gz
  fi
}

make_target() {
  cd "$PKG_BUILD"


  EXTRA_CFLAGS="-Isrc/deps/libretro-common/include -Isrc/deps/libretro-common"

  make \
    CC="$CC" \
    CFLAGS="$CFLAGS $EXTRA_CFLAGS" \
    LDFLAGS="$LDFLAGS" \
    platform="${LIBRETRO_PLATFORM:-unix}"
}


makeinstall_target() {
  mkdir -p "$INSTALL/usr/lib/libretro"
  cp "$PKG_BUILD/freechaf_libretro.so" "$INSTALL/usr/lib/libretro/"
}
