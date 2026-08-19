#!/bin/bash
# dreammstart.sh - DREAMM launcher for EmuELEC
#
# Usage:
#   dreammstart.sh /storage/roms/dreamm/monkey1          -> -run    (game directory)
#   dreammstart.sh /storage/roms/dreamm/monkey1.dreamm   -> -launch (.dreamm file)

. /etc/profile

export PATH="/emuelec/bin:$PATH"
export LD_PRELOAD="/emuelec/bin/dreamm_cursor.so"
export DREAMM_CURSOR_SCALE="${DREAMM_CURSOR_SCALE:-3}"
export LIBGL_NOTEST=1
export SDL_VIDEODRIVER=mali

DREAMM_BIN="/emuelec/bin/dreamm"
LOGFILE="/emuelec/logs/dreamm.log"
GAME="$1"

mkdir -p "$(dirname "$LOGFILE")"

if [ -z "$GAME" ]; then
    echo "Usage: $0 <game-directory|file.dreamm>" | tee -a "$LOGFILE"
    exit 1
fi

if [ ! -e "$GAME" ]; then
    echo "ERROR: path not found: $GAME" | tee -a "$LOGFILE"
    exit 1
fi

if [ -d "$GAME" ]; then
    MODE="-run"
else
    MODE="-launch"
fi

killall -STOP emulationstation 2>/dev/null

cleanup() {
    killall -CONT emulationstation 2>/dev/null
}
trap cleanup EXIT INT TERM

cd "$(dirname "$DREAMM_BIN")" || exit 1

{
    echo "=== $(date) ==="
    echo "MODE: $MODE"
    echo "GAME: $GAME"
    "$DREAMM_BIN" $MODE "$GAME" -sdl -fullscreen -nowait
} >> "$LOGFILE" 2>&1

exit 0