# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present Shanti Gilbert (https://github.com/shantigilbert)

PKG_NAME="atari800sa"
PKG_VERSION="98cc2dc749867c9c7317a0271ba062a6c797f886"
PKG_SITE="https://github.com/atari800/atari800"
PKG_URL="${PKG_SITE}/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2"
PKG_SHORTDESC="Atari 8-bit computer and 5200 console emulator"
PKG_TOOLCHAIN="configure"

pre_configure_target() {
  ${PKG_BUILD}/autogen.sh
}
