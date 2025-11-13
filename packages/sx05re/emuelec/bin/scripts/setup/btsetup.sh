#!/bin/bash
# ES Bluetooth setup (audio devices only) with Yes/Exit selection
set -euo pipefail
. /etc/profile

LOG="/tmp/btsetup.log"
ASOUND_RUNTIME="/run/asound.conf"
. "$(dirname "$0")/btaudio-lib.sh"

print_usage() {
  cat <<'EOF'
Usage: btsetup.sh

Interactive Bluetooth audio pairing tool.  Launch it from
EmulationStation: Main Menu -> Network & Services -> Bluetooth Audio Setup
or start manually over SSH with the command above.

Workflow
  1. Put the headset/speaker in pairing mode.
  2. Run btsetup.sh and press YES to scan (10 seconds).
  3. Pick the device, confirm the connection, and it becomes the
     default audio sink for EmulationStation and all emulators.

The last successful device is stored in /storage/.config/btaudio.last
so btconnect.sh can reconnect without re-pairing.
EOF
}

ee_console enable
cleanup() {
  ee_console disable
  rm -f /tmp/display
  [ -n "${BTCTL_PID:-}" ] && kill "$BTCTL_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  print_usage
  exit 0
fi

ask_yes() {
  text_viewer -y -w -t "$1" -f 24 -m "$2"
  rc=$?
  case "$rc" in
    21)   # A button
      return 0   # Yes
      ;;
    0)    # B button
      return 1   # No/Exit
      ;;
    *)
      return 1   # any other keys treated as No
      ;;
  esac
}

# Persistent bluetoothctl session for stable pairing
coproc BTCTL { bluetoothctl >>"$LOG" 2>&1; }
BTFD="${BTCTL[1]}"     # write fd

bt() { printf '%s\n' "$*" >&"$BTFD"; }

bt_init() {
  bt "power on"
  bt "pairable on"
  bt "agent NoInputNoOutput"
  bt "default-agent"
}

scan_start() { bt "scan on"; }
scan_stop()  { bt "scan off"; }

scan_audio_devices() {
  scan_start; sleep 10
  bluetoothctl devices \
    | awk '/^Device/ { mac=$2; $1=$2=""; sub(/^ /,""); print mac "|" $0 }' \
    | while IFS='|' read -r mac name; do
        [ -z "$mac" ] && continue
        is_audio_mac "$mac" && echo "${mac}|${name}"
      done
  scan_stop
}

pair_trust_connect() {
  local mac="$1"
  bluetoothctl info "$mac" >/dev/null 2>&1 || bt "remove $mac"

  if ! bluetoothctl info "$mac" 2>/dev/null | grep -q "Paired: yes"; then
    bt "pair $mac"
    for i in {1..10}; do
      bluetoothctl info "$mac" 2>/dev/null | grep -q "Paired: yes" && break
      sleep 1
    done
  fi

  bt "trust $mac"
  scan_stop

  for i in {1..8}; do
    bt "connect $mac"
    bluetoothctl info "$mac" 2>/dev/null | grep -q "Connected: yes" && return 0
    sleep 2
  done

  # Fallback: re-pair
  bt "remove $mac"; sleep 1
  bt "pair $mac"; sleep 2
  bt "trust $mac"
  for i in {1..6}; do
    bt "connect $mac"
    bluetoothctl info "$mac" 2>/dev/null | grep -q "Connected: yes" && return 0
    sleep 2
  done

  return 1
}

main() {
  ensure_pulseaudio
  bt_init

  ask_yes "BLUETOOTH SETUP" \
    "Put the audio device in pairing mode, then press YES to start scan.\n\nBe patient until the scan is done, it takes some seconds.\n\n\n[Yes]=Scan         [No]=Exit" || return 0

  while true; do
    mapfile -t DEVLIST < <(scan_audio_devices)

    if [ ${#DEVLIST[@]} -eq 0 ]; then
      ask_yes "NO AUDIO DEVICES" \
        "Nothing found.\n\n[Yes]=Scan again   [No]=Exit" \
        && continue || return 1
    fi

    LAST_MAC=""

    for entry in "${DEVLIST[@]}"; do
      mac="${entry%%|*}"
      name="${entry#*|}"

      if ask_yes "AUDIO DEVICE" \
          "Name: ${name}\nMAC: ${mac}\n\n[Yes]=Connect   [No]=Cancel"; then

        if pair_trust_connect "$mac"; then
          if SINK="$(set_bt_audio_sink "$mac")"; then
            echo "$mac" > /storage/.config/btaudio.last
            LAST_MAC="$mac"
            text_viewer -w -t "SUCCESS" -f 24 -m "Connected: ${name}\nSink: ${SINK}"
          else
            text_viewer -w -t "ERROR" -f 24 -m "Connected but no A2DP sink. See ${LOG}"
          fi
        else
          text_viewer -w -t "ERROR" -f 24 -m "Pair/connect failed."
        fi

        break   # stop after first attempt
      else
        break 2 # B button: abort entire scan cycle
      fi
    done

    ask_yes "CONNECTION COMPLETED" \
      "Scan again (YES) or exit to Emulationstation (NO)?\n" \
      && continue || break
  done

  
}

main
