# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="dxc"
PKG_VERSION="1.8.2505.1"
PKG_SHA256="f2213da1fc99dc8778c8823078e16ba97c7f80f86a1d4520ab1adf4b462bc48c"
PKG_LICENSE="LLVM"
PKG_SITE="https://github.com/microsoft/DirectXShaderCompiler"
PKG_URL="${PKG_SITE}/releases/download/v${PKG_VERSION}/linux_dxc_2025_07_14.x86_64.tar.gz"
PKG_DEPENDS_HOST=""
PKG_LONGDESC="DirectX Shader Compiler, prebuilt x86_64 host binary (HLSL to SPIR-V)"
PKG_TOOLCHAIN="manual"

# The archive has no top-level directory
unpack() {
  mkdir -p ${PKG_BUILD}
  tar -xf ${SOURCES}/${PKG_NAME}/${PKG_SOURCE_NAME} -C ${PKG_BUILD}
}

makeinstall_host() {
  mkdir -p ${TOOLCHAIN}/bin ${TOOLCHAIN}/lib
  cp ${PKG_BUILD}/bin/dxc ${TOOLCHAIN}/bin
  cp ${PKG_BUILD}/lib/libdxcompiler.so ${TOOLCHAIN}/lib
}
