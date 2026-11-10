# SPDX-License-Identifier: GPL-2.0

PKG_NAME="md4c"
PKG_VERSION="0.4.8"
PKG_LICENSE="MIT"
PKG_SITE="https://github.com/mity/md4c"
PKG_URL="https://github.com/mity/md4c/archive/release-${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="C Markdown parser"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DBUILD_SHARED_LIBS=ON \
                       -DBUILD_MD2HTML_EXECUTABLE=OFF"
