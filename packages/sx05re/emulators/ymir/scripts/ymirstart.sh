#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
. /etc/profile
PROFILE="/storage/.config/ymir"
CFG="${PROFILE}/Ymir.toml"
mkdir -p "${PROFILE}/roms/ipl"
# Ymir identifies the IPL by content, so link every common Saturn BIOS name
for f in saturn_bios.bin sega_101.bin mpr-17933.bin; do
  [ -e "/storage/roms/bios/${f}" ] && ln -sf "/storage/roms/bios/${f}" "${PROFILE}/roms/ipl/${f}"
done

# Ymir.toml is global and rewritten on exit: set every ES option on each start, Ymir default if unset
[ -f "${CFG}" ] || echo "ConfigVersion = 6" > "${CFG}"
ymir_set() { # section key value
  awk -v s="[$1]" -v k="$2" -v v="$3" '
    { t = $0; sub(/^[ \t]+/, "", t) }
    t ~ /^\[/ { if (sec && !done) { print k " = " v; done = 1 } sec = (t == s); if (sec) found = 1 }
    sec && $1 == k && $2 == "=" { if (!done) print k " = " v; done = 1; next }
    { print }
    END { if (!done) { if (!found) print "[" substr(s, 2); print k " = " v } }' "${CFG}" > "${CFG}.tmp" && mv "${CFG}.tmp" "${CFG}"
}
ee() { get_ee_setting "$1" saturn "${ROMNAME}"; }
ROMNAME="$(basename "${1}")"

case "$(ee ymir_fsres)" in
  720p) W=1280; H=720 ;; 1080p) W=1920; H=1080 ;; *) W=0; H=0 ;;
esac
if [ "${W}" -gt 0 ]; then
  ymir_set Video.FullScreenMode Borderless false
  ymir_set Video.FullScreenMode Width ${W}
  ymir_set Video.FullScreenMode Height ${H}
  ymir_set Video.FullScreenMode PixelFormat '"XRGB8888"'
  ymir_set Video.FullScreenMode RefreshRate 60.0
  ymir_set Video.FullScreenMode PixelDensity 1.0
else
  ymir_set Video.FullScreenMode Borderless true
fi

A="$(ee ymir_aspect)"
case "${A}" in
  auto) ymir_set Video ForceAspectRatio false ;;
  4:3|3:2|16:10|16:9) ymir_set Video ForceAspectRatio true; ymir_set Video ForcedAspect "\"${A}\"" ;;
  *) ymir_set Video ForceAspectRatio true; ymir_set Video ForcedAspect '"4:3"' ;;
esac

R="$(ee ymir_rotation)"
ymir_set Video Rotation "\"${R:-Normal}\""

[ "$(ee ymir_integer)" = "true" ] && V=true || V=false
ymir_set Video ForceIntegerScaling ${V}
[ "$(ee ymir_deinterlace)" = "true" ] && V=true || V=false
ymir_set Video.Enhancements Deinterlace ${V}
[ "$(ee ymir_meshes)" = "true" ] && V=true || V=false
ymir_set Video.Enhancements TransparentMeshes ${V}

ymir-sdl3 -p "${PROFILE}" -f "${1}"
