from __future__ import annotations

import argparse
import json
import sys

from asus_keylight.controller import (
    apply_static_color,
    current_brightness,
    ensure_supported_model,
    max_brightness,
    run_apply,
    write_brightness,
)
from asus_keylight.discovery import discover_keyboard
from asus_keylight.errors import AsusKeylightError, DiscoveryError, TransportError, ValidationError
from asus_keylight.protocol import Colour, find_lamp_array_report_ids, validate_brightness
from asus_keylight.state import load_state
from asus_keylight.transport import HidTransport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asus-keylight")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--force", action="store_true", help="ignore model mismatch")
    common.add_argument("--dry-run", action="store_true", help="print what would be sent without writing")
    common.add_argument("--verbose", action="store_true", help="print extra details")
    common.add_argument(
        "--backend",
        choices=("auto", "hidapi", "hidraw"),
        default="auto",
        help="transport backend preference",
    )
    for action in common._actions:
        if action.dest != "help":
            parser._add_action(action)

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "probe",
        help="detect keyboard RGB controller and brightness node",
        parents=[common],
    )

    set_color = subparsers.add_parser("set-color", help="set a static keyboard color", parents=[common])
    set_color.add_argument("color", help="hex RGB value, e.g. ff5500")

    set_brightness = subparsers.add_parser(
        "set-brightness",
        help="set brightness level 0..3",
        parents=[common],
    )
    set_brightness.add_argument("brightness", type=int, help="brightness level")

    apply_cmd = subparsers.add_parser(
        "apply",
        help="apply color and brightness in one command",
        parents=[common],
    )
    apply_cmd.add_argument("--color", dest="color", help="hex RGB value")
    apply_cmd.add_argument("--brightness", dest="brightness", type=int, help="brightness level 0..3")

    subparsers.add_parser(
        "restore",
        help="restore the last saved color and brightness",
        parents=[common],
    )
    return parser


def packet_hex(packet: bytes) -> str:
    return packet.hex(" ")


def command_probe(args: argparse.Namespace) -> int:
    target = discover_keyboard()
    ensure_supported_model(target, args.force)
    lamp_array_report_ids = None
    if target.report_descriptor_path.exists():
        lamp_array_report_ids = find_lamp_array_report_ids(target.report_descriptor_path.read_bytes())
    payload = {
        "sys_vendor": target.sys_vendor,
        "product_name": target.product_name,
        "product_version": target.product_version,
        "board_name": target.board_name,
        "hid_id": target.hid_id,
        "hid_name": target.hid_name,
        "hidraw_path": str(target.hidraw_path),
        "hidraw_exists": target.hidraw_path.exists(),
        "hid_sysfs_path": str(target.hid_sysfs_path),
        "brightness_path": str(target.brightness_path),
        "current_brightness": current_brightness(target),
        "max_brightness": max_brightness(target),
        "expected_model": target.is_expected_model,
        "report_descriptor_path": str(target.report_descriptor_path),
        "lamp_array_supported": lamp_array_report_ids is not None,
        "lamp_array_report_ids": (
            None
            if lamp_array_report_ids is None
            else {
                "attributes": lamp_array_report_ids.attributes,
                "attributes_request": lamp_array_report_ids.attributes_request,
                "attributes_response": lamp_array_report_ids.attributes_response,
                "range_update": lamp_array_report_ids.range_update,
                "control": lamp_array_report_ids.control,
            }
        ),
        "hidapi_available": HidTransport.hidapi_available(),
        "hidapi_library_present": HidTransport.hidapi_library_present(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def command_set_color(args: argparse.Namespace) -> int:
    target = discover_keyboard()
    ensure_supported_model(target, args.force)
    colour = Colour.parse(args.color)
    packets = apply_static_color(
        target,
        colour,
        dry_run=args.dry_run,
        preferred_backend=args.backend,
    )
    print(f"color={colour.as_hex()} hidraw={target.hidraw_path}")
    for index, packet in enumerate(packets, start=1):
        print(f"packet{index}={packet_hex(packet)}")
    return 0


def command_set_brightness(args: argparse.Namespace) -> int:
    target = discover_keyboard()
    ensure_supported_model(target, args.force)
    value = validate_brightness(args.brightness)
    if not args.dry_run:
        write_brightness(target, value)
    print(f"brightness={value} path={target.brightness_path}")
    return 0


def command_apply(args: argparse.Namespace) -> int:
    target, packets = run_apply(
        colour_hex=args.color,
        brightness=args.brightness,
        dry_run=args.dry_run,
        force=args.force,
        preferred_backend=args.backend,
    )
    result = {
        "hidraw_path": str(target.hidraw_path),
        "brightness_path": str(target.brightness_path),
        "color": args.color.lower() if args.color else None,
        "brightness": args.brightness,
        "packets": [packet_hex(packet) for packet in packets],
    }
    print(json.dumps(result, indent=2))
    return 0


def command_restore(args: argparse.Namespace) -> int:
    state = load_state()
    if state is None:
        raise ValidationError("no saved state found")

    color = state.get("color")
    brightness = state.get("brightness")
    target, packets = run_apply(
        colour_hex=str(color) if color is not None else None,
        brightness=int(brightness) if brightness is not None else None,
        dry_run=args.dry_run,
        force=args.force,
        preferred_backend=args.backend,
    )
    result = {
        "hidraw_path": str(target.hidraw_path),
        "brightness_path": str(target.brightness_path),
        "color": color,
        "brightness": brightness,
        "packets": [packet_hex(packet) for packet in packets],
    }
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            return command_probe(args)
        if args.command == "set-color":
            return command_set_color(args)
        if args.command == "set-brightness":
            return command_set_brightness(args)
        if args.command == "apply":
            return command_apply(args)
        if args.command == "restore":
            return command_restore(args)
        parser.error(f"unknown command: {args.command}")
    except (DiscoveryError, TransportError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except AsusKeylightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
