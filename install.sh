#!/bin/sh

set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RULE_SOURCE="$PROJECT_DIR/udev/70-asus-keylight.rules"
RULE_TARGET="/etc/udev/rules.d/70-asus-keylight.rules"
LEGACY_RULE="/etc/udev/rules.d/99-asus-keylight.rules"

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

need_cmd python3
need_cmd sudo
need_cmd udevadm

if command -v apt >/dev/null 2>&1; then
    echo "Installing system packages..."
    sudo apt update
    sudo apt install -y python3-tk upower
elif command -v pacman >/dev/null 2>&1; then
    echo "Installing system packages..."
    sudo pacman -S --needed tk upower
else
    echo "warning: no supported package manager found; skipping package installation" >&2
    echo "warning: install Tkinter and UPower manually for your distro" >&2
fi

echo "Installing udev rule..."
sudo install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
sudo rm -f "$LEGACY_RULE"
sudo udevadm control --reload

for device in /sys/bus/hid/devices/0018:0B05:19B6.*/hidraw/hidraw*; do
    [ -d "$device" ] || continue
    sudo udevadm trigger --settle "$device"
done

echo "Installing launchers..."
cd "$PROJECT_DIR"
python3 -m asus_keylight.install_desktop

echo
echo "Install complete."
echo "Run: asus-keylight-gui"
echo "Or open: ASUS Keylight from your app menu"
echo "If ~/.local/bin is not in PATH, run: python3 -m asus_keylight.gui"
