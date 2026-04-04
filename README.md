# asus-keylight

`asus-keylight` is a small Linux app and CLI for controlling ASUS keyboard
lighting.

It was tested on an **ASUS Vivobook S 14 `S5406SA`** running **Zorin OS**. The
project targets the ASUS HID keyboard lighting controller exposed as
`0B05:19B6`, so it may also work on other ASUS laptops that expose the same
controller or HID Lighting/LampArray interface, but that is not guaranteed.

## What It Does

- detects the machine model through DMI
- detects the ASUS keyboard HID controller `0B05:19B6`
- uses the standard ASUS brightness node at `/sys/class/leds/asus::kbd_backlight`
- prefers HID Lighting/LampArray when the device advertises it
- falls back to the older ASUS `0x5D B3/B4/B5` packet path when needed

The project includes:

- a CLI
- a simple desktop GUI
- a desktop launcher installer
- a `udev` rule for non-root access to the keyboard HID device

## Tested Hardware

Confirmed working on:

- ASUS Vivobook S 14 `S5406SA`

Possible compatibility:

- other ASUS laptops using HID device `0B05:19B6`
- other ASUS laptops exposing compatible HID Lighting/LampArray reports
- Debian/Ubuntu-based distributions should be the smoothest path because the
  install flow currently assumes `apt` and `python3-tk`

Not guaranteed:

- any ASUS laptop not using the same HID interface
- non-ASUS laptops

## Quick Install

From a fresh clone:

```bash
git clone <repo-url>
cd asus-keylight
chmod +x install.sh
./install.sh
```

The `chmod` step is a safe fallback. In a normal git clone the executable bit
should already be preserved, but including it avoids friction.

What `install.sh` does:

- installs `python3-tk` on Debian/Ubuntu systems
- installs the `udev` rule from [`udev/99-asus-keylight.rules`](udev/99-asus-keylight.rules)
- reloads `udev`
- installs local launchers in `~/.local/bin`
- installs a desktop entry in `~/.local/share/applications`

After installation, run:

```bash
asus-keylight-gui
```

Or open `ASUS Keylight` from your app menu.

If `~/.local/bin` is not in your `PATH`, run the GUI directly:

```bash
python3 -m asus_keylight.gui
```

## Uninstall

To remove the local install created by this project:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

`uninstall.sh` removes:

- `~/.local/bin/asus-keylight`
- `~/.local/bin/asus-keylight-gui`
- `~/.local/share/applications/asus-keylight.desktop`
- `/etc/udev/rules.d/99-asus-keylight.rules`

After removing the `udev` rule, the script also reloads `udev`.

The uninstall script does not delete the cloned repository directory itself. If
you also want to remove the source checkout, delete the project directory
manually after running the script.

## Manual Install

If you do not want to use `install.sh`:

```bash
sudo apt install python3-tk
sudo install -m 0644 udev/99-asus-keylight.rules /etc/udev/rules.d/99-asus-keylight.rules
sudo udevadm control --reload
sudo udevadm trigger /dev/hidraw1
python3 -m asus_keylight.install_desktop
```

This creates:

- `~/.local/bin/asus-keylight`
- `~/.local/bin/asus-keylight-gui`
- `~/.local/share/applications/asus-keylight.desktop`

## Running The App

GUI:

```bash
asus-keylight-gui
```

Direct module launch:

```bash
python3 -m asus_keylight.gui
```

App menu:

- search for `ASUS Keylight`

## CLI Usage

Examples:

```bash
python3 -m asus_keylight probe
python3 -m asus_keylight set-color ffcc00
python3 -m asus_keylight set-brightness 3
python3 -m asus_keylight apply --color 00ffaa --brightness 2
python3 -m asus_keylight set-color ff5500 --dry-run
```

Supported commands:

- `probe`
- `set-color RRGGBB`
- `set-brightness 0|1|2|3`
- `apply --color RRGGBB --brightness N`

## Permissions

To write keyboard color changes without `sudo`, the HID device must be writable
by your user.

This repository includes a `udev` rule in
[`udev/99-asus-keylight.rules`](udev/99-asus-keylight.rules) that
grants access to the matching ASUS keyboard HID device.

On the tested laptop, the rule matches HID parent `0018:0B05:19B6.0002` and
assigns access through the `plugdev` group.

Brightness changes use the standard ASUS sysfs backlight node and may also
require appropriate permissions depending on your system setup.

## Dependencies

Required:

- Python 3.12+
- `tkinter` for the GUI

Optional:

- `python3-hid` or `python3-hidapi`

If `hidapi` is available, the project tries that backend first. Otherwise it
uses `hidraw` with `ioctl` directly.

## Known Limitations

- ASUS does not provide official Linux support for this lighting interface.
- The project was validated on `S5406SA`, not across the full ASUS laptop range.
- Some ASUS models may require a different HID protocol or report layout.
- The desktop launcher created by this project runs the code from the cloned
  repository path, so if you move or delete the clone, reinstall the launcher.

## Development Notes

This project currently favors practical local installation from a git clone over
system-wide packaging. That keeps installation simple on Debian/Ubuntu systems
that enforce PEP 668 restrictions on `pip`.
