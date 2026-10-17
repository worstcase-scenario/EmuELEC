#!/bin/bash

. /etc/profile

CONF_DIR="/storage/.config/ARMSX2"
DEF_DIR="/usr/config/emuelec/configs/armsx2"

# BIOS is shared with the libretro core
mkdir -p "${CONF_DIR}/inis"
[ -e "${CONF_DIR}/bios" ] || ln -s /storage/roms/bios/pcsx2/bios "${CONF_DIR}/bios"

# Full default INI on first start (a partial one would be reset by the emulator)
[ -f "${CONF_DIR}/inis/PCSX2.ini" ] || cp "${DEF_DIR}/PCSX2.ini" "${CONF_DIR}/inis/"

/usr/share/armsx2SA/armsx2-sdl "${1}"
