#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"

# Kill old instances
killall -9 gptokeyb 2>/dev/null

# Check for game-specific gptk config
GPTK_GAME="/storage/.config/emuelec/configs/gptokeyb/simcoupe/${ROMBASE}.gptk"
GPTK_DEFAULT="/emuelec/configs/gptokeyb/simcoupe.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

# Start gptokeyb with selected config
gptokeyb 1 simcoupe -c "$GPTK_CONFIG" &

# Wait for gptokeyb to initialize
sleep 1

# Launch SimCoupe
/usr/bin/simcoupe -rom /storage/roms/bios/samcoupe.rom -fullscreen -disk1 "$ROM" -autoboot

# Cleanup
killall -9 gptokeyb