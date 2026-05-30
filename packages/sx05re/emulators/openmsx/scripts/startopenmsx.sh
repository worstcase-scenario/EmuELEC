#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"
ROMEXT="${ROMNAME##*.}"

# libGLX.so.0 is required by GLEW but absent from EmuELEC /usr/lib on Amlogic
export LD_LIBRARY_PATH="/usr/config/emuelec/configs/openmsx/libs:${LD_LIBRARY_PATH}"

# User-writable config dir - consistent with other EmuELEC emulators
export OPENMSX_HOME="/storage/.config/emuelec/configs/openmsx"

# Create systemroms symlink so openMSX finds BIOS files from the standard
# EmuELEC BIOS location (/storage/roms/bios) without manual copying.
if [ ! -e /storage/.config/emuelec/configs/openmsx/share/systemroms ]; then
  ln -sf /storage/roms/bios/msx \
    /storage/.config/emuelec/configs/openmsx/share/systemroms
fi

killall -9 gptokeyb 2>/dev/null

GPTK_GAME="/storage/.config/emuelec/configs/openmsx/gptk/${ROMBASE}.gptk"
GPTK_DEFAULT="/usr/config/emuelec/configs/openmsx/gptk/openmsx.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

gptokeyb 1 openmsx -c "$GPTK_CONFIG" &
sleep 1

case "$ROM" in
  */msx1/*|*/MSX1/*) MACHINE_ARG="-machine msx1" ;;
  */msx2/*|*/MSX2/*) MACHINE_ARG="-machine msx2" ;;
  */msx2+/*|*/MSX2+/*) MACHINE_ARG="-machine msx2plus" ;;
  */msxturbor/*|*/MSXTURBOR/*) MACHINE_ARG="-machine turbor" ;;
  *) MACHINE_ARG="" ;;
esac

case "${ROMEXT,,}" in
  dsk|dmk) MEDIA="-diska" ;;
  cas)     MEDIA="-cassettefile" ;;
  *)       MEDIA="-cart" ;;
esac

/usr/bin/openmsx \
  ${MACHINE_ARG} \
  ${MEDIA} "${ROM}"

killall -9 gptokeyb 2>/dev/null