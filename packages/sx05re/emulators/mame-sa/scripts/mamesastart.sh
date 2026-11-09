#!/bin/sh
# MAME standalone launcher: mamesastart.sh <rom> [gles]

CONF=/storage/.config/emuelec/configs/mame-sa
SHARE=/usr/share/mame
ROM="$1"

if [ "$2" = "gles" ]; then
  VIDEO="-video accel -renderdriver opengles2"
else
  VIDEO="-video bgfx -bgfx_backend vulkan -bgfx_path $SHARE/bgfx -switchres -resolution 1280x720@60"
fi

mkdir -p "$CONF"
cd "$CONF" || exit 1

export SDL_VIDEODRIVER=kmsdrm
exec /usr/bin/mame-sa "$(basename "${ROM%.*}")" \
  -rompath "$(dirname "$ROM")" \
  $VIDEO \
  -pluginspath "$SHARE/plugins" -languagepath "$SHARE/language" \
  -hashpath "$SHARE/hash"
