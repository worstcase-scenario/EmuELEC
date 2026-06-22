#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"

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

    # Priorität: cas > c10 > k7 > bas > asc > rom > ccc > bin > vdk > dsk > jvc > os9 > dmk > wav
    for EXT in cas c10 k7 bas asc rom ccc bin vdk dsk jvc os9 dmk wav; do
      FOUND=$(find "$TMPDIR" -type f -iname "*.${EXT}" | head -1)
      if [ -n "$FOUND" ]; then
        ROM="$FOUND"
        break
      fi
    done

    CLEANUP_TMPDIR=1
    ;;
esac

# Determine load flag based on file type
case "${ROM##*.}" in
  vdk|VDK|dsk|DSK|jvc|JVC|os9|OS9|dmk|DMK)
    LOAD_FLAG="-load"
    ;;
  rom|ROM|ccc|CCC|bin|BIN)
    LOAD_FLAG="-run"
    ;;
  cas|CAS|wav|WAV|k7|K7|c10|C10|bas|BAS|asc|ASC)
    LOAD_FLAG="-run"
    ;;
  *)
    LOAD_FLAG="-run"
    ;;
esac

# Kill old instances
killall -9 gptokeyb 2>/dev/null

# Check for game-specific gptk config
GPTK_GAME="/storage/.config/emuelec/configs/xroar/gptk/${ROMBASE}.gptk"
GPTK_DEFAULT="/usr/config/emuelec/configs/xroar/gptk/xroar.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

# Start gptokeyb with selected config
gptokeyb 1 xroar -c "$GPTK_CONFIG" &

# Wait for gptokeyb to initialize
sleep 1

# Launch XRoar
/usr/bin/xroar -fs -rompath /storage/roms/bios \
  -default-machine "$MACHINE" \
  ${LOAD_FLAG} "$ROM"

# Cleanup
killall -9 gptokeyb 2>/dev/null

if [ "$CLEANUP_TMPDIR" = "1" ]; then
  rm -rf "$TMPDIR"
fi