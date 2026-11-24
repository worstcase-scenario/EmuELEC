# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="SDL3_image"
PKG_VERSION="3.4.8"
PKG_SHA256="e8223b424bc7541cf84ffff5cf7e4f24ec3711c60462cb1bd6dc1d7bd7f25477"
PKG_LICENSE="Zlib"
PKG_SITE="https://github.com/libsdl-org/SDL_image"
PKG_URL="${PKG_SITE}/releases/download/release-${PKG_VERSION}/SDL3_image-${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL3"
PKG_LONGDESC="Image loading library for SDL3 (built-in stb decoders, no external image libraries)"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DSDLIMAGE_VENDORED=OFF \
                       -DSDLIMAGE_SAMPLES=OFF \
                       -DSDLIMAGE_TESTS=OFF \
                       -DSDLIMAGE_BACKEND_STB=ON \
                       -DSDLIMAGE_PNG_LIBPNG=OFF \
                       -DSDLIMAGE_AVIF=OFF \
                       -DSDLIMAGE_JXL=OFF \
                       -DSDLIMAGE_TIF=OFF \
                       -DSDLIMAGE_WEBP=OFF \
                       -DSDLIMAGE_STRICT=ON"
