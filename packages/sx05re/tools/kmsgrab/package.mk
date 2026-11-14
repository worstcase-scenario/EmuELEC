# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="kmsgrab"
PKG_VERSION="d4c6061a59f4b7ecb6b39f96c7d39a5d5f48b702"
PKG_SHA256="6531ddd6672fdd0a559cf9a12b9063ad241a5a64a2765b16dddb185c5e89c146"
PKG_LICENSE="GPL-2.0"
PKG_SITE="https://github.com/pcercuei/kmsgrab"
PKG_URL="https://github.com/pcercuei/kmsgrab/archive/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain libdrm libpng"
PKG_LONGDESC="Simple screenshot tool for DRM/KMS drivers (dumps a plane's framebuffer directly, no VAAPI required)."
PKG_TOOLCHAIN="cmake"

pre_configure_target() {
  # dma-buf fds can only be mmap'd MAP_SHARED; upstream uses MAP_PRIVATE,
  # which the kernel dma-buf exporter rejects with EINVAL on this driver.
  sed -i 's/MAP_PRIVATE/MAP_SHARED/' ${PKG_BUILD}/kmsgrab.c
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_BUILD}/.${TARGET_NAME}/kmsgrab ${INSTALL}/usr/bin
}
