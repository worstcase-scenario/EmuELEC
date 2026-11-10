# SPDX-License-Identifier: GPL-2.0

PKG_NAME="krb5"
PKG_VERSION="1.21.3"
PKG_SHA256="b7a4cd5ead67fb08b980b21abd150ff7217e85ea320c9ed0c6dadd304840ad35"
PKG_LICENSE="MIT"
PKG_SITE="https://web.mit.edu/kerberos/"
PKG_URL="https://kerberos.org/dist/krb5/${PKG_VERSION%.*}/krb5-${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain"
PKG_LONGDESC="MIT Kerberos client libraries (libgssapi_krb5 for Qt5Network)"
PKG_TOOLCHAIN="configure"

PKG_CONFIGURE_OPTS_TARGET="ac_cv_func_regcomp=yes \
                           ac_cv_printf_positional=yes \
                           krb5_cv_attr_constructor_destructor=yes,yes \
                           --with-crypto-impl=builtin \
                           --with-tls-impl=no \
                           --disable-pkinit \
                           --disable-rpath \
                           --without-keyutils \
                           --without-ldap \
                           --without-lmdb \
                           --without-tcl \
                           --without-libedit \
                           --without-readline"

pre_configure_target() {
  PKG_CONFIGURE_SCRIPT="${PKG_BUILD}/src/configure"
}

# only the client libraries are needed (lib/ in the build tree holds symlinks into the sources)
makeinstall_target() {
  make install DESTDIR=${PKG_BUILD}/.install_tmp
  mkdir -p ${INSTALL}/usr/lib
  for l in libgssapi_krb5.so.2 libkrb5.so.3 libk5crypto.so.3 libkrb5support.so.0 libcom_err.so.3; do
    cp -P ${PKG_BUILD}/.install_tmp/usr/lib/${l}* ${INSTALL}/usr/lib/
  done
}
