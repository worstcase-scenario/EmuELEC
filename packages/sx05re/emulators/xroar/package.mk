# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="xroar"
PKG_VERSION="xroar-1.8.2"
PKG_SHA256="d3f69bc475c66786f131ec95e264e154518d283439ffd82f31d74159cdca0b11"

PKG_ARCH="any"
PKG_LICENSE="GPL-3.0-or-later"
PKG_SITE="https://github.com/RetroDECK/XRoar"
PKG_URL="https://github.com/RetroDECK/XRoar/archive/refs/tags/${PKG_VERSION}.tar.gz"

# XRoar can use SDL2_image for screenshots/PNG handling and may detect libevdev for input.
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_image libpng zlib alsa-lib pulseaudio libevdev"

PKG_SECTION="emuelec/emulators"
PKG_SHORTDESC="XRoar - Dragon 32/64 & Tandy CoCo Emulator"
PKG_LONGDESC="XRoar emulates Dragon 32/64, Tandy Colour Computers 1/2/3, the MC-10 and related machines."

configure_target() {
  cd "$PKG_BUILD"

  # EmuELEC is not an X11 system.
  # During cross-compiles, configure may incorrectly detect X11 from the build host,
  # which makes it compile sdl2/sdl_x11.c and then fail because SDL2 was built without X11 support.
  
  export ac_cv_have_x=no
  export ac_cv_header_X11_Xlib_h=no
  export ac_cv_lib_X11_XOpenDisplay=no

  # Optional: if the configure script hard-fails when no OpenGL implementation is found,
  # neutralize that error for EmuELEC builds.
  if [ -f "./configure" ] && grep -q "Could not find a valid OpenGL implementation" ./configure; then
    sed -i '/Could not find a valid OpenGL implementation/ s/as_fn_error[^;]*/: # OpenGL disabled for EmuELEC/' ./configure
  fi

  ./configure \
    $TARGET_CONFIGURE_OPTS \
    --prefix=/usr \
    --enable-dragon \
    --enable-coco3 \
    --enable-mc10 \
    --without-gtk2 \
    --without-gtk3 \
    --without-gtkgl \
    --without-cocoa
}

make_target() {
  cd "$PKG_BUILD"
  make
}

makeinstall_target() {
  install -Dm755 "${PKG_BUILD}/src/xroar" "${INSTALL}/usr/bin/xroar"
}
