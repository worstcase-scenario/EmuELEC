#!/bin/bash
# Unified Bluetooth audio workflow for EmuELEC
set -euo pipefail
. /etc/profile

LOG="/tmp/btaudio.log"
ASOUND_RUNTIME="/run/asound.conf"
ASOUND_PERSIST="/storage/.config/asound.conf"

ensure_pulseaudio() {
  if ! pgrep -f "pulseaudio.*--system" >/dev/null; then
    pulseaudio --system --disallow-exit --disable-shm --log-level=error &>>"${LOG}" &
    sleep 2
  fi

  pactl list modules short | grep -q module-bluetooth-discover || \
    pactl load-module module-bluetooth-discover >/dev/null 2>&1 || true
}

configure_alsa_pulse() {
  mkdir -p "${ASOUND_RUNTIME%/*}" "${ASOUND_PERSIST%/*}"
  cat >"$ASOUND_RUNTIME" <<'CFG'
pcm.pulse {
  type pulse
  fallback "sysdefault"
}

ctl.pulse {
  type pulse
  fallback "sysdefault"
}

pcm.!default {
  type plug
  slave.pcm pulse
}

ctl.!default {
  type pulse
}
CFG

  ln -sf "$ASOUND_RUNTIME" "$ASOUND_PERSIST"

  if command -v set_audio >/dev/null 2>&1; then
    set_audio pulseaudio
  elif command -v emuelec-utils >/dev/null 2>&1; then
    emuelec-utils audio pulse
  fi
}

is_audio_mac() {
  local mac="$1" info
  info="$(bluetoothctl info "$mac" 2>/dev/null || true)"
  echo "$info" | grep -qiE 'Icon:\s*audio-' && return 0
  echo "$info" | grep -qiE 'UUID.*(A2DP|Audio Sink|Headset|Handsfree)' && return 0
  return 1
}

set_bt_audio_sink() {
  local BTMAC BTID CARD SINK

  BTMAC="$(echo "$1" | tr '[:lower:]' '[:upper:]')"

  ensure_pulseaudio

  BTID="${BTMAC//:/_}"
  CARD="bluez_card.$BTID"

  for _ in {1..12}; do pactl list cards short | grep -q "$CARD" && break; sleep 1; done
  pactl set-card-profile "$CARD" a2dp_sink >/dev/null 2>&1 || true

  SINK=""
  for _ in {1..12}; do
    SINK=$(pactl list short sinks | awk '{print $2}' | grep -E "bluez_sink\.${BTID}(\.a2dp_sink)?") || true
    [ -n "$SINK" ] && break; sleep 1
  done
  [ -n "$SINK" ] || return 1

  pactl set-default-sink "$SINK" >/dev/null 2>&1 || true
  pactl set-sink-mute   "$SINK" 0   >/dev/null 2>&1 || true
  pactl set-sink-volume "$SINK" 100% >/dev/null 2>&1 || true
  for id in $(pactl list short sink-inputs | awk '{print $1}'); do
    pactl move-sink-input "$id" "$SINK" >/dev/null 2>&1 || true
  done
  pactl list modules short | grep -q module-switch-on-connect || \
    pactl load-module module-switch-on-connect >/dev/null 2>&1 || true

  configure_alsa_pulse
  printf '%s\n' "$SINK"
}

MODE="scan"
TARGET_MAC=""
RESTART=0
ACTIVE_SINK=""

print_usage() {
  cat <<'USAGE'
Usage: btaudio.sh [options] [AA:BB:CC:DD:EE:FF]

Without arguments the script scans for Bluetooth audio devices, lets you
select one, then pairs/connects and routes all audio through PulseAudio.

Options:
  --scan           Force the interactive scan / pair workflow (default).
  --last           Connect to the MAC saved in /storage/.config/btaudio.last.
  --mac MAC        Connect directly to MAC (same as passing MAC positionally).
  --restart        Restart EmulationStation after a successful connect.
  --no-restart     Do not restart EmulationStation (default behaviour).
  -h, --help       Display this help.

Examples:
  btaudio.sh                    # scan, pair and route audio
  btaudio.sh --last --restart   # reconnect last sink and restart ES
  btaudio.sh AA:BB:CC:DD:EE:FF  # connect explicit MAC
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --scan)
      MODE="scan"
      shift
      ;;
    --last)
      MODE="last"
      shift
      ;;
    --mac)
      MODE="direct"
      TARGET_MAC="${2:-}"
      [ -n "$TARGET_MAC" ] || { echo "Missing MAC" >&2; exit 1; }
      shift 2
      ;;
    --restart)
      RESTART=1
      shift
      ;;
    --no-restart)
      RESTART=0
      shift
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      MODE="direct"
      TARGET_MAC="$1"
      shift
      ;;
  esac
done

ask_yes() {
  text_viewer -y -w -t "$1" -f 24 -m "$2"
  rc=$?
  rm -f /tmp/display
  case "$rc" in
    21)
      return 0
      ;;
    0)
      return 1
      ;;
    *)
      return 1
      ;;
  esac
}

overlay_msg() { ee_console disable; text_viewer -w -t "$1" -f 24 -m "$2"; rm -f /tmp/display; }
overlay_err() { ee_console disable; text_viewer -e -w -t "$1" -f 24 -m "$2"; rm -f /tmp/display; }

coproc_setup() {
  coproc BTCTL { bluetoothctl >>"$LOG" 2>&1; }
  BTFD="${BTCTL[1]}"
  BTCTL_PID="${COPROC_PID:-}"

  if [ -z "$BTCTL_PID" ]; then
    # BusyBox bash may clear COPROC_PID when job-control is disabled; fall back
    # to querying the coproc job directly so cleanup can still stop it.
    local job_info
    job_info="$(jobs -p %BTCTL 2>/dev/null || true)"
    BTCTL_PID="${job_info%%$'\n'*}"
  fi
}

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

connect_target() {
  local mac="$1"
  ensure_pulseaudio
  pair_trust_connect "$mac" || return 1
  local sink
  sink="$(set_bt_audio_sink "$mac")" || return 2
  ACTIVE_SINK="$sink"
  echo "$mac" > /storage/.config/btaudio.last
  return 0
}

interactive_scan() {
  ask_yes "BLUETOOTH AUDIO" \
    "Put the device in pairing mode, then press YES to scan.\n\nScanning lasts about 10 seconds.\n\n[Yes]=Scan     [No]=Exit" || return 0

  while true; do
    local DEVLIST=()
    mapfile -t DEVLIST < <(scan_audio_devices)

    if [ ${#DEVLIST[@]} -eq 0 ]; then
      ask_yes "NO DEVICES" "No Bluetooth audio device found.\n\n[Yes]=Scan again   [No]=Exit" && continue || return 1
    fi

    local entry mac name
    for entry in "${DEVLIST[@]}"; do
      mac="${entry%%|*}"
      name="${entry#*|}"
      if ask_yes "AUDIO DEVICE" "Name: ${name}\nMAC: ${mac}\n\n[Yes]=Connect   [No]=Skip"; then
        if connect_target "$mac"; then
          text_viewer -w -t "SUCCESS" -f 24 -m "Connected: ${name}\nSink: ${ACTIVE_SINK}"
          rm -f /tmp/display
        else
          text_viewer -w -t "ERROR" -f 24 -m "Connection failed. See ${LOG}"
          rm -f /tmp/display
        fi
        break
      fi
    done

    ask_yes "DONE?" "Scan again (YES) or exit (NO)?" && continue || break
  done
}

connect_from_mac() {
  local mac="$1"
  [ -n "$mac" ] || { overlay_err "MISSING" "Provide a MAC or use --scan."; return 1; }
  mac="$(echo "$mac" | tr '[:lower:]' '[:upper:]')"
  connect_target "$mac"
  rc=$?
  case $rc in
    0)
      overlay_msg "STATUS" "Active sink: ${ACTIVE_SINK}\nMAC: ${mac}"
      [ "$RESTART" -eq 1 ] && systemctl restart emustation
      ;;
    1)
      overlay_err "ERROR" "Failed to pair/connect ${mac}. See ${LOG}."
      ;;
    2)
      overlay_err "ERROR" "Connected but no A2DP sink detected."
      ;;
  esac
  return $rc
}

main() {
  ee_console enable
  coproc_setup
  cleanup() {
    ee_console disable
    rm -f /tmp/display
    [ -n "${BTCTL_PID:-}" ] && kill "$BTCTL_PID" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  bt_init

  case "$MODE" in
    scan)
      interactive_scan
      ;;
    last)
      if [ -z "$TARGET_MAC" ]; then
        [ -f /storage/.config/btaudio.last ] || { overlay_err "MISSING" "No previous Bluetooth audio device saved."; return 1; }
        TARGET_MAC="$(cat /storage/.config/btaudio.last)"
      fi
      connect_from_mac "$TARGET_MAC"
      ;;
    direct)
      connect_from_mac "$TARGET_MAC"
      ;;
  esac
}

main "$@"
