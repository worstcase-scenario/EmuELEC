#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2019-present SumavisionQ5 (https://github.com/SumavisionQ5)
# Modifications by Shanti Gilbert (https://github.com/shantigilbert)

# 12/07/2019 use mpv for all splash 
# 19/01/2020 use ffplay for all splash 
# 06/02/2020 move splash to roms folder and add global splash support

. /etc/profile

ACTION_TYPE="${1}"
PLATFORM="${2}"

SPLASHDIR="/storage/roms/splash"
RANDOMSPLASHDIR="${SPLASHDIR}/random"
PLATFORMSPLASHDIR="${SPLASHDIR}/${PLATFORM}"
DEFAULTSPLASH="/storage/.config/splash/splash-1080.png"
BLANKSPLASH="/storage/.config/splash/blank.png"
VIDEOSPLASH="/usr/config/splash/emuelec_intro_1080p.mp4"
RANDOMVIDEO="/storage/roms/splash/introvideos"
DURATION="5"

if [ -f "/storage/roms/splash/intro.mp4" ]; then
    VIDEOSPLASH="/storage/roms/splash/intro.mp4"
fi

PLATFORM=${PLATFORM,,}
PLAYER="ffplay"

MODE=`get_resolution`

# Choose random PNG image
get_random_splash() {
    local dir="$1"
    shopt -s nullglob
    local files=("${dir}"/*.png)
    if [[ ${#files[@]} -gt 0 ]]; then
        echo "${files[RANDOM % ${#files[@]}]}"
    else
        echo ""
    fi
}
# Choose random mp4 file
get_random_video() {
    local dir="$1"
    shopt -s nullglob
    local files=("${dir}"/*.mp4)
    if [[ ${#files[@]} -gt 0 ]]; then
        echo "${files[RANDOM % ${#files[@]}]}"
    else
        echo ""
    fi
}

if [ "${ACTION_TYPE}" == "intro" ]; then
    SPLASH=${DEFAULTSPLASH}
    if [[ "${MODE}" == *"x"* ]]; then
        SPLASH="/storage/.config/splash/splash-std.png"
    fi
elif [ "${ACTION_TYPE}" == "exit" ]; then
    EXITVIDEO="/storage/roms/splash/exitvideo.mp4"
    EXITSPLASH="/storage/roms/splash/exitsplash.png"

    if [[ $(get_ee_setting "ee_exitvideo.enabled") == "1" ]] && [[ -f "${EXITVIDEO}" ]]; then
        SPLASH="${EXITVIDEO}"
        VIDEO=1
    elif [[ $(get_ee_setting "ee_exitsplashimage.enabled") == "1" ]] && [[ -f "${EXITSPLASH}" ]]; then
        SPLASH="${EXITSPLASH}"
        VIDEO=0
    else
        SPLASH=${DEFAULTSPLASH}
        if [[ "${MODE}" == *"x"* ]]; then
            SPLASH="/storage/.config/splash/splash-std.png"
        fi
        VIDEO=0
    fi
elif [ "${ACTION_TYPE}" == "blank" ]; then
    SPLASH=${BLANKSPLASH}
elif [ "${ACTION_TYPE}" == "gameloading" ]; then
    GAMELOADINGSPLASH="/storage/.config/splash/loading-game.png"
    GAMELOADINGVIDEO="/storage/roms/splash/${PLATFORM}/launching.mp4"
    GLOBALGAMELOADINGVIDEO="/storage/roms/splash/launching.mp4"
    GLOBALGAMELOADINGIMAGE="/storage/roms/splash/launching.png"
	RANDOMSYSTEMVIDEO=$(get_random_video "/storage/roms/splash/${PLATFORM}")
	RANDOMVIDEOFILE=$(get_random_video "/storage/roms/splash/video")

    if [[ $(get_ee_setting "ee_systemloadingvideo.enabled") == "1" ]] && [[ -f "${GAMELOADINGVIDEO}" ]]; then
        SPLASH="${GAMELOADINGVIDEO}"
        VIDEO=1
    elif [[ $(get_ee_setting "ee_randomsystemvideo.enabled") == "1" ]] && [[ -n "${RANDOMSYSTEMVIDEO}" ]]; then
        SPLASH="${RANDOMSYSTEMVIDEO}"
        VIDEO=1
    elif [[ $(get_ee_setting "ee_randomloadingvideo.enabled") == "1" ]] && [[ -n "${RANDOMVIDEOFILE}" ]]; then
        SPLASH="${RANDOMVIDEOFILE}"
        VIDEO=1
    elif [[ $(get_ee_setting "ee_standardloadingvideo.enabled") == "1" ]] && [[ -f "${GLOBALGAMELOADINGVIDEO}" ]]; then
        SPLASH="${GLOBALGAMELOADINGVIDEO}"
        VIDEO=1
    elif [[ $(get_ee_setting "ee_randomimage.enabled") == "1" ]]; then
        SPLASH=$(get_random_splash "${RANDOMSPLASHDIR}")
    elif [[ $(get_ee_setting "ee_randomsystemimage.enabled") == "1" ]]; then
        SPLASH=$(get_random_splash "${PLATFORMSPLASHDIR}")
    elif [[ $(get_ee_setting "ee_systemsplashimage.enabled") == "1" ]]; then
        SPLASH="${PLATFORMSPLASHDIR}/launching.png"
    elif [[ $(get_ee_setting "ee_standardloadingimage.enabled") == "1" ]] && [[ -f "${GLOBALGAMELOADINGIMAGE}" ]]; then
        SPLASH="${GLOBALGAMELOADINGIMAGE}"
    elif [[ -f "${GLOBALGAMELOADINGVIDEO}" ]]; then
        SPLASH="${GLOBALGAMELOADINGVIDEO}"
        VIDEO=1
    fi

    if [[ -z "$SPLASH" ]]; then
        SPLASH="$GAMELOADINGSPLASH"
    fi
fi

SS_DEVICE=0
if [[ "${EE_DEVICE}" == "OdroidGoAdvance" ]] || [[ "${EE_DEVICE}" == "GameForce" ]]; then
  SS_DEVICE=1
  clear > /dev/console
  echo "Loading ..." > /dev/console
  PLAYER="mpv"
fi

declare -a RES=( ${MODE} )
SIZE=" -x ${RES[0]} -y ${RES[1]}"

# Fix: Set VIDEO only if not already set (especially for gameloading)
if [[ "${ACTION_TYPE}" == "intro" ]]; then
    VIDEO=$(get_ee_setting ee_bootvideo.enabled)
elif [[ -z "$VIDEO" ]]; then
    VIDEO=0
fi


if [[ ${VIDEO} != "1" ]] && [[ -f "/storage/.config/emuelec/configs/novideo" ]]; then
    if [ "${SS_DEVICE}" == 1 ]; then
        ${PLAYER} "${SPLASH}" > /dev/null 2>&1
    else
        ${PLAYER} -fs -autoexit ${SIZE} "${SPLASH}" > /dev/null 2>&1
    fi
else
    if [[ "${ACTION_TYPE}" == "intro" ]]; then
        RND=$(get_ee_setting "ee_randombootvideo.enabled" == "1")
        if [ "${RND}" == 1 ]; then
            SPLASH=$(ls ${RANDOMVIDEO}/*.mp4 | sort -R | tail -1)
            [[ -z "${SPLASH}" ]] && SPLASH="${VIDEOSPLASH}"
        else
            SPLASH="${VIDEOSPLASH}"
        fi
    fi

    set_audio alsa
    if [ ${SS_DEVICE} -eq 1 ]; then
        ${PLAYER} "${SPLASH}" > /dev/null 2>&1
    else
        ${PLAYER} -fs -autoexit ${SIZE} "${SPLASH}" > /dev/null 2>&1
    fi

    # Nur bei intro novideo setzen
    if [[ "${ACTION_TYPE}" == "intro" ]]; then
        touch "/storage/.config/emuelec/configs/novideo"
    fi
fi

fi

SPLASHTIME=$(get_ee_setting ee_splash.delay)
[ ! -z "${SPLASHTIME}" ] && sleep ${SPLASHTIME}
