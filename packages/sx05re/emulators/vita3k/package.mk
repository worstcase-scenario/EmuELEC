# SPDX-License-Identifier: GPL-2.0-or-later
# Vita3K PS Vita emulator - last ImGui/SDL3 frontend before the Qt6 rewrite

PKG_NAME="vita3k"
PKG_VERSION="a01f2b15b6b4149a80f531e56df351369ebc2e55"
PKG_ARCH="aarch64"
PKG_LICENSE="GPL-2.0-or-later"
PKG_SITE="https://github.com/Vita3K/Vita3K"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain boost openssl curl libdrm alsa-lib dbus vulkan-headers vulkan-loader"
PKG_LONGDESC="Vita3K PS Vita emulator (SDL3/ImGui frontend, Vulkan)"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="-DCMAKE_BUILD_TYPE=Release \
                       -DBUILD_SHARED_LIBS=OFF \
                       -DUSE_VITA3K_UPDATE=OFF \
                       -DVITA3K_FORCE_SYSTEM_BOOST=ON \
                       -DSDL_UNIX_CONSOLE_BUILD=ON"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/share/vita3k
  cp bin/Vita3K ${INSTALL}/usr/share/vita3k/
  cp -r bin/data bin/lang bin/shaders-builtin ${INSTALL}/usr/share/vita3k/
  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/vita3kstart.sh ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/vita3kstart.sh
}
