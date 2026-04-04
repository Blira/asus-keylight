#!/bin/sh

set -eu

INSTALL_DIR=${INSTALL_DIR:-"$HOME/.local/share/asus-keylight"}
RULE_TARGET="/etc/udev/rules.d/99-asus-keylight.rules"
GUI_LAUNCHER="$HOME/.local/bin/asus-keylight-gui"
CLI_LAUNCHER="$HOME/.local/bin/asus-keylight"
DESKTOP_ENTRY="$HOME/.local/share/applications/asus-keylight.desktop"

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

need_cmd rm
need_cmd sudo
need_cmd sh

if [ -f "$INSTALL_DIR/uninstall.sh" ]; then
    (
        cd "$INSTALL_DIR"
        sh ./uninstall.sh
    )
else
    echo "Removing local launchers..."
    rm -f "$GUI_LAUNCHER" "$CLI_LAUNCHER" "$DESKTOP_ENTRY"
    echo "Removing udev rule..."
    sudo rm -f "$RULE_TARGET"
    sudo udevadm control --reload
fi

echo "Removing downloaded application files..."
rm -rf "$INSTALL_DIR"

echo
echo "Remote uninstall complete."
