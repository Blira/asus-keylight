import unittest
from pathlib import Path

from asus_keylight.install_desktop import build_autostart_entry


class InstallDesktopTests(unittest.TestCase):
    def test_build_autostart_entry_uses_restore_command(self) -> None:
        entry = build_autostart_entry(Path("/tmp/asus-keylight"))

        self.assertIn("Exec=/tmp/asus-keylight restore", entry)
        self.assertIn("NoDisplay=true", entry)


if __name__ == "__main__":
    unittest.main()
