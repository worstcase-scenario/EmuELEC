#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# set_armsx2_joy.sh - write [Pad1]-[Pad4] of PCSX2.ini for the connected
# controllers, in EmulationStation player order

. /etc/profile
source joy_common.sh "armsx2"

INI="/storage/.config/ARMSX2/inis/PCSX2.ini"
[ -f "${INI}" ] || exit 0

mapfile -t GUIDS < <(gamepad_info 2>/dev/null | grep -oE '^[0-9a-f]{32}' | head -n4)
ORDER=($(jc_get_order_indexes 4 "${GUIDS[@]}"))

# Face buttons per SDL layout (Cross = South); armsx2_swap_face=1 swaps South/East
# and West/North for pads whose EmuELEC mapping is Nintendo-style
if [ "$(get_ee_setting armsx2_swap_face)" = "1" ]; then
    F=(FaceWest FaceSouth FaceEast FaceNorth)
else
    F=(FaceNorth FaceEast FaceSouth FaceWest)
fi

pad() {
    local s="SDL-$1"
    cat <<END
Type = DualShock2
Up = ${s}/DPadUp
Right = ${s}/DPadRight
Down = ${s}/DPadDown
Left = ${s}/DPadLeft
Triangle = ${s}/${F[0]}
Circle = ${s}/${F[1]}
Cross = ${s}/${F[2]}
Square = ${s}/${F[3]}
Select = ${s}/Back
Start = ${s}/Start
L1 = ${s}/LeftShoulder
R1 = ${s}/RightShoulder
L2 = ${s}/+LeftTrigger
R2 = ${s}/+RightTrigger
L3 = ${s}/LeftStick
R3 = ${s}/RightStick
LUp = ${s}/-LeftY
LRight = ${s}/+LeftX
LDown = ${s}/+LeftY
LLeft = ${s}/-LeftX
RUp = ${s}/-RightY
RRight = ${s}/+RightX
RDown = ${s}/+RightY
RLeft = ${s}/-RightX
END
}

TMP=$(mktemp)
# keep everything except the old [Pad1]-[Pad4] sections
awk '/^\[/{skip = /^\[Pad[1-4]\]$/} !skip' "${INI}" > "${TMP}"
for p in 0 1 2 3; do
    echo "[Pad$((p + 1))]" >> "${TMP}"
    dev=""
    for i in "${!GUIDS[@]}"; do
        [ -n "${GUIDS[$i]}" ] && [ "${ORDER[$i]}" = "${p}" ] && dev="${i}"
    done
    if [ -n "${dev}" ]; then pad "${dev}" >> "${TMP}"; else echo "Type = None" >> "${TMP}"; fi
    echo >> "${TMP}"
done
mv "${TMP}" "${INI}"
