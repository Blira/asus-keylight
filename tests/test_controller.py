import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from asus_keylight.controller import write_brightness
from asus_keylight.errors import TransportError
from asus_keylight.models import KeyboardTarget


class BrightnessTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        leds = Path(temp_dir.name)
        led = leds / "asus::kbd_backlight"
        led.mkdir()
        self.leds = leds
        self.target = mock.Mock(spec=KeyboardTarget)
        self.target.brightness_led_path = led
        self.target.brightness_path = led / "brightness"

    @mock.patch("asus_keylight.controller.subprocess.run")
    def test_writable_sysfs_does_not_need_upower(self, run) -> None:
        write_brightness(self.target, 2)
        self.assertEqual(self.target.brightness_path.read_text(), "2\n")
        run.assert_not_called()

    @mock.patch("asus_keylight.controller.subprocess.run")
    @mock.patch.object(Path, "write_text", side_effect=PermissionError)
    def test_permission_denied_uses_upower_for_sole_backlight(self, write, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0)
        write_brightness(self.target, 2)
        self.assertEqual(run.call_args.args[0][-3:], ["SetBrightness", "i", "2"])
        run.assert_called_once()

    @mock.patch("asus_keylight.controller.subprocess.run")
    @mock.patch.object(Path, "write_text", side_effect=PermissionError)
    def test_permission_denied_with_multiple_backlights_does_not_use_upower(self, write, run) -> None:
        (self.leds / "other::kbd_backlight").mkdir()
        with self.assertRaises(TransportError):
            write_brightness(self.target, 2)
        run.assert_not_called()
