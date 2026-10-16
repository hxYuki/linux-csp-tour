#!/usr/bin/env bash
# The installer extracts these exports from the user's CSPenguin launcher.
source "$(dirname "${BASH_SOURCE[0]}")/upstream-exports.sh"
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
export WINEPREFIX="$compat_prefix"
export WINESERVER="${compat_wine%/*}/wineserver"
export PATH="${compat_wine%/*}:$PATH"
export WINEDLLPATH="$compat_cspenguin${WINEDLLPATH:+:$WINEDLLPATH}"
export DXVK_CONFIG_FILE="$compat_prefix/dxvk.conf" DXVK_STATE_CACHE_PATH="$compat_prefix"
export __GL_SHADER_DISK_CACHE_PATH="$compat_prefix"
# Preserve upstream WebView2 flags; a machine-specific proxy is optional.
if [[ -n "$compat_proxy" ]]; then
    while [[ "${WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:-}" =~ --proxy-server=[^[:space:]]+ ]]; do
        WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=${WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS/"${BASH_REMATCH[0]}"/}
    done
    export WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="${WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:-} --proxy-server=$compat_proxy"
fi
wait_for_monitors() {
    local deadline=$((SECONDS + 90))
    until xrandr --listmonitors 2>/dev/null | awk 'NR==1 {ready=($2>0)} END {exit !ready}'; do
        if ((SECONDS >= deadline)); then
            echo 'No active Plasma Xwayland monitor after 90 seconds; switch back to this session and retry.' >&2
            return 1
        fi
        sleep 0.5
    done
}
