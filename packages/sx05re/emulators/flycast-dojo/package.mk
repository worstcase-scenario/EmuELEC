# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present DiegroSan (https://github.com/Diegrosan)

PKG_NAME="flycast-dojo"
PKG_VERSION="fa518ac574b17fbc70837f97275c019b208a8740" #6.53+
PKG_LICENSE="GPLv2"
PKG_SITE="https://github.com/blueminder/flycast-dojo"
PKG_URL="${PKG_SITE}.git"
PKG_DEPENDS_TARGET="toolchain ${OPENGLES} alsa SDL2 libzip zip asio vksdl "
PKG_LONGDESC="flycast-dojo is a multiplatform Sega Dreamcast, Naomi and Atomiswave emulator"
PKG_TOOLCHAIN="cmake"
PKG_GIT_CLONE_BRANCH="dojo"

PKG_CMAKE_OPTS_TARGET+=" -DTHREAD_SANITIZER_AVAILABLE_EXITCODE=1"
PKG_CMAKE_OPTS_TARGET+=" -DADDRESS_SANITIZER_AVAILABLE_EXITCODE=1"
PKG_CMAKE_OPTS_TARGET+=" -DALL_SANITIZERS_AVAILABLE_EXITCODE=1"
PKG_CMAKE_OPTS_TARGET+=" -DUSE_GLES=ON -DUSE_HOST_SDL=ON -DENABLE_CTEST=OFF -DTEST_AUTOMATION=OFF -DASAN=OFF "

if [ "${ARCH}" == "arm" ]; then
    PKG_PATCH_DIRS="arm"
fi

pre_configure_target() {
  export CXXFLAGS="${CXXFLAGS} -Wno-error=array-bounds -Wswitch -Wsign-compare -I$(get_install_dir asio)/usr/include"
  if [ "${DEVICE}" = "Amlogic-no" ]; then
    PKG_CMAKE_OPTS_TARGET+=" -DUSE_VULKAN=ON"
  else
    PKG_CMAKE_OPTS_TARGET+=" -DUSE_VULKAN=OFF"
  fi
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/bin
  mkdir -p ${INSTALL}/usr/config/flycast-dojo
  
  cp -r ${PKG_DIR}/config/* ${INSTALL}/usr/config/flycast-dojo
  
  cp "${PKG_BUILD}/.${TARGET_NAME}/flycast" "${INSTALL}/usr/bin/flycastdojo"
  cp ${PKG_DIR}/scripts/* ${INSTALL}/usr/bin

  chmod +x ${INSTALL}/usr/bin/flycastdojo.sh

	mkdir -p "${INSTALL}/usr/config/emuelec/configs"
	ln -sf "/storage/.config/flycast-dojo" "${INSTALL}/usr/config/emuelec/configs/flycast-dojo"

}
