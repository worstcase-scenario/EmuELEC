# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="zlib-ng"
PKG_VERSION="12731092979c6d07f42da27da673a9f6c7b13586" # 2.3.3
PKG_LICENSE="Zlib"
PKG_SITE="https://github.com/zlib-ng/zlib-ng"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="zlib replacement with optimizations, native API (zng_*) next to the system zlib"
PKG_GIT_CLONE_BRANCH="2.3.x"
GET_HANDLER_SUPPORT="git"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DZLIB_COMPAT=OFF \
                       -DBUILD_TESTING=OFF"
