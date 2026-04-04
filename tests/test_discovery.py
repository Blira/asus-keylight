import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vivorgb.discovery import EXPECTED_HID_ID, discover_keyboard


class DiscoveryTests(unittest.TestCase):
    def test_discover_keyboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dmi = root / "dmi"
            hidraw = root / "hidraw"
            led = root / "leds" / "asus::kbd_backlight"

            dmi.mkdir(parents=True)
            hidraw.mkdir(parents=True)
            led.mkdir(parents=True)

            (dmi / "sys_vendor").write_text("ASUSTeK COMPUTER INC.\n", encoding="utf-8")
            (dmi / "product_name").write_text("ASUS Vivobook S 14 S5406SA_S5406SA\n", encoding="utf-8")
            (dmi / "product_version").write_text("1.0\n", encoding="utf-8")
            (dmi / "board_name").write_text("S5406SA\n", encoding="utf-8")

            (led / "brightness").write_text("2\n", encoding="utf-8")
            (led / "max_brightness").write_text("3\n", encoding="utf-8")

            hidraw_dir = hidraw / "hidraw1" / "device"
            hidraw_dir.mkdir(parents=True)
            (hidraw_dir / "uevent").write_text(
                "\n".join(
                    [
                        "DRIVER=hid-generic",
                        f"HID_ID={EXPECTED_HID_ID}",
                        "HID_NAME=ITE5570:00 0B05:19B6",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with (
                mock.patch("vivorgb.discovery.DMI_ROOT", dmi),
                mock.patch("vivorgb.discovery.HIDRAW_ROOT", hidraw),
                mock.patch("vivorgb.discovery.LED_ROOT", led),
            ):
                target = discover_keyboard()

            self.assertEqual(target.hidraw_name, "hidraw1")
            self.assertEqual(str(target.hidraw_path), "/dev/hidraw1")
            self.assertTrue(target.is_expected_model)


if __name__ == "__main__":
    unittest.main()
