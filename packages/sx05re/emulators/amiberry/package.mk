# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2018-present Frank Hartung (supervisedthinking (@) gmail.com)

PKG_NAME="amiberry"
PKG_VERSION="2a622d2674c4114d3600c4cda004c857d4878bdf" # v8.5.0
PKG_ARCH="aarch64 arm"
PKG_LICENSE="GPLv3"
PKG_SITE="https://github.com/BlitterStudio/amiberry"
PKG_URL="https://github.com/BlitterStudio/amiberry.git"
PKG_DEPENDS_TARGET="toolchain SDL3 SDL3_image flac mpg123-compat libpng zlib zstd curl nlohmann-json libpcap libmpeg2 libportmidi libserialport libenet"
PKG_LONGDESC="Amiberry is an optimized Amiga emulator for ARM-based boards."
GET_HANDLER_SUPPORT="git"
PKG_TOOLCHAIN="cmake"
PKG_EE_UPDATE=no

# SDL renderer instead of OpenGL; FFmpeg 4.4 is too old (needs 5.1+);
# curl-config would bake the build host's CA bundle path into the binary
PKG_CMAKE_OPTS_TARGET="-DUSE_OPENGL=OFF \
                       -DUSE_FFMPEG=OFF \
                       -DUSE_WEBP=OFF \
                       -DUSE_UAENET_PCAP=ON \
                       -DCURL_CONFIG_EXECUTABLE=/bin/false"

pre_configure_target() {
  # native file dialogs need xdg-desktop-portal, not available
  rm -rf ${PKG_BUILD}/external/nativefiledialog-extended
}

post_makeinstall_target() {
  rm -rf ${INSTALL}/usr/share/{applications,doc,icons,man,metainfo,mime}

  mkdir -p ${INSTALL}/usr/config/amiberry
  cp -a ${PKG_DIR}/config/* ${INSTALL}/usr/config/amiberry/
  ln -s /storage/roms/bios ${INSTALL}/usr/config/amiberry/kickstarts
  ln -s /tmp/joypads ${INSTALL}/usr/config/amiberry/controller

  cp -a ${PKG_DIR}/scripts/* ${INSTALL}/usr/bin

  for i in ${INSTALL}/usr/config/amiberry/conf/*.uae; do
    echo -e "gfx_center_vertical=smart\ngfx_center_horizontal=smart" >> ${i}
  done

  mkdir -p ${INSTALL}/usr/config/emuelec/configs
  ln -sf /storage/.config/amiberry ${INSTALL}/usr/config/emuelec/configs/amiberry
}
