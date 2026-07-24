#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS FILE HAS BEEN CREATED BY CLAUDE.AI

. /etc/profile

PORT_URL="https://github.com/worstcase-scenario/qtruffle/releases/download/v1.0/flash-ruffle-emuelec.tar.gz"
PORTDIR="/storage/roms/ports/qtwebbrowser"
SCRIPTS="/storage/roms/ports_scripts"
ESCFG="/storage/.emulationstation/es_systems.cfg"
CACHE="/storage/roms/flash-ruffle-emuelec.tar.gz"
LOG="/emuelec/logs/ruffle-install.log"

fail() { echo "$1" | tee -a "$LOG"; return 1; }

ruffle_confirm() {
    text_viewer -y -w -t "Install Flash (Ruffle)" -f 24 -m "This will install the Ruffle Flash player (approx. 150 MB download) and enable it on Emulationstation.\n\nPlays .swf games fullscreen with gamepad controls. Place your games in /storage/roms/flash - per-game controls can be set with a <game>.gptk file next to the .swf.\n\nBased on the Qt Web Browser port by Snowram and Ruffle 0.3.0.\n\nNOTE: You need an active internet connection and you will need to restart ES after this script ends, continue?"
    if [[ $? == 21 ]]; then
        if ruffle_install; then
            text_viewer -w -t "Install Flash (Ruffle) Complete!" -f 24 -m "Installation is done!\n\nDon't forget to put .swf games into /storage/roms/flash and restart Emulationstation\n\n\NOTE: IF YOU START A FLASH FILE FOR THE FIRST TIME, BE PATIENT - LOADING CAN TAKE SOME TIME!"
            ruffle_browser_option
        else
            text_viewer -e -w -t "Install Flash (Ruffle) FAILED!" -f 24 -m "Installation was not completed!\n\nAre you sure you are connected to the internet?\n\nCheck ${LOG} for details."
        fi
    fi
    ee_console disable
}

ruffle_install() {
    ee_console enable
    mkdir -p "$(dirname "$LOG")"; rm -f "$LOG"
    # ee_console rebinds the console to tty0 but not our own stdout; wrapping the
    # body with >/dev/tty0 makes progress visible whether launched from ES or SSH.
    ( ruffle_install_body ) >/dev/tty0 2>&1
}

ruffle_install_body() {
    # --- Download and extract (skip if already installed) ---
    if [[ ! -f "$PORTDIR/qtwebbrowser.aarch64" ]]; then
        if [[ ! -f "$CACHE" ]]; then
            echo ">> Downloading port..." | tee -a "$LOG"
            wget -O "$CACHE" "$PORT_URL" 2>&1 | tee -a "$LOG"
        fi
        gzip -t "$CACHE" 2>>"$LOG" || { rm -f "$CACHE"; fail "archive missing or corrupted"; return 1; }
        echo ">> Extracting..." | tee -a "$LOG"
        mkdir -p /storage/roms/ports "$SCRIPTS"
        tar -xzf "$CACHE" -C /storage 2>>"$LOG" || { fail "extraction failed"; return 1; }
        rm -f "$CACHE"
    else
        echo ">> Port already installed" | tee -a "$LOG"
    fi

    [[ -f "$PORTDIR/qtwebbrowser.aarch64" ]] || { fail "qtwebbrowser.aarch64 missing"; return 1; }
    [[ -f "$PORTDIR/ruffle/ruffle.js" ]] || { fail "ruffle.js missing"; return 1; }
    chmod +x "$SCRIPTS/Flash-Ruffle.sh" "$SCRIPTS/qtwebbrowser.sh" 2>/dev/null
    mkdir -p /storage/roms/flash

    # --- ES system entry (with backup, idempotent) ---
    if [[ -f "$ESCFG" ]] && grep -q '<emulator name="ruffle">' "$ESCFG"; then
        echo ">> ES system entry already present" | tee -a "$LOG"
        return 0
    fi
    echo ">> Writing ES system entry..." | tee -a "$LOG"
    mkdir -p "$(dirname "$ESCFG")"
    if [[ -f "$ESCFG" ]]; then
        cp "$ESCFG" "$ESCFG.bak.$(date +%Y%m%d%H%M%S)" || { fail "es_systems.cfg backup failed"; return 1; }
    else
        printf '<?xml version="1.0"?>\n<systemList>\n</systemList>\n' > "$ESCFG"
    fi
    grep -q "</systemList>" "$ESCFG" || { fail "no </systemList> in $ESCFG"; return 1; }

    awk '
    /<\/systemList>/ {
        print "\t<system>"
        print "\t\t<fullname>Adobe Flash Player</fullname>"
        print "\t\t<name>flash</name>"
        print "\t\t<manufacturer>Macromedia</manufacturer>"
        print "\t\t<release>1996</release>"
        print "\t\t<hardware>computer</hardware>"
        print "\t\t<path>/storage/roms/flash</path>"
        print "\t\t<extension>.swf .SWF</extension>"
        print "\t\t<command>emuelecRunEmu.sh %ROM% -P%SYSTEM% --core=%CORE% --emulator=%EMULATOR% --controllers=\"%CONTROLLERSCONFIG%\"</command>"
        print "\t\t<platform>flash</platform>"
        print "\t\t<theme>flash</theme>"
        print "\t\t<emulators>"
        print "\t\t\t<emulator name=\"ruffle\">"
        print "\t\t\t\t<cores>"
        print "\t\t\t\t\t<core default=\"true\">ruffle</core>"
        print "\t\t\t\t</cores>"
        print "\t\t\t</emulator>"
        print "\t\t</emulators>"
        print "\t</system>"
    }
    { print }
    ' "$ESCFG" > "$ESCFG.tmp" && mv "$ESCFG.tmp" "$ESCFG" || { fail "es_systems.cfg update failed"; return 1; }
}

ruffle_browser_option() {
    local GL="$SCRIPTS/gamelist.xml"
    [[ -d "$SCRIPTS" ]] || return 0
    [[ -f "$GL" ]] && grep -q "qtwebbrowser.sh" "$GL" && return 0

    text_viewer -y -w -t "Add Qt Web Browser?" -f 24 -m "The Flash player is built on a full Qt Web Browser.\n\nDo you also want to add the browser itself to the Ports list, so you can use it for regular web browsing?\n\n(Adds an entry to the ports_scripts gamelist)"
    [[ $? == 21 ]] || return 0

    if ruffle_add_browser; then
        text_viewer -w -t "Qt Web Browser added" -f 24 -m "\nThe Qt Web Browser will show up in the Ports list after restarting Emulationstation."
    else
        text_viewer -e -w -t "Qt Web Browser FAILED" -f 24 -m "Could not update ${GL}.\n\nCheck ${LOG} for details."
    fi
}

ruffle_add_browser() {
    local GL="$SCRIPTS/gamelist.xml"
    echo ">> Adding Qt Web Browser to ports gamelist..." | tee -a "$LOG"
    if [[ -f "$GL" ]]; then
        cp "$GL" "$GL.bak.$(date +%Y%m%d%H%M%S)" || { fail "gamelist backup failed"; return 1; }
    else
        printf '<?xml version="1.0"?>\n<gameList>\n</gameList>\n' > "$GL"
    fi
    grep -q "</gameList>" "$GL" || { fail "no </gameList> in $GL"; return 1; }

    awk '
    /<\/gameList>/ {
        print "\t<game>"
        print "\t\t<path>./qtwebbrowser.sh</path>"
        print "\t\t<name>Qt Web Browser</name>"
        print "\t\t<desc>Full web browser (Qt WebEngine / Chromium) by Snowram. Browse with the gamepad: left stick moves the mouse, A clicks, B is Escape, Start is Enter. An on-screen keyboard opens for text input.</desc>"
        print "\t\t<image>/storage/roms/ports/qtwebbrowser/cover.jpg</image>"
        print "\t</game>"
    }
    { print }
    ' "$GL" > "$GL.tmp" && mv "$GL.tmp" "$GL" || { fail "gamelist update failed"; return 1; }
}

ruffle_confirm