#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later

# Starts yabasanshiro-pirry, or with "vk" as 2nd argument its Vulkan build

. /etc/profile

BIN="yabasanshiro_pirry${2}"
CFG="/storage/roms/saturn/${BIN}"
mkdir -p "${CFG}"

ROMNAME=$(basename "${1}")
BIOS=""

# Gamepad Autoconfiguration
GAMEPAD=$(sdljoytest -skip_loop | grep "0 name" | sed "s|Joystick 0 name ||")
GAMEPADCONFIG=$(xmlstarlet sel -t -c "//inputList/inputConfig[@deviceName=${GAMEPAD}]" -n /storage/.emulationstation/es_input.cfg)

if [ ! -z "${GAMEPADCONFIG}" ]; then
    echo -e "<?xml version=\"1.0\"?>\n<inputList>\n${GAMEPADCONFIG}\n</inputList>" > "${CFG}/input.cfg"
fi

[ -e "${CFG}/input.cfg" ] || cp -f /emuelec/configs/yabasanshiro1_5/input.cfg "${CFG}/input.cfg"

HLEBIOS=$(get_ee_setting hlebios saturn "${ROMNAME}")

if [ "${HLEBIOS}" != 1 ]; then
    if [ -e "/storage/roms/bios/saturn_bios.bin" ]; then
        BIOS="-b /storage/roms/bios/saturn_bios.bin"
    else
        text_viewer -w -t "Notice! Yabasanshiro BIOS Missing!" -f 24 -m "/storage/roms/bios/saturn_bios.bin was not found!\n\nYabasanshiro will continue to load with HLE BIOS\n\nTo avoid this message please copy saturn_bios.bin with checksum af5828fdff51384f99b3c4926be27762 to /storage/roms/bios/\n\nOr select \"USE HLE BIOS\" on the emulator options"
    fi
fi

if [[ "$(get_ee_setting yabasanshiro_auto_gamepad)" == "1" ]]; then
  cp -f /storage/.emulationstation/es_input.cfg "${CFG}/input.cfg"
  set_yabasanshiro_joy1_5.sh "${CFG}"
fi

# Resolution from the ES game/system options; unset = the in-game menu setting
RES=""
case "$(get_ee_setting yaba_resolution saturn "${ROMNAME}")" in
  native) RES="-r 0" ;; 4x) RES="-r 1" ;; 2x) RES="-r 2" ;;
  original) RES="-r 3" ;; 720p) RES="-r 4" ;; 1080p) RES="-r 5" ;;
esac

# We use { } to avoid SIGUSR signal showing text and messing up with the error handling
{ ${BIN} ${RES} -i "${1}" ${BIOS}; } > /emuelec/logs/emuelec.log 2>&1
