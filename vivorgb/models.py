from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KeyboardTarget:
    sys_vendor: str
    product_name: str
    product_version: str
    board_name: str
    hid_id: str
    hid_name: str
    hidraw_name: str
    hidraw_path: Path
    hid_sysfs_path: Path
    brightness_path: Path
    max_brightness_path: Path

    @property
    def is_expected_model(self) -> bool:
        return self.product_name == "ASUS Vivobook S 14 S5406SA_S5406SA"

    @property
    def brightness_led_path(self) -> Path:
        return self.brightness_path.parent

    @property
    def report_descriptor_path(self) -> Path:
        return self.hid_sysfs_path / "report_descriptor"
