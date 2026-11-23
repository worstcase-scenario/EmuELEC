#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later

. /etc/profile

PROFILE="/storage/.config/ymir"
mkdir -p "${PROFILE}/roms/ipl"
[ -e /storage/roms/bios/saturn_bios.bin ] && ln -sf /storage/roms/bios/saturn_bios.bin "${PROFILE}/roms/ipl/saturn_bios.bin"

ymir-sdl3 -p "${PROFILE}" -f "${1}"
