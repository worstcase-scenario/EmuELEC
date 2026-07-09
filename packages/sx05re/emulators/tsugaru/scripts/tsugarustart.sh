#!/bin/sh
# tsugarustart.sh - EmulationStation launcher for the Tsugaru FM Towns emulator
# Usage: tsugarustart.sh /full/path/to/game.cue
ROM="$1"
BIOS="/storage/roms/bios/fmtowns"
LOG="/emuelec/logs/tsugaru.log"
BIN="/usr/bin/tsugaru"
mkdir -p /emuelec/logs
exec >> "$LOG" 2>&1
echo "=== $(date) tsugaru launch: $ROM"
if [ ! -f "$BIOS/FMT_SYS.ROM" ]; then
    echo "ERROR: FM Towns BIOS not found in $BIOS"
    exit 1
fi
if [ ! -f "$ROM" ]; then
    echo "ERROR: ROM not found: $ROM"
    exit 1
fi
# --- media type by extension -------------------------------------------------
base="${ROM%.*}"
ext="$(echo "${ROM##*.}" | tr 'A-Z' 'a-z')"
case "$ext" in
    cue|iso|mds|ccd)  MEDIA="-CD" ;;
    d77|d88|hdm|xdf|bin) MEDIA="-FD0" ;;
    *)                MEDIA="-CD" ;;
esac
# --- per-game extra options: <rom>.opts (one line of extra CLI args) ---------
EXTRA=""
[ -f "${base}.opts" ] && EXTRA="$(head -1 "${base}.opts")"
# --- gameport autodetection ----------------------------------------------------
# Finds the first real gamepad on /dev/input/js0..js3 and picks the mode from
# its axis capabilities: hat/dpad present -> PHYSx, analog stick only -> ANAx.
# Global override: /emuelec/configs/tsugaru.gameport (e.g. "PHYS0CAPCOM").
JS_SYS_BASE="${JS_SYS_BASE:-/sys/class/input}"

detect_gameport() {
    for jsidx in 0 1 2 3; do
        [ -e "/dev/input/js$jsidx" ] || continue
        abs_file="$JS_SYS_BASE/js$jsidx/device/capabilities/abs"
        [ -f "$abs_file" ] || continue
        abs_low="$(awk '{print $NF}' "$abs_file")"
        abs_val=$((0x$abs_low)) 2>/dev/null || abs_val=0
        if [ $((abs_val & 196608)) -ne 0 ]; then    # 0x30000: ABS_HAT0X/Y
            echo "PHYS$jsidx"; return
        elif [ $((abs_val & 3)) -eq 3 ]; then       # ABS_X + ABS_Y
            echo "ANA$jsidx"; return
        fi
    done
    echo "ANA0"   # fallback
}

if [ -f /emuelec/configs/tsugaru.gameport ]; then
    GAMEPORT0="$(head -1 /emuelec/configs/tsugaru.gameport | tr -d ' ')"
else
    GAMEPORT0="$(detect_gameport)"
fi
PAD="$(echo "$GAMEPORT0" | tr -cd '0-9' | cut -c1)"
[ -n "$PAD" ] || PAD=0
echo "gameport: $GAMEPORT0 (pad index $PAD)"

# --- gptk support: pure-shell translation to native -VIRTKEY/-GAMEPORT --------
# Button numbers follow the common Xbox-style joydev layout; adjust here if a
# pad numbers its buttons differently (check with: jstest /dev/input/js0).
BTN_A=0;  BTN_B=1;  BTN_X=2;  BTN_Y=3
BTN_L1=4; BTN_R1=5; BTN_SELECT=6; BTN_START=7
BTN_L2=8; BTN_R2=9; BTN_L3=10; BTN_R3=11
BTN_DUP=12; BTN_DDOWN=13; BTN_DLEFT=14; BTN_DRIGHT=15

gptk_key() {  # gptk key value -> TOWNS_JISKEY suffix ('' = unsupported)
    case "$1" in
        enter|return) echo RETURN ;;   esc|escape) echo ESC ;;
        space) echo SPACE ;;           backspace) echo BACKSPACE ;;
        tab) echo TAB ;;               up) echo UP ;;
        down) echo DOWN ;;             left) echo LEFT ;;
        right) echo RIGHT ;;           leftshift|rightshift|shift) echo SHIFT ;;
        leftctrl|rightctrl|ctrl) echo CTRL ;;
        home) echo HOME ;;             insert) echo INSERT ;;
        delete) echo DELETE ;;         pageup) echo PREV ;;
        pagedown) echo NEXT ;;
        [a-z]) echo "$1" | tr 'a-z' 'A-Z' ;;
        [0-9]) echo "$1" ;;
        f[1-9]) echo "PF0${1#f}" ;;
        f1[0-9]|f20) echo "PF${1#f}" ;;
        *) echo "" ;;
    esac
}

gptk_btn() {  # gptk button name -> js button number ('' = unsupported)
    case "$1" in
        a) echo $BTN_A ;;       b) echo $BTN_B ;;
        x) echo $BTN_X ;;       y) echo $BTN_Y ;;
        l1) echo $BTN_L1 ;;     r1) echo $BTN_R1 ;;
        l2) echo $BTN_L2 ;;     r2) echo $BTN_R2 ;;
        l3) echo $BTN_L3 ;;     r3) echo $BTN_R3 ;;
        select|back) echo $BTN_SELECT ;;
        start) echo $BTN_START ;;
        up) echo $BTN_DUP ;;    down) echo $BTN_DDOWN ;;
        left) echo $BTN_DLEFT ;; right) echo $BTN_DRIGHT ;;
        *) echo "" ;;
    esac
}

GPTK="${base}.gptk"                                    # per-game override
[ -f "$GPTK" ] || GPTK="/emuelec/configs/tsugaru.gptk" # global user config
GPTK_ARGS=""
GPTK_MOUSE=0
if [ -f "$GPTK" ]; then
    while IFS= read -r gline || [ -n "$gline" ]; do
        gline="${gline%%#*}"
        case "$gline" in *=*) ;; *) continue ;; esac
        gname="$(echo "${gline%%=*}" | tr -d ' \t' | tr 'A-Z' 'a-z')"
        gval="$(echo "${gline#*=}"  | tr -d ' \t' | tr 'A-Z' 'a-z')"
        case "$gval" in
            mouse_movement_*)
                [ "$GPTK_MOUSE" = 0 ] && GPTK_ARGS="$GPTK_ARGS -GAMEPORT1 ANA${PAD}MOUSE"
                GPTK_MOUSE=1; continue ;;
            mouse_left|mouse_right|mouse_middle) continue ;;
        esac
        gkey="$(gptk_key "$gval")"; gbtn="$(gptk_btn "$gname")"
        if [ -n "$gkey" ] && [ -n "$gbtn" ]; then
            GPTK_ARGS="$GPTK_ARGS -VIRTKEY TOWNS_JISKEY_$gkey $PAD $gbtn"
        else
            echo "gptk: Zeile uebersprungen: $gname = $gval"
        fi
    done < "$GPTK"
    echo "gptk: $GPTK ->$GPTK_ARGS"
fi
# --- run ----------------------------------------------------------------------
SDL_VIDEODRIVER=mali "$BIN" "$BIOS" \
    -FULLSCREEN -AUTOSCALE -CDSPEED 32 \
    -GAMEPORT0 "$GAMEPORT0" \
    $MEDIA "$ROM" $GPTK_ARGS $EXTRA < /dev/null
RC=$?
echo "=== tsugaru exited rc=$RC"
exit $RC