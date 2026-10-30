#!/bin/bash

. /etc/profile

# gptokeyb (kill hotkey) sends Esc for Select, which is sm2-emu's exit key:
# unbind it, quitting stays on Guide + Start and the EmuELEC hotkey
INI="/storage/.config/sm2-emu/sm2-emu.ini"
mkdir -p "${INI%/*}"
[ -f "${INI}" ] || echo "key_exit =" > "${INI}"
sed -i 's/^key_exit = Escape$/key_exit =/' "${INI}"

# ES writes its RetroPad/SNES names (A = right) into the SDL database, but SDL
# reads a/b/x/y by position (A = bottom). Swap them for the pads set up in ES,
# as duckstation and PPSSPP do in their own mappings.
DB="${SDL_GAMECONTROLLERCONFIG_FILE:-/storage/.config/SDL-GameControllerDB/gamecontrollerdb.txt}"
if [ -f "${DB}" ]; then
    cp "${DB}" /tmp/sm2emu_gamecontrollerdb.txt
    for GUID in $(grep -o 'deviceGUID="[0-9a-f]*"' /storage/.emulationstation/es_input.cfg 2>/dev/null | cut -d'"' -f2); do
        sed -i "/^${GUID},/{s/,a:/,_A:/;s/,b:/,a:/;s/,_A:/,b:/;s/,x:/,_X:/;s/,y:/,x:/;s/,_X:/,y:/}" /tmp/sm2emu_gamecontrollerdb.txt
    done
    export SDL_GAMECONTROLLERCONFIG_FILE=/tmp/sm2emu_gamecontrollerdb.txt
fi

# Mali output has alpha < 1 -> make osd0 opaque (2 = None), restore after
modetest -M meson -w 31:"pixel blend mode":2 >/dev/null 2>&1
/usr/share/sm2emuSA/sm2-emu --fullscreen --graphics-backend vulkan "${1}"
RC=$?
modetest -M meson -w 31:"pixel blend mode":0 >/dev/null 2>&1
exit $RC
