from __future__ import annotations

import time
from pathlib import Path

from asus_keylight.discovery import discover_keyboard
from asus_keylight.errors import DiscoveryError, TransportError, ValidationError
from asus_keylight.models import KeyboardTarget
from asus_keylight.protocol import (
    APPLY_PACKET,
    SET_PACKET,
    Colour,
    LampArrayInfo,
    build_static_color_packet,
    build_lamp_array_control_report,
    build_lamp_attributes_request_report,
    build_lamp_range_update_report,
    find_lamp_array_report_ids,
    parse_lamp_array_attributes,
    parse_lamp_attributes_response,
    validate_brightness,
    wrap_i2c_feature_report,
)
from asus_keylight.transport import HidTransport


def ensure_supported_model(target: KeyboardTarget, force: bool) -> None:
    if target.is_expected_model or force:
        return
    raise DiscoveryError(
        f"unexpected model '{target.product_name}'. Use --force to continue."
    )


def current_brightness(target: KeyboardTarget) -> int:
    return int(target.brightness_path.read_text(encoding="utf-8").strip())


def max_brightness(target: KeyboardTarget) -> int:
    return int(target.max_brightness_path.read_text(encoding="utf-8").strip())


def write_brightness(target: KeyboardTarget, value: int) -> None:
    validated = validate_brightness(value)
    try:
        target.brightness_path.write_text(f"{validated}\n", encoding="utf-8")
    except OSError as exc:
        raise TransportError(f"cannot write brightness to {target.brightness_path}: {exc}") from exc


def detect_lamp_array(target: KeyboardTarget) -> LampArrayInfo | None:
    descriptor_path = target.report_descriptor_path
    if not descriptor_path.exists():
        return None
    report_ids = find_lamp_array_report_ids(descriptor_path.read_bytes())
    if report_ids is None:
        return None
    with HidTransport(target.hidraw_path) as transport:
        attrs = transport.get_feature_report(report_ids.attributes, 64)
        lamp_count, min_update_interval_us = parse_lamp_array_attributes(attrs)
        transport.send_feature_report(build_lamp_attributes_request_report(report_ids.attributes_request, 0))
        lamp_attrs = transport.get_feature_report(report_ids.attributes_response, 64)
    red_levels, green_levels, blue_levels, intensity_levels, is_programmable = parse_lamp_attributes_response(lamp_attrs)
    return LampArrayInfo(
        report_ids=report_ids,
        lamp_count=lamp_count,
        min_update_interval_us=min_update_interval_us,
        red_levels=red_levels,
        green_levels=green_levels,
        blue_levels=blue_levels,
        intensity_levels=intensity_levels,
        is_programmable=is_programmable,
    )


def apply_lamp_array_color(target: KeyboardTarget, colour: Colour, *, dry_run: bool, preferred_backend: str = "auto") -> list[bytes]:
    descriptor_path = target.report_descriptor_path
    if not descriptor_path.exists():
        raise TransportError(f"report descriptor not found at {descriptor_path}")
    report_ids = find_lamp_array_report_ids(descriptor_path.read_bytes())
    if report_ids is None:
        raise TransportError("lamp array reports not found in HID descriptor")

    if dry_run:
        lamp_count = 1
        min_update_interval_us = 0
        red_levels = green_levels = blue_levels = intensity_levels = 0xFF
    else:
        with HidTransport(target.hidraw_path, preferred_backend=preferred_backend) as transport:
            attrs = transport.get_feature_report(report_ids.attributes, 64)
            lamp_count, min_update_interval_us = parse_lamp_array_attributes(attrs)
            transport.send_feature_report(build_lamp_attributes_request_report(report_ids.attributes_request, 0))
            lamp_attrs = transport.get_feature_report(report_ids.attributes_response, 64)
            red_levels, green_levels, blue_levels, intensity_levels, is_programmable = parse_lamp_attributes_response(lamp_attrs)
            if not is_programmable:
                raise TransportError("lamp array reports indicate a non-programmable device")
            packets = [
                build_lamp_array_control_report(report_ids.control, autonomous_mode=False),
                build_lamp_range_update_report(
                    report_ids.range_update,
                    0,
                    max(0, lamp_count - 1),
                    colour,
                    red_levels=red_levels,
                    green_levels=green_levels,
                    blue_levels=blue_levels,
                    intensity_levels=intensity_levels,
                ),
            ]
            transport.send_feature_report(packets[0])
            if min_update_interval_us > 0:
                time.sleep(min_update_interval_us / 1_000_000)
            transport.send_feature_report(packets[1])
            return packets

    return [
        build_lamp_array_control_report(report_ids.control, autonomous_mode=False),
        build_lamp_range_update_report(
            report_ids.range_update,
            0,
            max(0, lamp_count - 1),
            colour,
            red_levels=red_levels,
            green_levels=green_levels,
            blue_levels=blue_levels,
            intensity_levels=intensity_levels,
        ),
    ]


def apply_static_color(target: KeyboardTarget, colour: Colour, *, dry_run: bool, preferred_backend: str = "auto") -> list[bytes]:
    if target.report_descriptor_path.exists():
        report_ids = find_lamp_array_report_ids(target.report_descriptor_path.read_bytes())
        if report_ids is not None:
            return apply_lamp_array_color(
                target,
                colour,
                dry_run=dry_run,
                preferred_backend=preferred_backend,
            )
    packets = [build_static_color_packet(colour), SET_PACKET, APPLY_PACKET]
    if dry_run:
        return packets
    with HidTransport(target.hidraw_path, preferred_backend=preferred_backend) as transport:
        for packet in packets:
            transport.send_feature_report(wrap_i2c_feature_report(packet))
    return packets


def run_apply(
    *,
    colour_hex: str | None,
    brightness: int | None,
    dry_run: bool,
    force: bool,
    preferred_backend: str = "auto",
) -> tuple[KeyboardTarget, list[bytes]]:
    target = discover_keyboard()
    ensure_supported_model(target, force)
    packets: list[bytes] = []
    colour: Colour | None = None

    if colour_hex is not None:
        colour = Colour.parse(colour_hex)
        packets.extend(
            apply_static_color(
                target,
                colour,
                dry_run=dry_run,
                preferred_backend=preferred_backend,
            )
        )

    if brightness is not None:
        validate_brightness(brightness)
        if not dry_run:
            write_brightness(target, brightness)
        if colour is not None:
            packets.extend(
                apply_static_color(
                    target,
                    colour,
                    dry_run=dry_run,
                    preferred_backend=preferred_backend,
                )
            )
    if colour_hex is None and brightness is None:
        raise ValidationError("nothing to apply")
    return target, packets
