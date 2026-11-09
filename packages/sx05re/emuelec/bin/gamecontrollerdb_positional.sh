#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

# One-time migration: SDL mappings written from ES used the Nintendo layout
# (a = east). Rewrite them positionally (a = south) from es_input.cfg.

ESINPUT="/storage/.config/emulationstation/es_input.cfg"
GCDB_DIR="/storage/.config/SDL-GameControllerDB"
GEN="/storage/.config/emulationstation/scripts/configscripts/gamecontrollerdb.sh"
DONE="${GCDB_DIR}/.positional"

[ -f "${DONE}" ] && exit 0
[ -f "${ESINPUT}" ] && [ -f "${GEN}" ] || exit 0

# one line per device: "D<tab>guid<tab>name", then "I<tab>name<tab>type<tab>id<tab>value" per input
awk '
/<inputConfig / && /type="joystick"/ {
  g = $0; sub(/.*deviceGUID="/, "", g); sub(/".*/, "", g)
  n = $0; sub(/.*deviceName="/, "", n); sub(/".*/, "", n)
  print "D\t" g "\t" n; dev = 1; next
}
/<\/inputConfig>/ { dev = 0; next }
dev && /<input / {
  split("name type id value", k, " ")
  out = "I"
  for (i = 1; i <= 4; i++) { v = $0; sub(".*" k[i] "=\"", "", v); sub(/".*/, "", v); out = out "\t" v }
  print out
}' "${ESINPUT}" > /tmp/gcdb_inputs

run_device() {
  [ -z "${DEVICE_GUID}" ] && return
  (
    . "${GEN}"
    onstart_gamecontrollerdb_joystick
    while IFS=$'\t' read -r name type id value; do
      map_gamecontrollerdb_joystick "${name}" "${type}" "${id}" "${value}"
    done <<< "${INPUTS}"
    onend_gamecontrollerdb_joystick
  )
}

INPUTS=""
while IFS=$'\t' read -r tag a b c d; do
  if [ "${tag}" = "D" ]; then
    run_device
    DEVICE_GUID="${a}"; DEVICE_NAME="${b}"; INPUTS=""
    export DEVICE_GUID DEVICE_NAME
  else
    INPUTS+="${a}"$'\t'"${b}"$'\t'"${c}"$'\t'"${d}"$'\n'
  fi
done < /tmp/gcdb_inputs
run_device

rm -f /tmp/gcdb_inputs
touch "${DONE}"
