#!/bin/bash

# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025-present Team EmuELEC

# Commander X16 Emulator Start Script

SYSTEM_ROM="/usr/share/x16-emulator/rom.bin"
USER_ROM="/storage/roms/x16/rom.bin"
EMU_BIN="/usr/bin/x16emu"

if [ -f "${USER_ROM}" ]; then
    ROM="${USER_ROM}"
elif [ -f "${SYSTEM_ROM}" ]; then
    ROM="${SYSTEM_ROM}"
else
    echo "ERROR: No rom.bin found!"
    exit 1
fi

PARAMS="-rom ${ROM}"
PARAMS="${PARAMS} -fullscreen"
PARAMS="${PARAMS} -quality best"
PARAMS="${PARAMS} -scale 2"

PARAMS="${PARAMS} -joy1 -joy2 -joy3 -joy4"

if [ -n "$1" ]; then
    FILE="$1"
    EXT="${FILE##*.}"
    
    case "${EXT,,}" in
        prg)
            PARAMS="${PARAMS} -prg ${FILE} -run"
            ;;
        bas)
            PARAMS="${PARAMS} -bas ${FILE} -run"
            ;;
        img)
            PARAMS="${PARAMS} -sdcard ${FILE}"
            ;;
        crt)
            PARAMS="${PARAMS} -cart ${FILE}"
            ;;
    esac
fi

exec ${EMU_BIN} ${PARAMS}