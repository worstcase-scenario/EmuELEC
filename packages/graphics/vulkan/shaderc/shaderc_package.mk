# SPDX-License-Identifier: GPL-2.0-or-later

PKG_NAME="shaderc"
PKG_VERSION="2023.2"
PKG_SHA256="06c4e2fdd63d62b73450d7011b72e7720b416182fb883fb0aac0afe6db2df3f6"
PKG_LICENSE="Apache-2.0"
PKG_SITE="https://github.com/google/shaderc"
PKG_URL="${PKG_SITE}/archive/v${PKG_VERSION}.tar.gz"
PKG_DEPENDS_HOST="toolchain:host Python3:host glslang:host"
PKG_LONGDESC="glslc GLSL to SPIR-V compiler (host tool)"
PKG_TOOLCHAIN="cmake"

# v2023.2 matches the glslang/spirv-tools/spirv-headers versions in the tree.
# Sources are taken from glslang:host (PKG_DEPENDS_UNPACK would hit the unpack recursion limit)
pre_configure_host() {
  # glslang in the tree no longer provides OGLCompiler/HLSL libs
  sed -i "s/ OGLCompiler//; s/ HLSL//" ${PKG_BUILD}/glslc/CMakeLists.txt ${PKG_BUILD}/libshaderc/CMakeLists.txt ${PKG_BUILD}/libshaderc_util/CMakeLists.txt
  # spirv-tools in the tree needs C++17
  sed -i "s/set (CMAKE_CXX_STANDARD 11)/set (CMAKE_CXX_STANDARD 17)/" ${PKG_BUILD}/CMakeLists.txt
  cp -R $(get_build_dir glslang) ${PKG_BUILD}/third_party/glslang
  cp -R $(get_build_dir spirv-tools) ${PKG_BUILD}/third_party/spirv-tools
  cp -R $(get_build_dir spirv-headers) ${PKG_BUILD}/third_party/spirv-headers
}

PKG_CMAKE_OPTS_HOST="-DSHADERC_SKIP_TESTS=ON \
                     -DSHADERC_SKIP_EXAMPLES=ON \
                     -DSHADERC_SKIP_COPYRIGHT_CHECK=ON \
                     -DSPIRV_SKIP_TESTS=ON \
                     -DSPIRV_SKIP_EXECUTABLES=ON \
                     -DENABLE_GLSLANG_BINARIES=OFF \
                     -DSKIP_GLSLANG_INSTALL=ON \
                     -DCMAKE_BUILD_TYPE=Release"

make_host() {
  ninja ${NINJA_OPTS} glslc_exe
}

makeinstall_host() {
  mkdir -p ${TOOLCHAIN}/bin
  cp glslc/glslc ${TOOLCHAIN}/bin
}
