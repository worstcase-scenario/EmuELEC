#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
. /etc/profile
PROFILE="/storage/.config/ymir"
mkdir -p "${PROFILE}/roms/ipl"
# Ymir identifies the IPL by content, so link every common Saturn BIOS name
for f in saturn_bios.bin sega_101.bin mpr-17933.bin; do
  [ -e "/storage/roms/bios/${f}" ] && ln -sf "/storage/roms/bios/${f}" "${PROFILE}/roms/ipl/${f}"
done
ymir-sdl3 -p "${PROFILE}" -f "${1}"