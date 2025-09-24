#!/bin/sh
# robust Wiimote connect (pure sh)
set -u
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/emuelec/bin

log(){ printf '%s\n' "$*"; }

# Stop services and load modules
/usr/bin/systemctl stop eventlircd 2>/dev/null || true
modprobe uhid 2>/dev/null || true
modprobe hid-wiimote 2>/dev/null || true

# Prepare adapter
/usr/bin/bluetoothctl power on >/dev/null 2>&1 || true
/usr/bin/bluetoothctl pairable on >/dev/null 2>&1 || true
/usr/bin/bluetoothctl agent on >/dev/null 2>&1 || true
/usr/bin/bluetoothctl default-agent >/dev/null 2>&1 || true

log "Scanning. Hold 1+2 on the Wiimote"
scanout="$(
  /usr/bin/bluetoothctl --timeout 20 scan on 2>&1 || true
)"

# Show scan lines for verification
printf '%s\n' "$scanout" | grep -E '^(\[NEW\]|Device)' || true

# Extract MAC where name matches Nintendo/Wiimote/RVL-CNT
mac="$(
  printf '%s\n' "$scanout" |
  awk '/Device/ && tolower($0) ~ /(nintendo|wiimote|rvl-cnt)/ {
    for (i=1;i<=NF;i++) if ($i ~ /^[0-9A-F]{2}(:[0-9A-F]{2}){5}$/) { print $i; exit }
  }'
)"

if [ -z "${mac:-}" ]; then
  log "No Wiimote found."
  exit 1
fi

log "Target: $mac"
/usr/bin/bluetoothctl trust "$mac"   >/dev/null 2>&1 || true
/usr/bin/bluetoothctl connect "$mac" >/dev/null 2>&1 || true
sleep 2

if ! /usr/bin/bluetoothctl info "$mac" | grep -q "Connected: yes"; then
  /usr/bin/bluetoothctl pair "$mac"    >/dev/null 2>&1 || true
  sleep 1
  /usr/bin/bluetoothctl connect "$mac" >/dev/null 2>&1 || true
  sleep 1
fi

/usr/bin/bluetoothctl info "$mac" | sed -n '1,40p'

if /usr/bin/bluetoothctl info "$mac" | grep -q "Connected: yes"; then
  log "Wiimote connected."
  exit 0
else
  log "Connect failed."
  exit 1
fi
