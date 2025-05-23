PKG_NAME="python-uinput"
PKG_VERSION="master"
PKG_LICENSE="GPL"
PKG_SITE="https://github.com/tuomasjjrasanen/python-uinput"
PKG_URL="https://github.com/tuomasjjrasanen/python-uinput/archive/refs/heads/master.tar.gz"
PKG_DEPENDS_TARGET="toolchain Python3"
PKG_LONGDESC="Pythonic API to create virtual input devices via uinput kernel module."
PKG_TOOLCHAIN="manual"

pre_make_target() {
  export LDSHARED="${CC} -shared"
}

make_target() {
  python3 setup.py build
}

makeinstall_target() {
  mkdir -p ${INSTALL}/usr/lib/python3.11/site-packages
  
  for libdir in ${PKG_BUILD}/build/lib*; do
    if [ -d "$libdir" ]; then
      cp -r "$libdir"/* ${INSTALL}/usr/lib/python3.11/site-packages/
    fi
  done
}

post_makeinstall_target() {
  python_remove_source
}