#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)
. /etc/profile
LOG="/emuelec/logs/macrosetup.log"
SCRIPT="/usr/bin/scripts/setup/macrosetup.py"

text_viewer -y -w -t "MACRO SETUP" -f 24 \
    -m "Record a macro.\n\nAssign a trigger button, then record any combination of button presses and analog stick movements.\n\nStick / D-Pad: navigate  A: confirm  B: cancel  Y: erase\n\nContinue?" || exit 0

ee_console enable
TTY="/dev/tty1"; [[ -w "$TTY" ]] || TTY="/dev/tty0"; [[ -w "$TTY" ]] || TTY="/dev/console"
exec <"$TTY" >"$TTY" 2>&1
for b in /sys/class/graphics/fb0/blank /sys/class/graphics/fb1/blank; do [[ -w "$b" ]] && echo 0 >"$b"; done
command -v setterm &>/dev/null && setterm -blank 0 -powerdown 0 -powersave off >"$TTY" 2>/dev/null
clear; [[ -f "$SCRIPT" ]] || { echo "ERROR: $SCRIPT not found"; ee_console disable; exit 1; }
chmod +x "$SCRIPT"; mkdir -p "$(dirname "$LOG")"; RET="/tmp/macrosetup.ret"; rm -f "$RET"

if command -v openvt &>/dev/null; then
    openvt -c 1 -s -f -- /bin/sh -c "/usr/bin/python3 -u '$SCRIPT' 2>&1 | tee '$LOG'; echo \$? >'$RET'"
    result=$(cat "$RET" 2>/dev/null || echo 1)
else
    /usr/bin/python3 -u "$SCRIPT" 2>&1 | tee "$LOG"; result=${PIPESTATUS[0]}
fi

ee_console disable; rm -f /tmp/display
[[ $result == 0 ]] \
    && text_viewer -w  -t "MACRO SETUP"   -f 24 -m "\n\nMacro saved.\n\nActivate it with Macro Enabler." \
    || text_viewer -e -w -t "MACRO SETUP" -f 24 -m "Cancelled or error.\n\nSee: $LOG"
