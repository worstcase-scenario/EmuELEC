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

# Handle compressed files (ZIP and 7Z)
case "${ROM##*.}" in
  zip|ZIP|7z|7Z)
    TMPDIR="/tmp/xroar_rom_$$"
    mkdir -p "$TMPDIR"
    
    if [ "${ROM##*.}" = "7z" ] || [ "${ROM##*.}" = "7Z" ]; then
      7z x -q "$ROM" -o"$TMPDIR"
    else
      unzip -q "$ROM" -d "$TMPDIR"
    fi
    
    # Find first valid XRoar file
    ROM=$(find "$TMPDIR" -type f \( \
      -iname "*.cas" -o -iname "*.c10" -o -iname "*.wav" -o -iname "*.k7" -o \
      -iname "*.bas" -o -iname "*.asc" -o \
      -iname "*.rom" -o -iname "*.ccc" -o \
      -iname "*.vdk" -o -iname "*.dsk" -o -iname "*.jvc" -o -iname "*.os9" -o -iname "*.dmk" -o \
      -iname "*.bin" \
    \) | head -1)
    
    CLEANUP_TMPDIR=1
    ;;
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

if [ "$CLEANUP_TMPDIR" = "1" ]; then
  rm -rf "$TMPDIR"
fi
