# SPDX-License-Identifier: GPL-2.0

PKG_NAME="ffmpeg-steamlink"
PKG_VERSION="5.1.6"
PKG_LICENSE="LGPLv2.1+"
PKG_SITE="https://ffmpeg.org"
PKG_URL="https://ffmpeg.org/releases/ffmpeg-${PKG_VERSION}.tar.xz"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="Minimal FFmpeg 5.1 (H.264/HEVC/Opus decoders) for Steam Link, installed to /usr/lib/steamlink"
PKG_TOOLCHAIN="manual"

configure_target() {
  cd ${PKG_BUILD}
  ./configure --prefix=/usr \
              --enable-cross-compile \
              --cross-prefix=${TARGET_PREFIX} \
              --sysroot=${SYSROOT_PREFIX} \
              --arch=aarch64 \
              --target-os=linux \
              --cc="${CC}" \
              --enable-pic \
              --enable-shared \
              --disable-static \
              --disable-debug \
              --disable-doc \
              --disable-programs \
              --disable-autodetect \
              --disable-network \
              --disable-avdevice \
              --disable-avformat \
              --disable-avfilter \
              --disable-swscale \
              --disable-postproc \
              --disable-everything \
              --enable-decoder=h264,hevc,opus \
              --enable-parser=h264,hevc,opus
}

make_target() {
  cd ${PKG_BUILD}
  make
}

makeinstall_target() {
  cd ${PKG_BUILD}
  mkdir -p ${INSTALL}/usr/lib/steamlink
  cp -P libavcodec/libavcodec.so.59* libavutil/libavutil.so.57* libswresample/libswresample.so.4* \
        ${INSTALL}/usr/lib/steamlink/
}
