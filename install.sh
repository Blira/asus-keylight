#!/bin/sh

set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RULE_SOURCE="$PROJECT_DIR/udev/99-asus-keylight.rules"
RULE_TARGET="/etc/udev/rules.d/99-asus-keylight.rules"

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

need_cmd python3
need_cmd sudo

if command -v apt >/dev/null 2>&1; then
    echo "Installing system packages..."
    sudo apt update
    sudo apt install -y python3-tk
else
    echo "warning: apt not found; skipping package installation" >&2
    echo "warning: install tkinter manually for your distro" >&2
fi

echo "Installing udev rule..."
sudo install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
sudo udevadm control --reload

if [ -e /dev/hidraw1 ]; then
    sudo udevadm trigger /dev/hidraw1
fi

echo "Installing launchers..."
python3 -m asus_keylight.install_desktop

echo
echo "Install complete."
echo "Run: asus-keylight-gui"
echo "Or open: ASUS Keylight from your app menu"
echo "If ~/.local/bin is not in PATH, run: python3 -m asus_keylight.gui"
