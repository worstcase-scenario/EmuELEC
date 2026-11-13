#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

. /etc/profile

export SDL_VIDEODRIVER=kmsdrm
export XDG_CONFIG_HOME=/storage/.config
export XDG_DATA_HOME=/storage/.config

gptokeyb azahar -c /emuelec/configs/gptokeyb/azahar.gptk &
azahar --fullscreen "${1}" > /emuelec/logs/azahar.log 2>&1
killall gptokeyb
