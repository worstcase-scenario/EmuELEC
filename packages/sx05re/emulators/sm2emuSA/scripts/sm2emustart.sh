#!/bin/bash

. /etc/profile

ROMBASE="$(basename "${1%.*}")"

# Copy default gptk to writable storage (gptokeyb opens config read/write)
GPTK_DIR="/storage/.config/emuelec/configs/sm2emuSA/gptk"
mkdir -p "${GPTK_DIR}"
[ -f "${GPTK_DIR}/sm2emuSA.gptk" ] || cp /usr/config/emuelec/configs/sm2emuSA/gptk/sm2emuSA.gptk "${GPTK_DIR}/"
GPTK_CONFIG="${GPTK_DIR}/sm2emuSA.gptk"
[ -f "${GPTK_DIR}/${ROMBASE}.gptk" ] && GPTK_CONFIG="${GPTK_DIR}/${ROMBASE}.gptk"

killall -9 gptokeyb 2>/dev/null
gptokeyb 1 sm2-emu -c "${GPTK_CONFIG}" &

# Mali output has alpha < 1 -> make osd0 opaque (2 = None), restore after
modetest -M meson -w 31:"pixel blend mode":2 >/dev/null 2>&1
/usr/share/sm2emuSA/sm2-emu --fullscreen --graphics-backend vulkan "${1}"
RC=$?
modetest -M meson -w 31:"pixel blend mode":0 >/dev/null 2>&1

killall -9 gptokeyb 2>/dev/null
exit $RC
