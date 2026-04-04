#!/bin/sh

set -eu

RULE_TARGET="/etc/udev/rules.d/99-asus-keylight.rules"
GUI_LAUNCHER="$HOME/.local/bin/asus-keylight-gui"
CLI_LAUNCHER="$HOME/.local/bin/asus-keylight"
DESKTOP_ENTRY="$HOME/.local/share/applications/asus-keylight.desktop"
AUTOSTART_ENTRY="$HOME/.config/autostart/asus-keylight-restore.desktop"

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

need_cmd rm
need_cmd sudo

echo "Removing local launchers..."
rm -f "$GUI_LAUNCHER" "$CLI_LAUNCHER" "$DESKTOP_ENTRY" "$AUTOSTART_ENTRY"

echo "Removing udev rule..."
sudo rm -f "$RULE_TARGET"
sudo udevadm control --reload

echo
echo "Uninstall complete."
echo "If you also want to remove the cloned repository, delete its directory manually."
