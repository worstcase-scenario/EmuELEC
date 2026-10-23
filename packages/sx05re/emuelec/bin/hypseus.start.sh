#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2021-present Shanti Gilbert (https://github.com/shantigilbert)

dir="${1%/}"
name=${dir##*/}
name=${name%.*}
config="/storage/.config/emuelec/configs/hypseus"
configfile="${config}/hypinput.ini"

if [[ ! -f "${config}/ee_updated" ]]; then
    cp "/usr/config/emuelec/configs/hypseus/hypinput_gamepad.ini" "${configfile}"
fi
touch "${config}/ee_updated"

if [[ -f "${dir}/${name}.commands" ]]; then
    params=$(<"${dir}/${name}.commands")
fi

# Not all gamepads use a trigger.
sed -i 's|AXIS_TRIGGER_RIGHT|BUTTON_X AXIS_TRIGGER_RIGHT|' ${configfile}

cd "${config}"

# Match the window to the current display mode, otherwise -fullscreen
# requests a 640x480 mode switch that the HDMI driver may reject.
res=""
vsize=$(cat /sys/class/graphics/fb0/virtual_size 2>/dev/null)
if [[ -n "${vsize}" ]]; then
    res="-x ${vsize%,*} -y $(( ${vsize#*,} / 2 ))"
fi

# -useoverlaysb is only valid for lair/ace/tq since hypseus 2.12,
# any other game type will hard-fail on this argument
sboverlay=""
case "${name}" in
    lair|ace|tq)
        sboverlay="-useoverlaysb 2"
        ;;
esac

# Load bezel from the game dir if present (both naming conventions)
bezel=""
if [[ -f "${dir}/bezel_${name}.png" ]]; then
    bezel="-bezeldir ${dir} -bezel bezel_${name}.png"
elif [[ -f "${dir}/${name}.png" ]]; then
    bezel="-bezeldir ${dir} -bezel ${name}.png"
fi

if [[ -f "${dir}/${name}.zip" ]]; then
    hypseus singe vldp -gamepad -manymouse -framefile "${dir}/${name}.txt" -zlua "${dir}/${name}.zip" -fullscreen ${res} ${bezel} ${params}
elif [[ -f "${dir}/${name}.singe" ]]; then
    hypseus singe vldp -gamepad -manymouse -framefile "${dir}/${name}.txt" -script "${dir}/${name}.singe" -fullscreen ${res} ${bezel} ${params}
else
    hypseus "${name}" vldp -gamepad -manymouse -framefile "${dir}/${name}.txt" -fullscreen ${res} ${sboverlay} ${params}
fi

ret=$?

if [[ ${ret} -eq 143 ]]; then
    exit 0
fi
exit ${ret}
