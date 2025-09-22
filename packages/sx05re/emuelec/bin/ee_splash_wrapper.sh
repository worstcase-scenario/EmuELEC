#!/usr/bin/bash

# SPDX-License-Identifier: GPL-2.0-or-later

set -euo pipefail

# shellcheck disable=SC1091
. /etc/profile

STOPPED=0

stop_splash() {
    if [[ ${STOPPED} -eq 0 ]]; then
        STOPPED=1
        "${TBASH:-/usr/bin/bash}" show_splash.sh stopplayer >/dev/null 2>&1 || true
    fi
}

is_shell_like() {
    case "$1" in
        ""|"/bin/bash"|"/usr/bin/bash"|"/bin/sh"|"/usr/bin/sh"|"/usr/bin/env"|"/bin/busybox"|"/usr/bin/busybox")
            return 0
            ;;
    esac
    return 1
}

has_non_shell_descendant() {
    local root_pid=$1
    local -A seen=()
    local queue=("${root_pid}")
    local idx=0

    while (( idx < ${#queue[@]} )); do
        local current_pid=${queue[idx]}
        ((idx++))

        while IFS= read -r child_pid; do
            child_pid=${child_pid//[[:space:]]/}
            [[ -z "${child_pid}" ]] && continue
            if [[ ${seen[${child_pid}]+_} ]]; then
                continue
            fi
            seen["${child_pid}"]=1

            local child_exe
            child_exe=$(readlink -f "/proc/${child_pid}/exe" 2>/dev/null || true)
            if [[ -n "${child_exe}" ]] && ! is_shell_like "${child_exe}"; then
                return 0
            fi

            queue+=("${child_pid}")
        done < <(ps -o pid= --ppid "${current_pid}" 2>/dev/null)
    done

    return 1
}

monitor_pid() {
    local target_pid=$1
    local timeout="${EE_SPLASH_TIMEOUT:-15}"
    local start_ts=$(date +%s)

    while kill -0 "${target_pid}" 2>/dev/null; do
        local exe
        exe=$(readlink -f "/proc/${target_pid}/exe" 2>/dev/null || true)
        if [[ -n "${exe}" ]] && ! is_shell_like "${exe}"; then
            stop_splash
            return
        fi

        if has_non_shell_descendant "${target_pid}"; then
            stop_splash
            return
        fi

        if [[ -n "${timeout}" && "${timeout}" =~ ^[0-9]+$ ]]; then
            local now=$(date +%s)
            if (( now - start_ts >= timeout )); then
                stop_splash
                return
            fi
        fi

        sleep 0.1
    done

    stop_splash
}

if [[ "${EE_SPLASH_DYNAMIC:-0}" != "1" || "${EE_SPLASH_STANDALONE:-0}" != "1" ]]; then
    exec "$@"
fi

"$@" &
cmd_pid=$!
monitor_pid "${cmd_pid}" &
watcher_pid=$!
wait "${cmd_pid}"
status=$?
wait "${watcher_pid}" 2>/dev/null || true
exit ${status}
