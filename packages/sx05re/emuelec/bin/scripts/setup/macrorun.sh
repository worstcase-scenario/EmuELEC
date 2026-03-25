#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

. /etc/profile

MACRO_RUN_SCRIPT="/usr/bin/scripts/setup/macrorun.py"
MACRO_LOG="/emuelec/logs/macrorun.log"
MACRO_RET="/tmp/macrorun.ret"

function macrorun_start() {
    ee_console enable

    TTY="/dev/tty1"
    [[ -w "$TTY" ]] || TTY="/dev/tty0"
    [[ -w "$TTY" ]] || TTY="/dev/console"

    exec <"$TTY" >"$TTY" 2>&1

    for b in /sys/class/graphics/fb0/blank /sys/class/graphics/fb1/blank; do
        [[ -w "$b" ]] && echo 0 >"$b"
    done

    if command -v setterm >/dev/null 2>&1; then
        setterm -blank 0 -powerdown 0 -powersave off >"$TTY" 2>/dev/null || true
    fi

    clear

    if [[ ! -f "$MACRO_RUN_SCRIPT" ]]; then
        echo "ERROR: macrorun.py not found at $MACRO_RUN_SCRIPT"
        ee_console disable
        return 1
    fi

    chmod +x "$MACRO_RUN_SCRIPT"
    mkdir -p "$(dirname "$MACRO_LOG")"

    rm -f "$MACRO_RET" >/dev/null 2>&1

    if command -v openvt >/dev/null 2>&1; then
        openvt -c 1 -s -f -- /bin/sh -c \
            "/usr/bin/python3 -u '$MACRO_RUN_SCRIPT' 2>&1 | tee '$MACRO_LOG'; echo \$? >'$MACRO_RET'"
        run_result=$(cat "$MACRO_RET" 2>/dev/null || echo 1)
    else
        /usr/bin/python3 -u "$MACRO_RUN_SCRIPT" 2>&1 | tee "$MACRO_LOG"
        run_result=${PIPESTATUS[0]}
    fi

    ee_console disable
    rm -f /tmp/display >/dev/null 2>&1

    return "$run_result"
}

macrorun_start
