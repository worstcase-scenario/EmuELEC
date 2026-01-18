#!/bin/bash
# XRoar Menu Wrapper for EmuELEC

. /etc/profile

ASSETDIR="/usr/config/emuelec/bin/xroar"

export LD_LIBRARY_PATH="${ASSETDIR}/libs.aarch64:${LD_LIBRARY_PATH}"

exec -a xroarmenu /usr/bin/xroarmenu.aarch64
