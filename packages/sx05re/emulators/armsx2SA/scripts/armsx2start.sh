#!/bin/bash

. /etc/profile

CONF_DIR="/storage/.config/ARMSX2"
DEF_DIR="/usr/config/emuelec/configs/armsx2"
BIOS_DIR="/storage/roms/bios/pcsx2/bios"

# BIOS is shared with the libretro core
mkdir -p "${CONF_DIR}/inis" "${BIOS_DIR}"
[ -L "${CONF_DIR}/bios" ] || ln -s "${BIOS_DIR}" "${CONF_DIR}/bios"

# Full default INI on first start (a partial one would be reset by the emulator)
[ -f "${CONF_DIR}/inis/PCSX2.ini" ] || cp "${DEF_DIR}/PCSX2.ini" "${CONF_DIR}/inis/"

# Find a PS2 BIOS (4 MB) in BIOS_DIR, else copy one from /storage/roms/bios
is_ps2bios() { [ -f "$1" ] && [ "$(wc -c < "$1")" -eq 4194304 ]; }
BIOS=""
for f in "${BIOS_DIR}"/*; do is_ps2bios "$f" && { BIOS="$f"; break; }; done
if [ -z "${BIOS}" ]; then
    for f in /storage/roms/bios/*; do
        is_ps2bios "$f" && { cp "$f" "${BIOS_DIR}/"; BIOS="$f"; break; }
    done
fi

# Set BIOS in INI if not configured
[ -n "${BIOS}" ] && sed -i "s|^BIOS =[[:space:]]*$|BIOS = ${BIOS##*/}|" "${CONF_DIR}/inis/PCSX2.ini"

# CUE sheets are not supported, pass the first BIN instead
ROM="${1}"
if [ "${ROM##*.}" = "cue" ]; then
    BIN=$(sed -n 's/^FILE "\(.*\)".*/\1/p' "${ROM}" | head -n1 | tr -d '\r')
    [ -n "${BIN}" ] && ROM="$(dirname "${ROM}")/${BIN}"
fi

/usr/share/armsx2SA/armsx2-sdl "${ROM}"
