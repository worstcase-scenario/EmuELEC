#!/bin/bash
# Minimal XRoar wrapper + per-game gptokeyb override
# Base dir: /storage/.config/emuelec/configs/xroar/gptk
# Default:  xroar.gptk
# Per-game: "<ROM basename>.gptk"  (e.g. "Chuckie Egg Plus (1983)(Burgin, Paul).gptk")

. /etc/profile

ROM="$1"

XROAR_BIN="/usr/bin/xroar.aarch64"
BIOSDIR="/storage/roms/bios"

GPTK_DIR="/storage/.config/emuelec/configs/xroar/gptk"
GPTK_DEFAULT="${GPTK_DIR}/xroar.gptk"

# Build per-game gptk filename from ROM basename (keep extension in ROM, replace with .gptk)
ROM_BASE="$(basename "$ROM")"
GAME_GPTK="${GPTK_DIR}/${ROM_BASE%.*}.gptk"

# Ensure uinput for gptokeyb
[ -e /dev/uinput ] || modprobe uinput 2>/dev/null || true

# Choose per-game gptk if present, else fallback to default
GPTK_CFG=""
if [ -f "${GAME_GPTK}" ]; then
  GPTK_CFG="${GAME_GPTK}"
elif [ -f "${GPTK_DEFAULT}" ]; then
  GPTK_CFG="${GPTK_DEFAULT}"
fi

# Start gptokeyb if we have a config
if [ -n "${GPTK_CFG}" ]; then
  gptokeyb -k "xroar.aarch64" -c "${GPTK_CFG}" &
  GPTK_PID=$!
  trap 'kill "${GPTK_PID}" 2>/dev/null' EXIT
fi

exec "${XROAR_BIN}" -fs -rompath "${BIOSDIR}" -run "${ROM}"