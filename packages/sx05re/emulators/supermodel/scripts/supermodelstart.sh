#!/bin/bash

CONF="/storage/.config/supermodel"

# first run: seed writable config from the read-only image copy
if [ ! -d "${CONF}/Config" ]; then
  mkdir -p "${CONF}"
  cp -r /usr/config/supermodel/. "${CONF}/"
fi
mkdir -p "${CONF}/NVRAM" "${CONF}/Saves"

export SDL_VIDEO_GL_DRIVER=/usr/lib/libGL.so.1

cd "${CONF}"
exec /usr/bin/supermodel "$1" -fullscreen -res=1920,1080