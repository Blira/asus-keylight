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
- a polished desktop GUI
- a full-spectrum color picker with RGB inputs
- a live mode that applies color changes directly from the picker
- automatic restore of the last saved lighting on login after reboot
- a desktop launcher installer
- a `udev` rule for non-root access to the keyboard HID device

## Supported Distributions

| Distribution family | Installer | Packages |
| --- | --- | --- |
| Zorin OS, Ubuntu and Debian | `apt` | `python3-tk`, `upower` |
| CachyOS and Arch Linux | `pacman` | `tk`, `upower` |

Use the same install or update command on either family. Run it as your
regular desktop user. The installer invokes `sudo` for packages and the
`udev` rule.

## Tested Hardware

Confirmed working on:

- ASUS Vivobook S 14 `S5406SA`

On CachyOS, this model exposes the same I²C HID LampArray device and the same
keyboard brightness LED as on Zorin OS. The installer supports CachyOS and
Arch Linux, and keyboard brightness can be set through UPower.

Possible compatibility:

- other ASUS laptops using HID device `0B05:19B6`
- other ASUS laptops exposing compatible HID Lighting/LampArray reports

Not guaranteed:

- any ASUS laptop not using the same HID interface
- non-ASUS laptops

## Quick Install

Without cloning the repository:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Blira/asus-keylight/main/scripts/install-remote.sh)
```

This downloads the project into `~/.local/share/asus-keylight` and then runs
the normal local installer.

To update that remote install later:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Blira/asus-keylight/main/scripts/update-remote.sh)
```

To remove that remote install completely:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Blira/asus-keylight/main/scripts/uninstall-remote.sh)
```

From a fresh clone:

```bash
git clone https://github.com/Blira/asus-keylight.git
cd asus-keylight
chmod +x install.sh
./install.sh
```

The `chmod` step is a safe fallback. In a normal git clone the executable bit
should already be preserved, but including it avoids friction.

What `install.sh` does:

- installs `python3-tk` and `upower` on Zorin OS, Debian and Ubuntu
- installs `tk` and `upower` on CachyOS/Arch Linux
- installs [`udev/70-asus-keylight.rules`](udev/70-asus-keylight.rules) and removes the old `99-asus-keylight.rules`
- reloads `udev` and reapplies rules to the matching HID devices
- installs local launchers in `~/.local/bin`
- installs a desktop entry in `~/.local/share/applications`
- installs an autostart entry in `~/.config/autostart` to restore the last saved lighting

What the remote installer additionally does:

- downloads the repository archive from GitHub
- stores the app under `~/.local/share/asus-keylight`
- makes future remote update and remote uninstall possible

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
- `~/.config/autostart/asus-keylight-restore.desktop`
- `/etc/udev/rules.d/70-asus-keylight.rules` and the legacy `99-asus-keylight.rules`

After removing the `udev` rule, the script also reloads `udev`.

The uninstall script does not delete the cloned repository directory itself. If
you also want to remove the source checkout, delete the project directory
manually after running the script.

If you installed with the remote no-clone flow, use:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Blira/asus-keylight/main/scripts/uninstall-remote.sh)
```

That removes the local launchers, desktop entry, `udev` rule, and the downloaded
application directory under `~/.local/share/asus-keylight`.

## Manual Install

For a manual installation, install the packages for your distribution.

CachyOS and Arch Linux

```bash
sudo pacman -S --needed tk upower
```

Zorin OS, Debian and Ubuntu

```bash
sudo apt update
sudo apt install python3-tk upower
```

Then run these commands from the project directory on either family.

```bash
sudo install -m 0644 udev/70-asus-keylight.rules /etc/udev/rules.d/70-asus-keylight.rules
sudo rm -f /etc/udev/rules.d/99-asus-keylight.rules
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=hidraw --settle
python3 -m asus_keylight.install_desktop
```

This creates:

- `~/.local/bin/asus-keylight`
- `~/.local/bin/asus-keylight-gui`
- `~/.local/share/applications/asus-keylight.desktop`
- `~/.config/autostart/asus-keylight-restore.desktop`

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
python3 -m asus_keylight restore
python3 -m asus_keylight set-color ff5500 --dry-run
```

Supported commands:

- `probe`
- `set-color RRGGBB`
- `set-brightness 0|1|2|3`
- `apply --color RRGGBB --brightness N`
- `restore`

## Permissions

To write keyboard color changes without `sudo`, the HID device must be writable
by your user.

This repository includes a `udev` rule in
[`udev/70-asus-keylight.rules`](udev/70-asus-keylight.rules) that tags
HID devices with the matching I²C vendor and product IDs for access by the
active local session through systemd-logind. Run the GUI and CLI as your
normal user from that session.

Brightness changes use the ASUS sysfs backlight node directly when it is
writable. When direct access is denied and it is the only keyboard
backlight exposed in sysfs, the app calls UPower through `busctl`.

## Dependencies

Required:

- Python 3.10+
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
