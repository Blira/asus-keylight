from __future__ import annotations

from pathlib import Path

from vivorgb.errors import DiscoveryError
from vivorgb.models import KeyboardTarget

DMI_ROOT = Path("/sys/devices/virtual/dmi/id")
HIDRAW_ROOT = Path("/sys/class/hidraw")
LED_ROOT = Path("/sys/class/leds/asus::kbd_backlight")
EXPECTED_HID_ID = "0018:00000B05:000019B6"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def discover_keyboard() -> KeyboardTarget:
    if not HIDRAW_ROOT.exists():
        raise DiscoveryError("hidraw sysfs root not found")
    if not LED_ROOT.exists():
        raise DiscoveryError("ASUS keyboard backlight sysfs entry not found")

    sys_vendor = _read_text(DMI_ROOT / "sys_vendor")
    product_name = _read_text(DMI_ROOT / "product_name")
    product_version = _read_text(DMI_ROOT / "product_version")
    board_name = _read_text(DMI_ROOT / "board_name")

    for hidraw_dir in sorted(HIDRAW_ROOT.glob("hidraw*")):
        uevent_path = hidraw_dir / "device" / "uevent"
        if not uevent_path.exists():
            continue
        pairs = {}
        for line in _read_text(uevent_path).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                pairs[key] = value
        if pairs.get("HID_ID") != EXPECTED_HID_ID:
            continue
        hidraw_name = hidraw_dir.name
        return KeyboardTarget(
            sys_vendor=sys_vendor,
            product_name=product_name,
            product_version=product_version,
            board_name=board_name,
            hid_id=pairs["HID_ID"],
            hid_name=pairs.get("HID_NAME", ""),
            hidraw_name=hidraw_name,
            hidraw_path=Path("/dev") / hidraw_name,
            hid_sysfs_path=(hidraw_dir / "device").resolve(),
            brightness_path=LED_ROOT / "brightness",
            max_brightness_path=LED_ROOT / "max_brightness",
        )
    raise DiscoveryError(f"ASUS RGB HID {EXPECTED_HID_ID} not found")
