#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2019-present Shanti Gilbert (https://github.com/shantigilbert)

# OpenBOR only works with Pak files, if you have an extracted game you will need to create a pak first.

OB=${2}
[[ -z ${OB} ]] && OB=OpenBOR

pakname=$(basename "${1}")
pakname="${pakname%.*}"

CONFIGDIR="/emuelec/configs/openbor"
PAKS="${CONFIGDIR}/Paks"
SAVES="${CONFIGDIR}/Saves"

# Make sure the folders exists
	mkdir -p "${PAKS}"
	mkdir -p "${SAVES}"

# make a symlink to the pak
    ln -sf "${1}" "${PAKS}"

# remove game symlink if exists
if [ -L "${SAVES}/${pakname}.cfg" ]; then
    rm "${SAVES}/${pakname}.cfg"
fi

# copy master.cfg to master game config if no file present
if [ ! -f "${SAVES}/${pakname}.cfg" ]; then
    if [ ${OB} = "OpenBORff" ]; then
         cp -f "${CONFIGDIR}/masterff.cfg" "${SAVES}/${pakname}_masterff.cfg"
    else
         cp -f "${CONFIGDIR}/master.cfg" "${SAVES}/${pakname}_master.cfg"
    fi
fi

# copy game config from game _master.cfg
if [ ${OB} = "OpenBORff" ]; then
     cp -f "${SAVES}/${pakname}_masterff.cfg" "${SAVES}/${pakname}.cfg"
else
     cp -f "${SAVES}/${pakname}_master.cfg" "${SAVES}/${pakname}.cfg"
fi

# Run OpenBOR in the config folder
    cd "${CONFIGDIR}"
	SDL_AUDIODRIVER=alsa ${OB}

# copy game config to _master.cfg
if [ ${OB} = "OpenBORff" ]; then
     cp -f "${SAVES}/${pakname}.cfg" "${SAVES}/${pakname}_masterff.cfg"
else
     cp -f "${SAVES}/${pakname}.cfg" "${SAVES}/${pakname}_master.cfg"
fi

# Clear PAKS folder to avoid getting the launcher on nex run
rm -rf ${PAKS}/*
