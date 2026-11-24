# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="malisx2"
PKG_VERSION="0.6.1"
PKG_ARCH="aarch64"
PKG_LICENSE="MIT"
PKG_SITE="https://github.com/bmdhacks/malisx2"
PKG_URL="${PKG_SITE}/releases/download/v${PKG_VERSION}/malisx2-${PKG_VERSION}-aarch64.tar.gz"
PKG_SOURCE_DIR="malisx2"
PKG_DEPENDS_TARGET="toolchain libdrm"
PKG_LONGDESC="Mesa panvk Vulkan driver for Mali on kbase (optional, per emulator)"
PKG_TOOLCHAIN="manual"

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/lib/malisx2
  cp ${PKG_BUILD}/${PKG_VERSION}/libvulkan_malisx2.so ${INSTALL}/usr/lib/malisx2/
  sed 's|"library_path": *"[^"]*"|"library_path": "/usr/lib/malisx2/libvulkan_malisx2.so"|' \
    ${PKG_BUILD}/${PKG_VERSION}/malisx2_icd.aarch64.json > ${INSTALL}/usr/lib/malisx2/malisx2_icd.aarch64.json
}