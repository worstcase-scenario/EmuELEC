PKG_NAME="supermodel"
#new_PKG_VERSION="24d2ffcfc7f14229337f05f4920fe26b56633d9d"
PKG_VERSION="121f81c7429b18d5085ce2d3b2a7b9e045c39c72"
PKG_SHA256="b57a4d280c7dcafc6610df933b897968f3f07ce20c3c971565812dbfca54bbcc"
#new_PKG_SHA256="027c544e0eb223831c3a702fe326f7ac7c9b120c036133f05b52ccf3ca0feb95"
#PKG_SHA256="121f81c7429b18d5085ce2d3b2a7b9e045c39c72"
PKG_LICENSE="GPLv3"
PKG_SITE="https://github.com/trzy/Supermodel"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_net zlib gl4es"
PKG_SECTION="emuelec"
PKG_SHORTDESC="Supermodel: A Sega Model 3 Arcade Emulator"
PKG_LONGDESC="Supermodel emulates Sega Model 3 arcade platform."
PKG_TOOLCHAIN="manual"

pre_make_target() {
  # m68kmake is a build-time code generator: it must run on the build machine.
  # Build and run it with the host compiler so make skips its own cross-built rule.
  mkdir -p obj
  ${HOST_CC} -O2 Src/CPU/68K/Musashi/m68kmake.c -o obj/m68kmake.exe
  ./obj/m68kmake.exe obj Src/CPU/68K/Musashi/m68k_in.c
}

make_target() {
  local SDL_CFLAGS SDL_LIBS
  SDL_CFLAGS="$(${PKG_CONFIG} --cflags sdl2)"
  SDL_LIBS="$(${PKG_CONFIG} --libs sdl2) -lSDL2_net"

  make -f Makefiles/Makefile.UNIX \
    CC="${CC}" \
    CXX="${CXX}" \
    LD="${CXX}" \
    SUPERMODEL_BUILD_FLAGS="-DGLEW_NO_GLU" \
    PLATFORM_CXXFLAGS="${SDL_CFLAGS} -O3" \
    PLATFORM_LDFLAGS="${SDL_LIBS} -lGL -lz -lm -lstdc++ -lpthread"
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp bin/supermodel ${INSTALL}/usr/bin/supermodel
  cp ${PKG_DIR}/scripts/supermodelstart.sh ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/supermodelstart.sh

  mkdir -p ${INSTALL}/usr/config/supermodel/Config
  cp -r Config/. ${INSTALL}/usr/config/supermodel/Config/

}