from __future__ import annotations

from dataclasses import dataclass

from vivorgb.errors import ValidationError

AURA_MSG_LEN = 17
I2C_HID_REPORT_ID = 0x5F
I2C_HID_REPORT_LEN = 64
SET_PACKET = bytes([0x5D, 0xB5] + [0x00] * 15)
APPLY_PACKET = bytes([0x5D, 0xB4] + [0x00] * 15)
LAMP_UPDATE_COMPLETE = 0x01


@dataclass(frozen=True)
class Colour:
    r: int
    g: int
    b: int

    @classmethod
    def parse(cls, value: str) -> "Colour":
        normalized = value.strip().lower().removeprefix("#")
        if len(normalized) != 6:
            raise ValidationError("color must be a 6-digit RGB hex value")
        try:
            return cls(
                r=int(normalized[0:2], 16),
                g=int(normalized[2:4], 16),
                b=int(normalized[4:6], 16),
            )
        except ValueError as exc:
            raise ValidationError("color must be a valid hex value") from exc

    def as_hex(self) -> str:
        return f"{self.r:02x}{self.g:02x}{self.b:02x}"


def validate_brightness(value: int) -> int:
    if value not in (0, 1, 2, 3):
        raise ValidationError("brightness must be one of: 0, 1, 2, 3")
    return value


def build_static_color_packet(colour: Colour) -> bytes:
    packet = bytearray(AURA_MSG_LEN)
    packet[0] = 0x5D
    packet[1] = 0xB3
    packet[2] = 0x00
    packet[3] = 0x00
    packet[4] = colour.r
    packet[5] = colour.g
    packet[6] = colour.b
    packet[7] = 0xEB
    packet[8] = 0x00
    return bytes(packet)


def wrap_i2c_feature_report(packet: bytes, *, report_id: int = I2C_HID_REPORT_ID, total_length: int = I2C_HID_REPORT_LEN) -> bytes:
    if len(packet) + 1 > total_length:
        raise ValidationError("packet is too large for the hid feature report")
    wrapped = bytearray(total_length)
    wrapped[0] = report_id
    wrapped[1 : 1 + len(packet)] = packet
    return bytes(wrapped)


@dataclass(frozen=True)
class LampArrayReportIds:
    attributes: int
    attributes_request: int
    attributes_response: int
    range_update: int
    control: int


@dataclass(frozen=True)
class LampArrayInfo:
    report_ids: LampArrayReportIds
    lamp_count: int
    min_update_interval_us: int
    red_levels: int
    green_levels: int
    blue_levels: int
    intensity_levels: int
    is_programmable: bool


def find_lamp_array_report_ids(report_descriptor: bytes) -> LampArrayReportIds | None:
    usages = {
        0x02: "attributes",
        0x20: "attributes_request",
        0x22: "attributes_response",
        0x60: "range_update",
        0x70: "control",
    }
    found: dict[str, int] = {}
    for index in range(len(report_descriptor) - 3):
        if report_descriptor[index] != 0x85 or report_descriptor[index + 2] != 0x09:
            continue
        usage = report_descriptor[index + 3]
        name = usages.get(usage)
        if name is None or name in found:
            continue
        found[name] = report_descriptor[index + 1]
    if set(found) != set(usages.values()):
        return None
    return LampArrayReportIds(
        attributes=found["attributes"],
        attributes_request=found["attributes_request"],
        attributes_response=found["attributes_response"],
        range_update=found["range_update"],
        control=found["control"],
    )


def parse_lamp_array_attributes(report: bytes) -> tuple[int, int]:
    if len(report) < 23:
        raise ValidationError("lamp array attributes report is too short")
    lamp_count = int.from_bytes(report[1:3], "little")
    min_update_interval_us = int.from_bytes(report[19:23], "little")
    return lamp_count, min_update_interval_us


def parse_lamp_attributes_response(report: bytes) -> tuple[int, int, int, int, bool]:
    if len(report) < 29:
        raise ValidationError("lamp attributes response report is too short")
    red_levels = report[23]
    green_levels = report[24]
    blue_levels = report[25]
    intensity_levels = report[26]
    is_programmable = report[27] != 0
    return red_levels, green_levels, blue_levels, intensity_levels, is_programmable


def build_lamp_array_control_report(report_id: int, *, autonomous_mode: bool) -> bytes:
    return bytes([report_id, 0x01 if autonomous_mode else 0x00])


def build_lamp_attributes_request_report(report_id: int, lamp_id: int) -> bytes:
    if lamp_id < 0 or lamp_id > 0xFFFF:
        raise ValidationError("lamp id is out of range")
    return bytes([report_id, lamp_id & 0xFF, (lamp_id >> 8) & 0xFF])


def _scale_channel(value: int, levels: int) -> int:
    if levels <= 0 or value <= 0:
        return 0
    scaled = round((value / 255) * levels)
    return max(1, min(levels, scaled))


def build_lamp_range_update_report(report_id: int, lamp_id_start: int, lamp_id_end: int, colour: Colour, *, red_levels: int, green_levels: int, blue_levels: int, intensity_levels: int) -> bytes:
    if lamp_id_start < 0 or lamp_id_end < lamp_id_start or lamp_id_end > 0xFFFF:
        raise ValidationError("lamp range is out of bounds")
    red = _scale_channel(colour.r, red_levels)
    green = _scale_channel(colour.g, green_levels)
    blue = _scale_channel(colour.b, blue_levels)
    if intensity_levels > 0 and (red or green or blue):
        intensity = intensity_levels
    else:
        intensity = 0
    return bytes(
        [
            report_id,
            LAMP_UPDATE_COMPLETE,
            lamp_id_start & 0xFF,
            (lamp_id_start >> 8) & 0xFF,
            lamp_id_end & 0xFF,
            (lamp_id_end >> 8) & 0xFF,
            red,
            green,
            blue,
            intensity,
        ]
    )
