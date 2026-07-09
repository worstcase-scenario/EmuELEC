#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present worstcase_scenario (https://github.com/worstcase-scenario)
. /etc/profile

ROM="$1"
BIOS="/storage/roms/bios/fmtowns"
LOG="/emuelec/logs/tsugaru.log"
BIN="/usr/bin/tsugaru"
mkdir -p /emuelec/logs
exec >> "$LOG" 2>&1
echo "=== $(date) tsugaru launch: $ROM"
if [ ! -f "$BIOS/FMT_SYS.ROM" ]; then
    echo "ERROR: FM Towns BIOS not found in $BIOS"
    exit 1
fi
if [ ! -f "$ROM" ]; then
    echo "ERROR: ROM not found: $ROM"
    exit 1
fi
# --- media type by extension -------------------------------------------------
base="${ROM%.*}"
ext="$(echo "${ROM##*.}" | tr 'A-Z' 'a-z')"
case "$ext" in
    cue|iso|mds|ccd)  MEDIA="-CD" ;;
    d77|d88|hdm|xdf|bin) MEDIA="-FD0" ;;
    *)                MEDIA="-CD" ;;
esac
# --- per-game extra options: <rom>.opts (one line of extra CLI args) ---------
EXTRA=""
[ -f "${base}.opts" ] && EXTRA="$(head -1 "${base}.opts")"
# --- run ----------------------------------------------------------------------
SDL_VIDEODRIVER=mali "$BIN" "$BIOS" \
    -FULLSCREEN -AUTOSCALE -CDSPEED 32 \
    -GAMEPORT0 ANA1 \
    $MEDIA "$ROM" $EXTRA < /dev/null
RC=$?
echo "=== tsugaru exited rc=$RC"
exit $RC