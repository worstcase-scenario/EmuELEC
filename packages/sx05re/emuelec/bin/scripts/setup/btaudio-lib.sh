#!/bin/bash
# Shared helpers for EmuELEC Bluetooth audio scripts

: "${ASOUND_RUNTIME:=/run/asound.conf}"
: "${ASOUND_PERSIST:=/storage/.config/asound.conf}"

ensure_pulseaudio() {
  if ! pgrep -f "pulseaudio.*--system" >/dev/null; then
    pulseaudio --system --disallow-exit --disable-shm --log-level=error &>>"${LOG:-/tmp/btaudio.log}" &
    sleep 2
  fi

  # Make sure bluetooth modules are available so a2dp sinks appear
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
