#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

. /etc/profile

export SDL_VIDEODRIVER=kmsdrm
export XDG_CONFIG_HOME=/storage/.config
export XDG_DATA_HOME=/storage/.config

# ES internal resolution, only for this start: the old value is restored on exit
INI=/storage/.config/azahar-emu/sdl2-config.ini
setres() { sed -i "/^\[Renderer\]/,/^\[/ s/^resolution_factor *=.*/resolution_factor = $1/" "${INI}"; }
OLDRES=$(sed -n "/^\[Renderer\]/,/^\[/ s/^resolution_factor *= *//p" "${INI}" 2>/dev/null)
[ -n "${EE_IRES}" ] && [ -f "${INI}" ] && setres "${EE_IRES}"
gptokeyb azahar -c /emuelec/configs/gptokeyb/azahar.gptk &
azahar --fullscreen "${1}" > /emuelec/logs/azahar.log 2>&1
[ -n "${EE_IRES}" ] && [ -f "${INI}" ] && setres "${OLDRES}"
killall gptokeyb
