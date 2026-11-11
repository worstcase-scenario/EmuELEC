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
    text_viewer -t "STEAM LINK" -f 24 -m "Downloading Steam Link from Valve...\n\nThis only happens on the first start and after updates.\n\nPlease wait.\n\nThis window will close itself automatically when the download is finished." &
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
# some fbdev drivers report bogus physical sizes, which makes Qt scale the UI up:
# pass the current mode with the physical size of a 96 dpi screen
FB_WH=$(cut -d: -f2 /sys/class/graphics/fb0/modes 2>/dev/null | head -1)
FB_WH=${FB_WH%%[pi]*}
FB_W=${FB_WH%x*}
FB_H=${FB_WH#*x}
if [ "${FB_W:-0}" -gt 0 ] 2>/dev/null && [ "${FB_H:-0}" -gt 0 ] 2>/dev/null; then
    export QT_QPA_PLATFORM="linuxfb:size=${FB_W}x${FB_H}:mmsize=$((FB_W * 254 / 960))x$((FB_H * 254 / 960))"
fi
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export QT_SCALE_FACTOR=1
export LD_LIBRARY_PATH="${SL_DIR}/lib:${QT_DIR}/lib:${SL_LIB}:/usr/lib"
export PATH="${SL_DIR}/bin:${PATH}"
export TMPDIR="${SL_DIR}/.tmp"
export SDL_EGL_LIBRARY="${SL_LIB}/libegl_shim.so"
mkdir -p "$TMPDIR"

cd "$SL_DIR"
LD_PRELOAD="${SL_LIB}/libdrm_shim.so" ./bin/shell >> "$LOGFILE" 2>&1

# unblank the fbdev layers in case Steam Link ended during a stream
for f in /sys/class/graphics/fb*/blank; do echo 0 > "$f"; done
