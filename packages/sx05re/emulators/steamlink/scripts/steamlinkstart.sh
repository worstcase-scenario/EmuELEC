#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# steamlinkstart.sh - Steam Link launcher for EmuELEC (Amlogic-no)
#
. /etc/profile

SL_DIR="/emuelec/configs/steamlink"
SL_LIB="/usr/lib/steamlink"
SL_URL="https://media.steampowered.com/steamlink/rpi/bookworm/arm64"
LOGFILE="/emuelec/logs/steamlink.log"

mkdir -p "$(dirname "$LOGFILE")"
echo "=== $(date) ===" > "$LOGFILE"

# Steam Link may not be redistributed: fetch Valve's build on first start and on updates
LATEST=$(curl -sfL "${SL_URL}/public_build.txt")
if [ -n "$LATEST" ] && [ "$LATEST" != "$(cat "${SL_DIR}/.version" 2>/dev/null)" ]; then
    echo "Downloading ${LATEST}" >> "$LOGFILE"
    text_viewer -t "STEAM LINK" -f 24 -m "P L E A S E  W A I T . . .\n\nDownloading Steam Link from Valve...\n\nThis only happens on the first start and after updates.\n\nThis window will close itself automatically." &
    TV_PID=$!
    mkdir -p "$(dirname "$SL_DIR")"
    curl -sfL "$LATEST" | tar -xz -C "$(dirname "$SL_DIR")" && echo "$LATEST" > "${SL_DIR}/.version"
    kill "$TV_PID" 2>/dev/null
fi
if [ ! -x "${SL_DIR}/bin/shell" ]; then
    echo "ERROR: Steam Link not installed (no network?)" >> "$LOGFILE"
    exit 1
fi

QT_DIR=$(ls -d "${SL_DIR}"/Qt-* | head -1)

# drmu allocates its video buffers from linux,cma, which the Amlogic kernel does not provide
ln -sf system /dev/dma_heap/linux,cma

export QT_PLUGIN_PATH="${QT_DIR}/plugins"
export QT_QPA_PLATFORM=linuxfb
export LD_LIBRARY_PATH="${SL_DIR}/lib:${QT_DIR}/lib:${SL_LIB}:/usr/lib"
export PATH="${SL_DIR}/bin:${PATH}"
export TMPDIR="${SL_DIR}/.tmp"
export SDL_EGL_LIBRARY="${SL_LIB}/libegl_shim.so"
mkdir -p "$TMPDIR"

cd "$SL_DIR"
LD_PRELOAD="${SL_LIB}/libdrm_shim.so" ./bin/shell >> "$LOGFILE" 2>&1

# unblank the fbdev layers in case Steam Link ended during a stream
for f in /sys/class/graphics/fb*/blank; do echo 0 > "$f"; done
