from __future__ import annotations

import sys
from pathlib import Path


def build_launcher_script(project_root: Path, module_name: str) -> str:
    python = sys.executable
    return "\n".join(
        [
            "#!/bin/sh",
            f'cd "{project_root}"',
            f'exec "{python}" -m {module_name} "$@"',
            "",
        ]
    )


def build_desktop_entry(launcher_path: Path) -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=ASUS Keylight",
            "Comment=Control ASUS keyboard lighting",
            f"Exec={launcher_path}",
            "Terminal=false",
            "Categories=Utility;Settings;",
            "Keywords=keyboard;rgb;backlight;asus;",
            "Icon=preferences-desktop-color",
            "StartupNotify=true",
            "StartupWMClass=ASUS Keylight",
            "",
        ]
    )


def build_autostart_entry(launcher_path: Path) -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=ASUS Keylight Restore",
            "Comment=Restore saved ASUS keyboard lighting",
            f"Exec={launcher_path} restore",
            "Terminal=false",
            "NoDisplay=true",
            "X-GNOME-Autostart-enabled=true",
            "",
        ]
    )


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    bin_dir = Path.home() / ".local" / "bin"
    applications_dir = Path.home() / ".local" / "share" / "applications"
    autostart_dir = Path.home() / ".config" / "autostart"
    bin_dir.mkdir(parents=True, exist_ok=True)
    applications_dir.mkdir(parents=True, exist_ok=True)
    autostart_dir.mkdir(parents=True, exist_ok=True)

    gui_launcher_path = bin_dir / "asus-keylight-gui"
    gui_launcher_path.write_text(build_launcher_script(project_root, "asus_keylight.gui"), encoding="utf-8")
    gui_launcher_path.chmod(0o755)

    cli_launcher_path = bin_dir / "asus-keylight"
    cli_launcher_path.write_text(build_launcher_script(project_root, "asus_keylight"), encoding="utf-8")
    cli_launcher_path.chmod(0o755)

    desktop_path = applications_dir / "asus-keylight.desktop"
    desktop_path.write_text(build_desktop_entry(gui_launcher_path), encoding="utf-8")
    desktop_path.chmod(0o755)
    autostart_path = autostart_dir / "asus-keylight-restore.desktop"
    autostart_path.write_text(build_autostart_entry(cli_launcher_path), encoding="utf-8")
    autostart_path.chmod(0o755)
    print(f"installed desktop launcher at {desktop_path}")
    print(f"installed autostart restore entry at {autostart_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
