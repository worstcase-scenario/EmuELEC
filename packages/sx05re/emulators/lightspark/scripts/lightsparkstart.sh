#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"

LIGHTSPARK_BIN="/usr/bin/lightspark"
LIGHTSPARK_LIB="/usr/lib"

export LD_LIBRARY_PATH="${LIGHTSPARK_LIB}:${LD_LIBRARY_PATH}"

# Kill old instances
killall -9 gptokeyb 2>/dev/null
killall -9 lightspark 2>/dev/null

# Check for game-specific gptk config
GPTK_GAME="/storage/.config/emuelec/configs/lightspark/gptk/${ROMBASE}.gptk"
GPTK_DEFAULT="/storage/.config/emuelec/configs/lightspark/gptk/lightspark.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

# Start gptokeyb
gptokeyb 1 lightspark -c "$GPTK_CONFIG" &
sleep 1

# Launch Lightspark
"${LIGHTSPARK_BIN}" -fs "${ROM}"

# Cleanup
killall -9 gptokeyb 2>/dev/null