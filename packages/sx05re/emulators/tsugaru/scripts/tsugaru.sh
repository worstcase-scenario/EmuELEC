#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present worstcase_scenario (https://github.com/worstcase-scenario)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"
ROMBASE="${ROMNAME%.*}"

BIOSDIR="/storage/roms/bios/fmtowns"
CONFIGDIR="/storage/.config/emuelec/configs/tsugaru"
SYSCONFIGDIR="/usr/config/emuelec/configs/tsugaru"

mkdir -p "${CONFIGDIR}/gptk"
[ ! -f "${CONFIGDIR}/gptk/tsugaru.gptk" ] && \
    cp "${SYSCONFIGDIR}/gptk/tsugaru.gptk" "${CONFIGDIR}/gptk/tsugaru.gptk"

killall -9 gptokeyb 2>/dev/null

GPTK_CONFIG="${CONFIGDIR}/gptk/tsugaru.gptk"
[ -f "${CONFIGDIR}/gptk/${ROMBASE}.gptk" ] && \
    GPTK_CONFIG="${CONFIGDIR}/gptk/${ROMBASE}.gptk"

gptokeyb 1 tsugaru_cui -c "${GPTK_CONFIG}" &
sleep 1

echo 1 > /sys/class/graphics/fb0/osd_clear 2>/dev/null
fbfix 0

# SDL2 backend: fbdev for video, ALSA for audio
# gl4es LIBGL_FB=2 for FBO rendering without X11
export SDL_VIDEODRIVER=fbdev
export SDL_FBDEV=/dev/fb0
export SDL_AUDIODRIVER=alsa
export SDL_AUDIO_DEVICE_NAME=default
export LIBGL_FB=2

/usr/bin/tsugaru_cui "${BIOSDIR}" \
    -GAMEPORT0 KEY \
    -FULLSCREEN \
    -CD "${ROM}"

killall -9 gptokeyb 2>/dev/null
