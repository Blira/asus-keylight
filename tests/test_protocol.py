import unittest

from asus_keylight.errors import ValidationError
from asus_keylight.protocol import (
    APPLY_PACKET,
    I2C_HID_REPORT_ID,
    LAMP_UPDATE_COMPLETE,
    SET_PACKET,
    Colour,
    build_lamp_array_control_report,
    build_lamp_attributes_request_report,
    build_lamp_range_update_report,
    build_static_color_packet,
    find_lamp_array_report_ids,
    parse_lamp_array_attributes,
    parse_lamp_attributes_response,
    validate_brightness,
    wrap_i2c_feature_report,
)


class ProtocolTests(unittest.TestCase):
    def test_parse_colour(self) -> None:
        colour = Colour.parse("#ff11dd")
        self.assertEqual((colour.r, colour.g, colour.b), (0xFF, 0x11, 0xDD))

    def test_parse_colour_rejects_invalid(self) -> None:
        with self.assertRaises(ValidationError):
            Colour.parse("abc")

    def test_static_packet_shape(self) -> None:
        packet = build_static_color_packet(Colour.parse("ff11dd"))
        self.assertEqual(
            packet,
            bytes([0x5D, 0xB3, 0x00, 0x00, 0xFF, 0x11, 0xDD, 0xEB, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        )
        self.assertEqual(len(packet), 17)

    def test_apply_and_set_packet_shape(self) -> None:
        self.assertEqual(len(SET_PACKET), 17)
        self.assertEqual(len(APPLY_PACKET), 17)

    def test_validate_brightness(self) -> None:
        self.assertEqual(validate_brightness(3), 3)
        with self.assertRaises(ValidationError):
            validate_brightness(4)

    def test_wrap_i2c_feature_report(self) -> None:
        wrapped = wrap_i2c_feature_report(bytes([0x5D, 0xB4]))
        self.assertEqual(len(wrapped), 64)
        self.assertEqual(wrapped[0], I2C_HID_REPORT_ID)
        self.assertEqual(wrapped[1:3], bytes([0x5D, 0xB4]))

    def test_find_lamp_array_report_ids(self) -> None:
        descriptor = bytes(
            [
                0x85,
                0x01,
                0x09,
                0x02,
                0x85,
                0x02,
                0x09,
                0x20,
                0x85,
                0x03,
                0x09,
                0x22,
                0x85,
                0x05,
                0x09,
                0x60,
                0x85,
                0x0B,
                0x09,
                0x70,
            ]
        )
        report_ids = find_lamp_array_report_ids(descriptor)
        self.assertIsNotNone(report_ids)
        assert report_ids is not None
        self.assertEqual(report_ids.attributes, 0x01)
        self.assertEqual(report_ids.attributes_request, 0x02)
        self.assertEqual(report_ids.attributes_response, 0x03)
        self.assertEqual(report_ids.range_update, 0x05)
        self.assertEqual(report_ids.control, 0x0B)

    def test_parse_lamp_array_attributes(self) -> None:
        report = bytes([0x01, 0x05, 0x00] + [0x00] * 16 + [0x40, 0x42, 0x0F, 0x00])
        self.assertEqual(parse_lamp_array_attributes(report), (5, 1_000_000))

    def test_parse_lamp_attributes_response(self) -> None:
        report = bytes([0x03] + [0x00] * 22 + [0xFF, 0xFE, 0xFD, 0x20, 0x01, 0x00])
        self.assertEqual(
            parse_lamp_attributes_response(report),
            (0xFF, 0xFE, 0xFD, 0x20, True),
        )

    def test_build_lamp_reports(self) -> None:
        self.assertEqual(build_lamp_array_control_report(0x0B, autonomous_mode=False), bytes([0x0B, 0x00]))
        self.assertEqual(build_lamp_attributes_request_report(0x02, 0x1234), bytes([0x02, 0x34, 0x12]))
        self.assertEqual(
            build_lamp_range_update_report(
                0x05,
                0,
                4,
                Colour.parse("804020"),
                red_levels=0xFF,
                green_levels=0xFF,
                blue_levels=0xFF,
                intensity_levels=0x10,
            ),
            bytes([0x05, LAMP_UPDATE_COMPLETE, 0x00, 0x00, 0x04, 0x00, 0x80, 0x40, 0x20, 0x10]),
        )


if __name__ == "__main__":
    unittest.main()
