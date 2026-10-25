#!/bin/bash

. /etc/profile

# Mali output has alpha < 1 -> make osd0 opaque (2 = None), restore after
modetest -M meson -w 31:"pixel blend mode":2 >/dev/null 2>&1
/usr/share/sm2emuSA/sm2-emu --fullscreen "${1}"
RC=$?
modetest -M meson -w 31:"pixel blend mode":0 >/dev/null 2>&1
exit $RC
