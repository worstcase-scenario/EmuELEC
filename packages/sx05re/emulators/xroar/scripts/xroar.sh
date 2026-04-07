#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"

# Asset directory setup
ASSETDIR="/usr/config/emuelec/configs/xroar"
export LD_LIBRARY_PATH="${ASSETDIR}/libs.aarch64:${LD_LIBRARY_PATH}"

# Determine machine type based on ROM path
case "$ROM" in
  */dragon32/*) MACHINE="dragon32" ;;
  */dragon64/*) MACHINE="dragon64" ;;
  */coco/*)     MACHINE="coco" ;;
  */coco3/*)    MACHINE="coco3" ;;
  */mc10/*)     MACHINE="mc10" ;;
  *)            MACHINE="dragon64" ;;
esac

# Kill old instances
killall -9 gptokeyb 2>/dev/null

# Check for game-specific gptk config
GPTK_GAME="/storage/.config/emuelec/configs/xroar/gptk/${ROMBASE}.gptk"
GPTK_DEFAULT="/storage/.config/emuelec/configs/xroar/gptk/xroar.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

# Start gptokeyb with selected config
gptokeyb 1 xroar.aarch64 -c "$GPTK_CONFIG" &

# Wait for gptokeyb to initialize
sleep 1

# Launch XRoar
/usr/bin/xroar.aarch64 -fs -rompath /storage/roms/bios \
  -default-machine "$MACHINE" \
  -run "$ROM"

# Cleanup
killall -9 gptokeyb 2>/dev/null
