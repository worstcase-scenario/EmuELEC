#!/bin/bash
# Bluetooth connect: ES overlays, audio devices only
set -euo pipefail
. /etc/profile

LOG="/tmp/btconnect.log"
ASOUND_RUNTIME="/run/asound.conf"
. "$(dirname "$0")/btaudio-lib.sh"

print_usage() {
  cat <<'EOF'
Usage: btconnect.sh [--no-restart] [AA:BB:CC:DD:EE:FF]

Connects to the last remembered Bluetooth audio device (or the MAC
supplied on the command line), forces A2DP, and redirects EmulationStation
plus all emulators through the Bluetooth sink.  Run from the EmulationStation
Tools -> Bluetooth quick connect entry or manually from an SSH session.

  --no-restart   Do not restart EmulationStation after a successful connect.
EOF
}

RESTART=1
[ "${NO_ES_RESTART:-}" = "1" ] && RESTART=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --no-restart)
      RESTART=0
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

overlay_yes() {
  ee_console disable
  text_viewer -y -w -t "$1" -f 24 -m "$2"
  rc=$?; rm -f /tmp/display
  [ "$rc" -eq 21 ] || [ "$rc" -eq 0 ]
}
overlay_msg() { ee_console disable; text_viewer -w -t "$1" -f 24 -m "$2"; rm -f /tmp/display; }
overlay_err() { ee_console disable; text_viewer -e -w -t "$1" -f 24 -m "$2"; rm -f /tmp/display; }

run_connect() {
  local MAC_IN="${1:-}"
  [ -z "$MAC_IN" ] && [ -f /storage/.config/btaudio.last ] && MAC_IN="$(cat /storage/.config/btaudio.last)"
  [ -z "$MAC_IN" ] && { overlay_err "MISSING" "Usage: btconnect.sh [--no-restart] AA:BB:CC:DD:EE:FF"; exit 1; }

  local BTMAC SINK
  BTMAC="$(echo "$MAC_IN" | tr '[:lower:]' '[:upper:]')"
  is_audio_mac "$BTMAC" || { overlay_err "CANCEL" "Not an audio device."; exit 2; }
  ensure_pulseaudio

  if ! bluetoothctl info "$BTMAC" 2>/dev/null | grep -q "Paired: yes"; then
    bluetoothctl power on >>"$LOG" 2>&1 || true
    bluetoothctl pairable on >>"$LOG" 2>&1 || true
    bluetoothctl pair  "$BTMAC" >>"$LOG" 2>&1 || true
    bluetoothctl trust "$BTMAC" >>"$LOG" 2>&1 || true
  else
    bluetoothctl trust "$BTMAC" >>"$LOG" 2>&1 || true
  fi

  local connected=0
  for i in {1..6}; do
    bluetoothctl connect "$BTMAC" >>"$LOG" 2>&1 || true
    bluetoothctl info "$BTMAC" 2>/dev/null | grep -q "Connected: yes" && { connected=1; break; }
    sleep 2
  done
  [ "$connected" -eq 1 ] || { overlay_err "ERROR" "Connect failed. See $LOG"; exit 1; }

  SINK="$(set_bt_audio_sink "$BTMAC")" || { overlay_err "ERROR" "No A2DP sink found."; exit 1; }

  echo "$BTMAC" > /storage/.config/btaudio.last
  overlay_msg "STATUS" "Active sink: $SINK\n"

  [ "$RESTART" -eq 1 ] && systemctl restart emustation
}

if overlay_yes "CONNECT LAST BLUETOOTH AUDIO DEVICE" "Audio devices only. A2DP enforced.\n\n\n[YES]=Continue and exit to Emulationstation\n\n\n[No]=Cancel"; then
  run_connect "${1:-}"
fi
