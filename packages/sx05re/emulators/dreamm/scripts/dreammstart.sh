#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2024-present Harakiri (https://github.com/worstcase-scenario)
#
# dreamm.sh - DREAMM launcher for EmuELEC
#
# ROMs are directories named <game>.dreamm containing the game files, following
# the same convention as daphne/hypseus. A .dreamm file produced by DREAMM's
# own -makedreamm is launched instead when one is passed.
#
# Called with no argument, DREAMM's Game Manager is started so games can be
# installed with -install / -autoinstall from the shell.

. /etc/profile

# Software mouse pointer: EmuELEC's SDL2 only ships the "mali" and "offscreen"
# video drivers, neither of which implements a hardware cursor.
export LD_PRELOAD="/usr/lib/dreamm_cursor.so"
export DREAMM_CURSOR_SCALE="${DREAMM_CURSOR_SCALE:-3}"
export DREAMM_CURSOR_TOGGLE="${DREAMM_CURSOR_TOGGLE:-66}"   # F9
export DREAMM_MENU_KEY="${DREAMM_MENU_KEY:-67}"             # F10 -> F12

export LIBGL_NOTEST=1
export SDL_VIDEODRIVER=mali

USERPATH="/storage/roms/dreamm"
LOGFILE="/emuelec/logs/dreamm.log"

dir="${1%/}"
ROMNAME="${dir##*/}"
ROMBASE="${ROMNAME%.*}"

mkdir -p "$(dirname "$LOGFILE")" "$USERPATH"

killall -9 gptokeyb 2>/dev/null

GPTK_GAME="/storage/.config/emuelec/configs/gptokeyb/dreamm/${ROMBASE}.gptk"
GPTK_DEFAULT="/emuelec/configs/gptokeyb/dreamm.gptk"

if [ -f "$GPTK_GAME" ]; then
    GPTK_CONFIG="$GPTK_GAME"
else
    GPTK_CONFIG="$GPTK_DEFAULT"
fi

# Per-game overrides, e.g. DREAMM_CURSOR=0 for titles drawing their own pointer
if [ -d "$dir" ] && [ -f "${dir}/dreamm.conf" ]; then
    . "${dir}/dreamm.conf"
fi

if [ -z "$dir" ]; then
    MODE=""
elif [ ! -e "$dir" ]; then
    echo "ERROR: path not found: $dir" | tee -a "$LOGFILE"
    exit 1
elif [ -d "$dir" ]; then
    MODE="-run"
else
    MODE="-launch"
fi

gptokeyb 1 dreamm -c "$GPTK_CONFIG" &
sleep 1

{
    echo "=== $(date) ==="
    echo "MODE: ${MODE:-frontend}"
    echo "GAME: ${dir:-none}"
    echo "GPTK: ${GPTK_CONFIG}"
    if [ -n "$MODE" ]; then
        dreamm -userpath "$USERPATH" $MODE "$dir" -sdl -fullscreen -nowait
    else
        dreamm -userpath "$USERPATH" -sdl -fullscreen
    fi
} >> "$LOGFILE" 2>&1

killall -9 gptokeyb 2>/dev/null

exit 0