#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS FILE HAS BEEN CREATED BY CLAUDE.AI

. /etc/profile

RUFFLE_INSTALL_SCRIPT="/usr/bin/scripts/setup/RUFFLE_INSTALL.py"

function ruffleinstall_confirm() {
    text_viewer -y -w -t "Install Flash (Ruffle)" -f 24 -m "This will install the Ruffle Flash player (approx. 160 MB download) and enable it on Emulationstation.\n\nPlays .swf games fullscreen with gamepad controls. Place your games in /storage/roms/flash - per-game controls can be set with a <game>.gptk file next to the .swf.\n\nBased on the Qt Web Browser port by Snowram and Ruffle 0.3.0. Exit games with Select+Start.\n\nController Navigation:\n\n- D-Pad: Navigate menus\n- A / Start: Confirm selection\n- B: Go back\n- Select: Exit program\n\nNOTE: You need an active internet connection. EmulationStation will automatically restart after this script ends. Continue?"
    if [[ $? == 21 ]]; then
        if ruffleinstall_start; then
            text_viewer -w -t "Install Flash (Ruffle)" -f 24 -m "\n\nDon't forget to put .swf games into /storage/roms/flash!\n\nEmulationStation will restart now.\n\nNOTE: Starting a flash file for the first time can take a while, be patient when you only see a black screen."
            ee_console disable
            
            # Automatically restart EmulationStation after a successful installation
            systemctl restart emustation
            exit 0
        else
            text_viewer -e -w -t "Install Flash (Ruffle) FAILED" -f 24 -m "There has been an error!\n\nCheck /emuelec/logs/ruffle-install.log for details."
        fi
    fi
    ee_console disable
}

function ruffleinstall_start() {
    ee_console enable

    local timeout=10
    while pgrep -x text_viewer > /dev/null 2>&1 && [[ $timeout -gt 0 ]]; do
        sleep 0.2
        timeout=$((timeout - 1))
    done

    killall -STOP emulationstation 2>/dev/null || true

    /usr/bin/python3 -u "$RUFFLE_INSTALL_SCRIPT" 2>&1 | tee -a /emuelec/logs/ruffle-install.log
    setup_result=${PIPESTATUS[0]}

    killall -CONT emulationstation 2>/dev/null || true
    ee_console disable

    [[ $setup_result == 0 ]]
}

ruffleinstall_confirm