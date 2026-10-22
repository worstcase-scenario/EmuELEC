#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
. /etc/profile

ROM="$1"
LOG="/emuelec/logs/vita3k.log"
BIN="/usr/share/vita3k/Vita3K"
mkdir -p /emuelec/logs
# one log per launch; Vita3K itself only logs critical errors (-l 5), trace logs grow to GBs
exec > "$LOG" 2>&1
echo "=== $(date) vita3k launch: $ROM"
# config/log/cache -> /emuelec/configs/vita3k/Vita3K
# ux0 (installed games, firmware) -> /storage/roms/psvita/.vita3k/Vita3K/Vita3K
export XDG_CONFIG_HOME="/emuelec/configs/vita3k"
export XDG_CACHE_HOME="/emuelec/configs/vita3k"
export XDG_DATA_HOME="/storage/roms/psvita/.vita3k"
unset XDG_DATA_DIRS
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
# new config: skip the setup wizard (not usable with a gamepad); face buttons
# rotated like the ARMSX2 config, EmuELEC's SDL mapping swaps South/East, West/North
CFG="$XDG_CONFIG_HOME/Vita3K/config.yml"
[ -f "$CFG" ] || { mkdir -p "${CFG%/*}"; printf 'initial-setup: true\ncontroller-binds: [1, 0, 3, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]\n' > "$CFG"; }
# install firmware on first start; second try covers the upstream first-run crash
PUP="/storage/roms/bios/PSVUPDAT.PUP"
FW="$XDG_DATA_HOME/Vita3K/Vita3K/vs0"
for i in 1 2; do
    [ -d "$FW" ] || [ ! -f "$PUP" ] && break
    "$BIN" -l 5 --firmware "$PUP" < /dev/null
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
# Mali VK_KHR_display outputs alpha=0 -> make osd0 opaque (2 = None), restore after
modetest -M meson -w 31:"pixel blend mode":2 >/dev/null 2>&1
"$BIN" -F -l 5 "${ARGS[@]}" < /dev/null
RC=$?
modetest -M meson -w 31:"pixel blend mode":0 >/dev/null 2>&1
# newly installed .vpk/.zip: create matching .psvita next to it
if [ "$ext" != "psvita" ]; then
    for id in $(ls "$APPS" 2>/dev/null); do
        echo "$BEFORE" | grep -qx "$id" || echo "$id" > "${ROM%.*}.psvita"
    done
fi
echo "=== vita3k exited rc=$RC"
exit 0
