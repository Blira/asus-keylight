import tempfile
import unittest
from pathlib import Path

from asus_keylight.errors import ValidationError
from asus_keylight.state import load_state, save_state


class StateTests(unittest.TestCase):
    def test_save_and_load_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            saved = save_state(color="#0EA5E9", brightness=2, path=path)
            loaded = load_state(path)

        self.assertEqual(saved, {"color": "0ea5e9", "brightness": 2})
        self.assertEqual(loaded, {"color": "0ea5e9", "brightness": 2})

    def test_save_state_preserves_existing_brightness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            save_state(color="ff0000", brightness=3, path=path)
            save_state(color="00ff00", path=path)
            loaded = load_state(path)

        self.assertEqual(loaded, {"color": "00ff00", "brightness": 3})

    def test_load_state_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text("{broken", encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_state(path)


if __name__ == "__main__":
    unittest.main()
