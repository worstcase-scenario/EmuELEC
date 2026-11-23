# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="SDL3"
PKG_VERSION="3.4.20"
PKG_SHA256="f3bb06f55bed9557227a700af2ea62e49497ebdf58037732a731a5fb3ef8581f"
PKG_LICENSE="Zlib"
PKG_SITE="https://www.libsdl.org/"
PKG_URL="https://github.com/libsdl-org/SDL/releases/download/release-${PKG_VERSION}/SDL3-${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain alsa-lib systemd dbus pulseaudio libdrm ${OPENGLES} vulkan-headers vulkan-loader"
PKG_LONGDESC="Simple DirectMedia Layer 3, installed side by side with SDL2 (KMSDRM, GLES, Vulkan)"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DSDL_STATIC=OFF \
                       -DSDL_TEST_LIBRARY=OFF \
                       -DSDL_TESTS=OFF \
                       -DSDL_EXAMPLES=OFF \
                       -DSDL_UNIX_CONSOLE_BUILD=ON \
                       -DSDL_X11=OFF \
                       -DSDL_WAYLAND=OFF \
                       -DSDL_KMSDRM=ON \
                       -DSDL_OPENGL=OFF \
                       -DSDL_OPENGLES=ON \
                       -DSDL_VULKAN=ON \
                       -DSDL_ALSA=ON \
                       -DSDL_PULSEAUDIO=ON \
                       -DSDL_PIPEWIRE=OFF \
                       -DSDL_JACK=OFF \
                       -DSDL_SNDIO=OFF \
                       -DSDL_IBUS=OFF \
                       -DSDL_RPATH=OFF"
