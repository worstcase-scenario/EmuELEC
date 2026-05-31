#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

. /etc/profile

ROM="$1"
ROMNAME="${ROM##*/}"; ROMBASE="${ROMNAME%.*}"

export LD_LIBRARY_PATH="/usr/config/emuelec/configs/openmsx/libs:${LD_LIBRARY_PATH}"
export OPENMSX_HOME="/storage/.openMSX"
export LIBGL_VSYNC=0
export LIBGL_NOINTOVLHACK=1

# BIOS symlink
mkdir -p /storage/.openMSX/share
[ ! -e /storage/.openMSX/share/systemroms ] && \
  ln -sf /storage/roms/bios/msx /storage/.openMSX/share/systemroms

# gptk
killall -9 gptokeyb 2>/dev/null
GPTK_DIR="/storage/.config/emuelec/configs/openmsx/gptk"
GPTK_LD="${GPTK_DIR}/openmsx-ld.gptk"
[ ! -f "${GPTK_LD}" ] && mkdir -p "${GPTK_DIR}" && \
  cp /usr/config/emuelec/configs/openmsx/gptk/openmsx-ld.gptk "${GPTK_LD}"
[ -f "${GPTK_DIR}/${ROMBASE}.gptk" ] && GPTK_CONFIG="${GPTK_DIR}/${ROMBASE}.gptk" || GPTK_CONFIG="${GPTK_LD}"
gptokeyb 1 openmsx-ld -c "${GPTK_CONFIG}" &
sleep 3

# Activate SUPERIMPOSE=1 shaders for laserdisc video
mount --bind /usr/share/shaders_laserdisc /usr/share/shaders

# Settings
[ ! -f "${OPENMSX_HOME}/share/settings.xml" ] && \
  INIT_CMD="set fullscreen on; set auto_enable_reverse off; set accuracy line; set resampler blip; set samples 2048; set frequency 44100; set sound_driver SDL" || \
  INIT_CMD="set fullscreen on"

/usr/bin/openmsx-ld \
  -command "${INIT_CMD}" \
  -machine Pioneer_PX-7 \
  -laserdisc "${ROM}" &
OPENMSX_PID=$!

# Hide ES splash screen
sleep 2
echo 1 > /sys/class/graphics/fb0/blank 2>/dev/null
sleep 0.1
echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null

wait $OPENMSX_PID
killall -9 gptokeyb 2>/dev/null
umount /usr/share/shaders 2>/dev/null