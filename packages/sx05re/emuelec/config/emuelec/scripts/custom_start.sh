

#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2019-present Shanti Gilbert (https://github.com/shantigilbert)

# Source predefined functions and variables
. /etc/profile

# Place any scripts you need to run at boot on this file

case "${1}" in
"before")

# Any commands that you want to run before the frontend begins should go here

# # Der Prozessname, nach dem gesucht wird
# PROCESS_NAME="/usr/sbin/eventlircd -f --evmap=/etc/eventlircd.d --socket=/run/lirc/lircd"

# # Suche den Prozess und beende ihn, falls er läuft
# PID=$(pgrep -f "$PROCESS_NAME")
# if [ -n "$PID" ]; then
    # echo "Prozess gefunden mit PID: $PID. Beende den Prozess..."
    # kill $PID
    # echo "Prozess $PID wurde beendet."
# else
    # echo "Prozess '$PROCESS_NAME' wurde nicht gefunden."
# fi
        # Umbennen der Datei "gamelist.xml" in "ex_gamelist.xml"
        mv /storage/roms/ports_scripts/gamelist.xml /storage/roms/ports_scripts/ex_gamelist.xml
        # Kopieren der Datei "gamelist.xml" von "media" nach "ports_scripts"
        cp /storage/roms/ports_scripts/media/gamelist.xml /storage/roms/ports_scripts/

l
		
# example BT config, use only as a last resort
# Bluetooth, Make sure you change your BT MAC address, you need to do this by SSH the first time
# by running 

# hcitool scan
# bluetoothctl pair yourmac
# bluetoothctl trust yourmac 

# If you want to use bluetooth, uncomment every line after this one 

# BTMAC="E4:17:D8:8B:F1:80"
# (
# echo "agent on" | bluetoothctl
# echo "default-agent" | bluetoothctl
# echo "power on" | bluetoothctl
# echo "discoverable on" | bluetoothctl
# echo "pairable on" | bluetoothctl
# echo "scan on" | bluetoothctl
# echo "trust ${BTMAC}" | bluetoothctl
# echo "connect ${BTMAC}" | bluetoothctl
# )&

	exit 0
	;;
*)
# Any commands that you want to run after the frontend has started goes here



    exit 0
	;;
esac
## nothing was called so exit
/storage/roms/ports/librespot/librespot --name PORTMASTER --bitrate 320 --cache /storage/roms/ports/librespot/cache --device-type gameconsole --backend sdl &

exit 0
