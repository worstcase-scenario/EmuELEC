#!/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2019-present Shanti Gilbert (https://github.com/shantigilbert)
# Copyright (C) 2024-present Langerz82 (https://github.com/Langerz82)

# Source predefined functions and variables
. /etc/profile

arguments="$@"

# Configure dynamic splash handling before starting the splash
SPLASH_DYNAMIC_RAW=$(get_ee_setting ee_splash.dynamic_stop)
case "${SPLASH_DYNAMIC_RAW,,}" in
    1|true|yes|on|enabled)
        SPLASH_DYNAMIC="1"
        ;;
    *)
        SPLASH_DYNAMIC="0"
        ;;
esac

if [[ "${SPLASH_DYNAMIC}" == "1" ]]; then
    export EE_SPLASH_DYNAMIC="1"
    EE_SPLASH_PATTERN=$(get_ee_setting ee_splash.dynamic_stop_pattern)
    export EE_SPLASH_PATTERN
    EE_SPLASH_TIMEOUT=$(get_ee_setting ee_splash.dynamic_timeout)
    export EE_SPLASH_TIMEOUT
    export EE_SPLASH_STANDALONE="1"
else
    unset EE_SPLASH_DYNAMIC EE_SPLASH_PATTERN EE_SPLASH_TIMEOUT EE_SPLASH_STANDALONE
fi

# Extract the platform name from the arguments
PLATFORM="${arguments##*-P}"  # read from -P onwards
PLATFORM="${PLATFORM%% *}"  # until a space is found

ROMNAME="${1}"

init_game
emuelec-utils init_app_video "${PLATFORM}" "${ROMNAME}"

if [[ "${SPLASH_DYNAMIC}" == "1" ]]; then
    ee_splash_wrapper.sh "$@"
else
    "$@"
fi

emuelec-utils end_app_video
end_game