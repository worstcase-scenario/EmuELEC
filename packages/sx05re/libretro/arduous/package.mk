# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="arduous"
PKG_VERSION="main"
PKG_SHA256="5c9ecda60735aab6d3e26ed78f1fc266cb0f45635ecf7ff1a3bd29aeddf9db63"

PKG_ARCH="any"
PKG_LICENSE="GPLv3"
PKG_SITE="https://github.com/libretro/arduous"
PKG_URL="https://github.com/libretro/arduous/archive/${PKG_VERSION}.tar.gz"

PKG_DEPENDS_TARGET="toolchain"
PKG_SECTION="emuelec/libretro"
PKG_SHORTDESC="Arduous libretro core (Arduboy)"
PKG_LONGDESC="Arduous is a libretro core for the Arduboy handheld game console."

PKG_TOOLCHAIN="manual"

configure_target() {
  cd "${PKG_BUILD}"


  if [ ! -f "simavr/simavr/sim/avr_acomp.c" ]; then
    rm -rf simavr
    mkdir -p simavr

    echo "Arduous: fetching simavr source ..."
    if command -v curl >/dev/null 2>&1; then
      curl -L -o simavr.tar.gz \
        "https://github.com/buserror/simavr/archive/refs/heads/master.tar.gz"
    else
      wget -O simavr.tar.gz \
        "https://github.com/buserror/simavr/archive/refs/heads/master.tar.gz"
    fi

    tar -xf simavr.tar.gz --strip-components=1 -C simavr
    rm -f simavr.tar.gz
  fi


  if ! grep -q "ihex_chunk_s" src/arduous/arduous.cpp; then
    sed -i '1i\
typedef struct ihex_chunk_s {\
    unsigned long baseaddr;\
    unsigned int size;\
    unsigned char *data;\
} ihex_chunk_t;\
\
typedef ihex_chunk_t* ihex_chunk_p;\
\
static inline void free_ihex_chunks(ihex_chunk_p chunks) {\
    (void)chunks;\
}\
' src/arduous/arduous.cpp
  fi

  mkdir -p build
  cd build

  cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DLIBRETRO=ON \
    -DCMAKE_C_COMPILER="${CC}" \
    -DCMAKE_CXX_COMPILER="${CXX}"
}

make_target() {
  cd "${PKG_BUILD}/build"
  make
}

makeinstall_target() {
  mkdir -p "${INSTALL}/usr/lib/libretro"
  cp "${PKG_BUILD}/build/arduous_libretro.so" \
     "${INSTALL}/usr/lib/libretro/"
}
