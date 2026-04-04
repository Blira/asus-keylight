from __future__ import annotations

import json
from pathlib import Path

from asus_keylight.errors import ValidationError
from asus_keylight.protocol import Colour, validate_brightness

CONFIG_DIR = Path.home() / ".config" / "asus-keylight"
STATE_PATH = CONFIG_DIR / "state.json"


def load_state(path: Path = STATE_PATH) -> dict[str, int | str] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read saved state from {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValidationError("saved state must be a JSON object")

    state: dict[str, int | str] = {}
    colour = raw.get("color")
    if colour is not None:
        state["color"] = Colour.parse(str(colour)).as_hex()

    brightness = raw.get("brightness")
    if brightness is not None:
        try:
            numeric_brightness = int(brightness)
        except (TypeError, ValueError) as exc:
            raise ValidationError("saved brightness must be an integer") from exc
        state["brightness"] = validate_brightness(numeric_brightness)

    return state or None


def save_state(*, color: str | None = None, brightness: int | None = None, path: Path = STATE_PATH) -> dict[str, int | str]:
    existing = load_state(path) or {}
    state = dict(existing)

    if color is not None:
        state["color"] = Colour.parse(color).as_hex()
    if brightness is not None:
        state["brightness"] = validate_brightness(brightness)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state
