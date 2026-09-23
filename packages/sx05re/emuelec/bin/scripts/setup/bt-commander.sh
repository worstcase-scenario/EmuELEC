#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS FILE HAS BEEN CREATED BY CLAUDE.AI

. /etc/profile

BT_COMMANDER_SCRIPT="/usr/bin/scripts/setup/BT_COMMANDER.py"

function btcommander_confirm() {
    text_viewer -y -w -t "B T   C O M M A N D E R" -f 24 -m "Welcome to BT Commander.\n\nUse this tool to scan for Bluetooth audio devices, to pair and connect them with A2DP audio routing, to reconnect the device you used last, and to remove a pairing again.\n\nController Navigation:\n\n- D-Pad: Navigate menus\n- A / Start: Confirm selection\n- B: Go back\n- Select: Exit program\n\nContinue?"
    if [[ $? == 21 ]]; then
        if btcommander_start; then
            text_viewer -w -t "BT COMMANDER" -f 24 -m "\n\nBluetooth setup finished."
        else
            text_viewer -e -w -t "BT COMMANDER FAILED" -f 24 -m "There has been an error!\n\nCheck /emuelec/logs/bt-commander.log for details."
        fi
    fi
    ee_console disable
}

function btcommander_start() {
    ee_console enable

    # fbcon blanks the console after 600 seconds by default, which takes the
    # framebuffer with it while the tool is still running. Turn the timeout off.
    echo -e '\033[9;0]' > /dev/tty0

    local timeout=10
    while pgrep -x text_viewer > /dev/null 2>&1 && [[ $timeout -gt 0 ]]; do
        sleep 0.2
        timeout=$((timeout - 1))
    done

    killall -STOP emulationstation 2>/dev/null || true

    /usr/bin/python3 -u "$BT_COMMANDER_SCRIPT" 2>&1 | tee /emuelec/logs/bt-commander.log
    setup_result=${PIPESTATUS[0]}

    killall -CONT emulationstation 2>/dev/null || true
    ee_console disable

    # The tool leaves this marker when it changed the system audio routing;
    # EmulationStation has to restart to pick up the new SDL audio driver.
    if [[ -f /tmp/bt-commander.restart-es ]]; then
        rm -f /tmp/bt-commander.restart-es
        systemctl restart emustation
    fi

    [[ $setup_result == 0 ]]
}

btcommander_confirm
