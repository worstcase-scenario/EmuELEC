# SPDX-License-Identifier: GPL-2.0

PKG_NAME="double-conversion"
PKG_VERSION="3.3.0"
PKG_LICENSE="BSD"
PKG_SITE="https://github.com/google/double-conversion"
PKG_URL="https://github.com/google/double-conversion/archive/v${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="Efficient binary-decimal and decimal-binary conversion routines for IEEE doubles"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DBUILD_SHARED_LIBS=ON \
                       -DBUILD_TESTING=OFF"
