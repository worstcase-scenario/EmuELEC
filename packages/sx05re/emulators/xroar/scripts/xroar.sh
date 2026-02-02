#!/bin/bash
# XRoar wrapper + per-game gptokeyb override
# Base dir: /storage/.config/emuelec/configs/xroar/gptk
# Default:  xroar.gptk
# Per-game: "<ROM basename>.gptk"  (e.g. "Chuckie Egg Plus (1983)(Burgin, Paul).gptk")

. /etc/profile

ROM="$1"

ASSETDIR="/usr/config/emuelec/configs/xroar"
export LD_LIBRARY_PATH="${ASSETDIR}/libs.aarch64:${LD_LIBRARY_PATH}"

case "$ROM" in
  */dragon32/*) MACHINE="dragon32" ;;
  */dragon64/*) MACHINE="dragon64" ;;
  */coco/*)     MACHINE="coco" ;;
  */coco3/*)    MACHINE="coco3" ;;
  */mc10/*)     MACHINE="mc10" ;;
  *)            MACHINE="dragon64" ;;
esac

GPTK_DIR="/storage/.config/emuelec/configs/xroar/gptk"
BASE="$(basename "$ROM")"
CFG="${GPTK_DIR}/${BASE%.*}.gptk"
[ -f "$CFG" ] || CFG="${GPTK_DIR}/xroar.gptk"

PID=""
trap '[ -n "$PID" ] && kill "$PID" 2>/dev/null' EXIT INT TERM
[ -f "$CFG" ] && gptokeyb -k "xroar.aarch64" -c "$CFG" & PID=$! && sleep 0.2

/usr/bin/xroar.aarch64 -fs -rompath /storage/roms/bios \
  -default-machine "$MACHINE" \
  -run "$ROM"
