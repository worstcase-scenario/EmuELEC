# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2020-present Shanti Gilbert (https://github.com/shantigilbert)

PKG_NAME="dolphinSA"
PKG_VERSION="048e6306b82b183d061ee33c4ee32d5e76f3f09a"
PKG_ARCH="aarch64"
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/dolphin-emu/dolphin"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain systemd libevdev alsa-lib"
PKG_LONGDESC="Dolphin is a GameCube / Wii emulator, allowing you to play games for these two platforms on PC with improvements. "
PKG_BUILD_FLAGS="-lto"

# Configure CMake with BFD linker (LTO off)
PKG_CMAKE_OPTS_TARGET=" -DENABLE_LTO=OFF \
                        -DCMAKE_EXE_LINKER_FLAGS='-fuse-ld=bfd' \
                        -DCMAKE_SHARED_LINKER_FLAGS='-fuse-ld=bfd' \
                        -DDISTRIBUTOR='EmuELEC' \
                        -DBUILD_SHARED_LIBS=OFF \
                        -DTHREADS_PTHREAD_ARG=OFF \
                        -DENABLE_EGL=ON \
                        -DENABLE_X11=OFF \
                        -DENABLE_NOGUI=ON \
                        -DUSE_DISCORD_PRESENCE=OFF \
                        -DENABLE_QT=OFF \
                        -DENABLE_TESTS=OFF \
                        -DCMAKE_BUILD_TYPE=Release"


if [ ${DEVICE} = "Amlogic-no" ]; then
   PKG_CMAKE_OPTS_TARGET+=" -DENABLE_DRM=ON"
else
   PKG_CMAKE_OPTS_TARGET+=" -DENABLE_DRM=OFF"
fi

makeinstall_target() {
export CXXFLAGS="`echo ${CXXFLAGS} | sed -e "s|-O.|-O3|g"`"
mkdir -p ${INSTALL}/usr/bin
cp -rf ${PKG_BUILD}/.${TARGET_NAME}/Binaries/dolphin-emu-nogui ${INSTALL}/usr/bin
cp -rf ${PKG_DIR}/scripts/* ${INSTALL}/usr/bin

mkdir -p ${INSTALL}/usr/share/dolphin-emu
cp -rf ${PKG_BUILD}/Data/Sys ${INSTALL}/usr/share/dolphin-emu/

mkdir -p ${INSTALL}/usr/config/emuelec/configs/dolphin-emu
cp -rf ${PKG_BUILD}/Data/Sys/* ${INSTALL}/usr/config/emuelec/configs/dolphin-emu
cp -rf ${PKG_DIR}/config/* ${INSTALL}/usr/config/emuelec/configs/dolphin-emu
}
