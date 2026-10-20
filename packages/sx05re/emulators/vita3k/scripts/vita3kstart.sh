#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
. /etc/profile

ROM="$1"
LOG="/emuelec/logs/vita3k.log"
BIN="/usr/share/vita3k/Vita3K"
mkdir -p /emuelec/logs
exec >> "$LOG" 2>&1
echo "=== $(date) vita3k launch: $ROM"
# config/log/cache -> /emuelec/configs/vita3k/Vita3K
# ux0 (installed games, firmware) -> /storage/roms/psvita/.vita3k/Vita3K/Vita3K
export XDG_CONFIG_HOME="/emuelec/configs/vita3k"
export XDG_CACHE_HOME="/emuelec/configs/vita3k"
export XDG_DATA_HOME="/storage/roms/psvita/.vita3k"
unset XDG_DATA_DIRS
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
# skip the initial setup wizard (not usable with a gamepad)
CFG="$XDG_CONFIG_HOME/Vita3K/config.yml"
[ -f "$CFG" ] || { mkdir -p "${CFG%/*}"; echo 'initial-setup: true' > "$CFG"; }
# install firmware on first start; second try covers the upstream first-run crash
PUP="/storage/roms/bios/PSVUPDAT.PUP"
FW="$XDG_DATA_HOME/Vita3K/Vita3K/vs0"
for i in 1 2; do
    [ -d "$FW" ] || [ ! -f "$PUP" ] && break
    "$BIN" --firmware "$PUP" < /dev/null
done
# .psvita: text file, first line = title ID of an installed game (e.g. PCSE00000)
# .vpk/.zip: installed on first start, then run
ext="$(echo "${ROM##*.}" | tr 'A-Z' 'a-z')"
case "$ext" in
    psvita) ARGS=(-r "$(head -1 "$ROM" | tr -d ' \r\n')") ;;
    *)      ARGS=(-- "$ROM") ;;
esac
APPS="$XDG_DATA_HOME/Vita3K/Vita3K/ux0/app"
BEFORE="$(ls "$APPS" 2>/dev/null)"
"$BIN" -F "${ARGS[@]}" < /dev/null
RC=$?
# newly installed .vpk/.zip: create matching .psvita next to it
if [ "$ext" != "psvita" ]; then
    for id in $(ls "$APPS" 2>/dev/null); do
        echo "$BEFORE" | grep -qx "$id" || echo "$id" > "${ROM%.*}.psvita"
    done
fi
echo "=== vita3k exited rc=$RC"
exit 0
