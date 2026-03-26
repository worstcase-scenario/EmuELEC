#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)
. /etc/profile
LOG="/emuelec/logs/macrorun.log"
CFG="/storage/.config/emuelec/scripts/macro_config.json"
SCRIPT="/usr/bin/scripts/setup/macrorun.py"

[[ -f "$CFG" ]] || { text_viewer -e -w -t "MACRO ENABLER" -f 24 -m "No macros found.\n\nRun Macro Setup first."; exit 0; }
count=$(grep -c '"name"' "$CFG" 2>/dev/null || echo 0)
text_viewer -y -w -t "MACRO ENABLER" -f 24 \
    -m "Found ${count} macro(s).\n\nSelect and activate a macro. The trigger button replays the recorded sequence.\nHold trigger 3 s to stop.\n\nStick / D-Pad: navigate  A: activate  B: cancel\n\nContinue?" || exit 0

ee_console enable
TTY="/dev/tty1"; [[ -w "$TTY" ]] || TTY="/dev/tty0"; [[ -w "$TTY" ]] || TTY="/dev/console"
exec <"$TTY" >"$TTY" 2>&1
for b in /sys/class/graphics/fb0/blank /sys/class/graphics/fb1/blank; do [[ -w "$b" ]] && echo 0 >"$b"; done
command -v setterm &>/dev/null && setterm -blank 0 -powerdown 0 -powersave off >"$TTY" 2>/dev/null
clear; [[ -f "$SCRIPT" ]] || { echo "ERROR: $SCRIPT not found"; ee_console disable; exit 1; }
chmod +x "$SCRIPT"; mkdir -p "$(dirname "$LOG")"; RET="/tmp/macrorun.ret"; rm -f "$RET"

if command -v openvt &>/dev/null; then
    openvt -c 1 -s -f -- /bin/sh -c "/usr/bin/python3 -u '$SCRIPT' 2>&1 | tee '$LOG'; echo \$? >'$RET'"
    result=$(cat "$RET" 2>/dev/null || echo 1)
else
    /usr/bin/python3 -u "$SCRIPT" 2>&1 | tee "$LOG"; result=${PIPESTATUS[0]}
fi

ee_console disable; rm -f /tmp/display
[[ $result == 0 ]] \
    && text_viewer -w -t "MACRO ENABLER" -f 24 -m "Macro mode is now active in the background!\n\nATTENTION: DO NOT press the trigger button as long as you are in EmulationStation, otherwise the new controller-setup screen will pop up.\n\nIn this case, just press the hotkey button to exit the routine.\n\nTo DISABLE the macro again, press the macro button for around 3-5 seconds." \
    || text_viewer -e -w -t "MACRO ENABLER" -f 24 -m "Cancelled or error.\n\nSee: $LOG"
