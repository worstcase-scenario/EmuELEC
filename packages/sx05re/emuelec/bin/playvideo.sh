#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2020-present Shanti Gilbert (https://github.com/shantigilbert)

# Source predefined functions and variables
. /etc/profile

clear > /dev/console
clear > /dev/tty1
clear > /dev/tty0

ee_console disable
set_video_controls

romdir="/storage/roms/"
PLAYER="${2}"

case ${PLAYER} in
    "ffplay")
        MODE=`get_resolution`
        declare -a RES=( ${MODE} )
        SIZE=" -x ${RES[0]} -y ${RES[1]}"
        player="ffplay -fs -autoexit -loglevel warning -hide_banner ${SIZE}"
    ;;
    "vlc")
        /usr/bin/vlc -I "dummy" --aout=alsa "${1}" vlc://quit < /dev/tty1 > /dev/null 2>&1
    ;;
    "mpv")
        player="mpv -fs --volume-max=200 --really-quiet --no-input-builtin-bindings"
    ;;
esac

cd /tmp

# Function to check if the file is in specific directories (TV or Music)
check_stream_type() {
    local file_path="${1}"
    if [[ "${file_path}" == /storage/roms/mplayer/tv/* ]]; then
        echo "tv"
    elif [[ "${file_path}" == /storage/roms/mplayer/music/* ]]; then
        echo "music"
    else
        echo "radio"
    fi
}

case ${1} in
    *.m3u)
        # Überprüfen, ob die .m3u-Datei im TV- oder Musikverzeichnis ist
        stream_type=$(check_stream_type "${1}")
        
        # Verzeichnis und Basisnamen der m3u-Datei abrufen
        dir_name=$(dirname "${1}")
        base_name=$(basename "${1}" .m3u)
        png_image="${dir_name}/${base_name}.png"
        
        if [ "${stream_type}" == "tv" ] || [ "${stream_type}" == "music" ]; then
            # Kein Bild für TV- oder Musikstreams
            mpv -fs --volume-max=200 --no-input-builtin-bindings --really-quiet --force-window=yes "${1}" > /dev/tty1 2>&1
        else
            # Radio-Stream mit Bild
            if [ -f "${png_image}" ]; then
                ${player} "${png_image}" &
                PLAYER_PID=$!
                sleep 2
                mpv -fs --volume-max=200 --no-input-builtin-bindings --really-quiet "${1}" > /dev/tty1 2>&1
                kill $PLAYER_PID 2>/dev/null
            else
                echo "Bilddatei nicht gefunden: ${png_image}. Stattdessen bigradio.mp4 starten."
                mpv --loop --fs --volume-max=200 --no-input-builtin-bindings --really-quiet --no-audio "/storage/roms/splash/bigradio.mp4" &
                VIDEO_PID=$!
                mpv -fs --volume-max=200 --no-input-builtin-bindings --really-quiet --force-window=no --no-video "${1}" > /dev/tty1 2>&1
                kill $VIDEO_PID 2>/dev/null
            fi
        fi
    ;;
    *)
        VIDEO_MODE=general
        IS_YOUTUBE=$(cat "${1}" 2>/dev/null | grep -E "^https://www.youtube.com/.*")
        [[ ! -z "${IS_YOUTUBE}" ]] && VIDEO_MODE=youtube
        
        IS_TWITCH=$(cat "${1}" 2>/dev/null | grep -E "^https://www.twitch.tv/.*")
        [[ ! -z "${IS_TWITCH}" ]] && VIDEO_MODE=twitch
        
        [[ "${1}" == *".ytb" ]] && VIDEO_MODE=youtube
        [[ "${1}" == *".twi" ]] && VIDEO_MODE=twitch
        
        case ${VIDEO_MODE} in
            youtube)
                ${player} "/storage/.config/splash/youtube-1080.png"
                youtube-dl --quiet --no-warnings -o - -a "${1}" | ${player} - > /dev/tty1 2>&1
            ;;
            twitch)
                ${player} "/storage/.config/splash/twitch-1080.png"
                youtube-dl --quiet --no-warnings -o - -a "${1}" | ${player} - > /dev/tty1 2>&1
            ;;
            general)
                ${player} "${1}" > /dev/tty1 2>&1
            ;;
        esac
    ;;
esac

clear > /dev/console
clear > /dev/tty1
clear > /dev/tty0

kill_video_controls