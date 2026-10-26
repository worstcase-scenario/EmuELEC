#!/bin/bash

. /etc/profile

# gptokeyb (kill hotkey) sends Esc for Select, which is sm2-emu's exit key:
# unbind it, quitting stays on Guide + Start and the EmuELEC hotkey
INI="/storage/.config/sm2-emu/sm2-emu.ini"
mkdir -p "${INI%/*}"
[ -f "${INI}" ] || echo "key_exit =" > "${INI}"
sed -i 's/^key_exit = Escape$/key_exit =/' "${INI}"

# Mali output has alpha < 1 -> make osd0 opaque (2 = None), restore after
modetest -M meson -w 31:"pixel blend mode":2 >/dev/null 2>&1
/usr/share/sm2emuSA/sm2-emu --fullscreen --graphics-backend vulkan "${1}"
RC=$?
modetest -M meson -w 31:"pixel blend mode":0 >/dev/null 2>&1
exit $RC
