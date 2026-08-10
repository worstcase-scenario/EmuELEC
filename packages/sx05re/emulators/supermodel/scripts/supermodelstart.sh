#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

. /etc/profile

CONF="/storage/.config/supermodel"

# First run: seed the writable config from the read-only image copy
if [ ! -d "${CONF}/Config" ]; then
  mkdir -p "${CONF}"
  cp -r /usr/config/supermodel/. "${CONF}/"
fi
mkdir -p "${CONF}/NVRAM" "${CONF}/Saves"

# SDL needs to be pointed at gl4es explicitly
export SDL_VIDEO_GL_DRIVER="/usr/lib/libGL.so.1"
export LIBGL_GLXRECYCLE=0

# Supermodel resolves Config/, NVRAM/ and Saves/ relative to the working directory
cd "${CONF}"

exec /usr/bin/supermodel "${1}" -fullscreen -res=1920,1080 -legacy3d -no-throttle