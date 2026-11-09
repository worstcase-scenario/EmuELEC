#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2020-present Shanti Gilbert (https://github.com/shantigilbert)

# Source predefined functions and variables
. /etc/profile

CONFIG_DIR="/storage/.config/ppsspp/PSP/SYSTEM"
CONFIG=${CONFIG_DIR}/controls.ini
CONFIG_TMP=/tmp/jc/ppsspp.tmp

source joy_common.sh "ppsspp" "fixed_order"

# PPSSPP reads pads through the SDL GameController API and turns the SDL
# button/axis names into fixed key codes (SDL/SDLJoystick.cpp), so the
# mapping does not depend on the raw button numbers of the pad.
# Keyboard code first, then the pad code.
declare -A PPSSPP_MAPPING=(
  [Up]="1-19,10-19"
  [Down]="1-20,10-20"
  [Left]="1-21,10-21"
  [Right]="1-22,10-22"
  [Circle]="1-54,10-190"   # SDL b (east)
  [Cross]="1-52,10-189"    # SDL a (south)
  [Triangle]="1-29,10-188" # SDL y (north)
  [Square]="1-47,10-191"   # SDL x (west)
  [L]="1-45,10-193"
  [R]="1-51,10-192"
  [Select]="1-66,10-196"
  [Start]="1-62,10-197"
  [An.Up]="1-37,10-4003"
  [An.Down]="1-39,10-4002"
  [An.Left]="1-38,10-4001"
  [An.Right]="1-40,10-4000"
  [Pause]="1-111,10-4"     # SDL guide (Xbox/PS/Home button)
)

# Keeps the user's hotkeys and removes the old mapping.
clean_pad() {
  [[ "${1}" != "1" ]] && return
  [[ -f "${CONFIG_TMP}" ]] && rm "${CONFIG_TMP}"
  [[ ! -f "${CONFIG}" ]] && return
  local KEY
  for KEY in "Analog limiter" "RapidFire" "Unthrottle" "SpeedToggle" "Pause (no menu)" "Rewind" "Toggle Debugger"; do
    grep -m 1 "^${KEY} =" ${CONFIG} >> ${CONFIG_TMP}
  done
  rm ${CONFIG}
}

# ${1} = Player Number
# ${5} = SDL mapping
set_pad() {
  [[ "${1}" != "1" ]] && return
  local GC_CONFIG="${5}"
  [[ -z ${GC_CONFIG} ]] && return

  local KEY
  for KEY in "${!PPSSPP_MAPPING[@]}"; do
    echo "${KEY} = ${PPSSPP_MAPPING[${KEY}]}" >> ${CONFIG_TMP}
  done

  echo "[ControlMapping]" > ${CONFIG}
  sort ${CONFIG_TMP} >> ${CONFIG}
  rm "${CONFIG_TMP}"
}

jc_get_players
