#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"; ROMBASE="${ROMNAME%.*}"; ROMEXT="${ROMNAME##*.}"

export LD_LIBRARY_PATH="/usr/config/emuelec/configs/openmsx/libs:${LD_LIBRARY_PATH}"
export OPENMSX_HOME="/storage/.openMSX"
export LIBGL_VSYNC=0
export LIBGL_NOINTOVLHACK=1

# BIOS symlink
mkdir -p /storage/.openMSX/share
[ ! -e /storage/.openMSX/share/systemroms ] && \
  ln -sf /storage/roms/bios/msx /storage/.openMSX/share/systemroms

# gptk
GPTK_DIR="/storage/.config/emuelec/configs/openmsx/gptk"
GPTK_DEFAULT="${GPTK_DIR}/openmsx.gptk"
[ ! -f "${GPTK_DEFAULT}" ] && mkdir -p "${GPTK_DIR}" && \
  cp /usr/config/emuelec/configs/openmsx/gptk/openmsx.gptk "${GPTK_DEFAULT}"
[ -f "${GPTK_DIR}/${ROMBASE}.gptk" ] && GPTK_CONFIG="${GPTK_DIR}/${ROMBASE}.gptk" || GPTK_CONFIG="${GPTK_DEFAULT}"
gptokeyb 1 openmsx -c "${GPTK_CONFIG}" &
sleep 1

# Machine selection
case "$ROM" in
  */msx1/*|*/MSX1/*)           MACHINE="msx1" ;;
  */msx2/*|*/MSX2/*)           MACHINE="msx2" ;;
  */msx2+/*|*/MSX2+/*)         MACHINE="msx2plus" ;;
  */msxturbor/*|*/MSXTURBOR/*) MACHINE="turbor" ;;
  *) MACHINE="" ;;
esac
MACHINE_ARG=""
[ -n "$MACHINE" ] && MACHINE_ARG="-machine ${MACHINE}"

# ZIP/M3U extraction
ROMFILE="${ROM}"
if [ "${ROMEXT,,}" = "zip" ]; then
  TMPDIR=$(mktemp -d /tmp/openmsx_XXXXXX)
  unzip -o "${ROM}" -d "${TMPDIR}" > /dev/null 2>&1
  EXTRACTED=$(find "${TMPDIR}" -maxdepth 2 -type f | head -1)
  [ -n "${EXTRACTED}" ] && ROMFILE="${EXTRACTED}" && ROMEXT="${ROMFILE##*.}"
elif [ "${ROMEXT,,}" = "m3u" ]; then
  ROMDIR="$(dirname "${ROM}")"
  TMPDIR=$(mktemp -d /tmp/openmsx_XXXXXX)
  line=$(grep -m1 "." "${ROM}" | tr -d '\r')
  ENTRY="${line}"
  [ ! -f "${ENTRY}" ] && ENTRY="${ROMDIR}/${line}"
  EXT="${ENTRY##*.}"
  if [ "${EXT,,}" = "zip" ]; then
    DISKDIR="${TMPDIR}/disk0"
    mkdir -p "${DISKDIR}"
    unzip -o "${ENTRY}" -d "${DISKDIR}" > /dev/null 2>&1
    ENTRY=$(find "${DISKDIR}" -maxdepth 1 -type f | head -1)
  fi
  ROMFILE="${ENTRY}"
  ROMEXT="${ROMFILE##*.}"
fi

# Media type (skipped for M3U which uses DISK_ARGS array)
if [ "${ROMEXT,,}" != "m3u" ]; then
  case "${ROMEXT,,}" in
    dsk|dmk) MEDIA="-diska" ;;
    cas)     MEDIA="-cassettefile" ;;
    *)       MEDIA="-cart" ;;
  esac
fi

# Settings
[ ! -f "${OPENMSX_HOME}/share/settings.xml" ] && \
  INIT_CMD="set fullscreen on; set full_stretch on; set auto_enable_reverse off; set accuracy line; set resampler blip; set samples 2048; set frequency 44100; set scale_factor 1; set scale_algorithm simple; set vsync off; set fullspeedwhenloading on; set grabinput off; set sound_driver SDL" || \
  INIT_CMD="set fullscreen on; set full_stretch on"

/usr/bin/openmsx -command "${INIT_CMD}" ${MACHINE_ARG} ${MEDIA} "${ROMFILE}"

killall -9 gptokeyb 2>/dev/null
rm -rf /tmp/openmsx_* 2>/dev/null