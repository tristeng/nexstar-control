#
# Copyright Tristen Georgiou 2024
#
import datetime
import logging
from unittest.mock import MagicMock, call
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockFixture
import serial

from nexstar_control.device import (
    NexStarHandControl,
    TrackingMode,
    DeviceType,
    DeviceModel,
    to_dms,
    LatitudeDMS,
    CardinalDirectionLatitude,
    LongitudeDMS,
    CardinalDirectionLongitude,
)


@pytest.fixture
def mock_serial(mocker: MockFixture) -> MagicMock:
    return mocker.patch("nexstar_control.device.serial.Serial")


@pytest.fixture
def mock_hand_control(mock_serial: MagicMock) -> NexStarHandControl:
    return NexStarHandControl(port="COM3")


def test_init(mock_serial: MagicMock) -> None:
    NexStarHandControl("COM1")
    mock_serial.assert_called_with("COM1", 9600, parity="N", timeout=3.5, write_timeout=3.5)


def test_init_raises_serial_exception_when_serial_open_fails(mock_serial: MagicMock) -> None:
    mock_serial.side_effect = serial.SerialException("Failed to open port")

    with pytest.raises(serial.SerialException, match="Failed to open port"):
        NexStarHandControl("COM1")


def test_destructor_closes_serial_port_if_open(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.__del__()
    mock_serial.return_value.close.assert_called()


def test_write_sends_command_to_device(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.write(b"command")
    mock_serial.return_value.write.assert_called_with(b"command")


def test_write_logs_debug_message_with_command(
    mock_hand_control: NexStarHandControl, caplog: pytest.LogCaptureFixture
) -> None:
    # temporarily set the logging level to debug
    caplog.set_level(logging.DEBUG)
    mock_hand_control.write(b"V")
    assert "Writing command b'V' to device..." in caplog.text


def test_write_command_raises_serial_exception_when_serial_port_is_not_open(
    mock_hand_control: NexStarHandControl,
) -> None:
    mock_hand_control.ser = None
    with pytest.raises(serial.SerialException, match="Serial port is not open"):
        mock_hand_control.write(b"V")


def test_query_sends_command_and_reads_response(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_serial.return_value.read_until.return_value = b"response#"
    response = mock_hand_control.query(b"command")
    mock_serial.return_value.write.assert_called_with(b"command")
    assert response == b"response"


def test_query_logs_debug_message_with_command_and_response(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    # temporarily set the logging level to debug
    caplog.set_level(logging.DEBUG)
    mock_serial.return_value.read_until.return_value = b"response#"
    mock_hand_control.query(b"V")
    assert "Writing command b'V' to device..." in caplog.text
    assert "Received response b'response#' from device" in caplog.text


def test_handle_position_response_with_precise_response_returns_correct_values(
    mock_hand_control: NexStarHandControl,
) -> None:
    encoded_x = round(2**32 / 4)  # 1/4 of a revolution - 90 degrees
    encoded_y = round(2**32 / 2)  # 1/2 of a revolution - 180 degrees
    precise_response = f"{encoded_x:08x},{encoded_y:08x}".encode("ascii")
    x, y = mock_hand_control._handle_position_response(precise_response, is_precise=True)
    assert x == pytest.approx(90.0)
    assert y == pytest.approx(180.0)


def test_handle_position_response_with_non_precise_response_returns_correct_values(
    mock_hand_control: NexStarHandControl,
) -> None:
    encoded_x = round(2**16 / 4)  # 1/4 of a revolution - 90 degrees
    encoded_y = round(2**16 / 2)  # 1/2 of a revolution - 180 degrees
    non_precise_response = f"{encoded_x:04x},{encoded_y:04x}".encode("ascii")
    x, y = mock_hand_control._handle_position_response(non_precise_response, is_precise=False)
    assert x == pytest.approx(90.0)
    assert y == pytest.approx(180.0)


def test_handle_position_response_with_precise_response_raises_assertion_error_for_incorrect_length(
    mock_hand_control: NexStarHandControl,
) -> None:
    incorrect_length_response = b"12345678,9abcdef"
    with pytest.raises(AssertionError):
        mock_hand_control._handle_position_response(incorrect_length_response, is_precise=True)


def test_handle_position_response_with_non_precise_response_raises_assertion_error_for_incorrect_length(
    mock_hand_control: NexStarHandControl,
) -> None:
    incorrect_length_response = b"123,abcd"
    with pytest.raises(AssertionError):
        mock_hand_control._handle_position_response(incorrect_length_response, is_precise=False)


def test_get_position_ra_dec_returns_correct_values(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"4000,8000#"
    ra, dec = mock_hand_control.get_position_ra_dec()
    assert ra == pytest.approx(90.0)
    assert dec == pytest.approx(180.0)


def test_get_position_ra_dec_precise_returns_correct_values(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"40000000,80000000#"
    ra, dec = mock_hand_control.get_position_ra_dec_precise()
    assert ra == pytest.approx(90.0)
    assert dec == pytest.approx(180.0)


def test_get_position_azm_alt_returns_correct_values(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"4000,8000#"
    azm, alt = mock_hand_control.get_position_azm_alt()
    assert azm == pytest.approx(90.0)
    assert alt == pytest.approx(180.0)


def test_get_position_azm_alt_precise_returns_correct_values(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"40000000,80000000#"
    azm, alt = mock_hand_control.get_position_azm_alt_precise()
    assert azm == pytest.approx(90.0)
    assert alt == pytest.approx(180.0)


def test_get_position_azm_alt_raises_assertion_error_for_incorrect_response_length(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"123,5678#"
    with pytest.raises(AssertionError):
        mock_hand_control.get_position_azm_alt()


def test_get_position_azm_alt_precise_raises_assertion_error_for_incorrect_response_length(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"123456,9abcdef0#"
    with pytest.raises(AssertionError):
        mock_hand_control.get_position_azm_alt_precise()


def test_goto_command_with_precise_ra_dec_receives_unexpected_response_logs_warning(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
):
    mock_hand_control.is_aligned = MagicMock(return_value=False)
    mock_serial.return_value.read_until.return_value = b"Unexpected response#"
    mock_hand_control.goto_ra_dec_precise(45.123, 30.456)
    assert "Telescope is not aligned" in caplog.text
    assert "Expected an empty response!" in caplog.text


def test_goto_ra_dec_sends_correct_command(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.is_aligned = MagicMock(return_value=True)
    mock_hand_control.goto_ra_dec(90, 180)
    mock_serial.return_value.write.assert_called_with(b"R4000,8000")


def test_goto_ra_dec_precise_sends_correct_command(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.is_aligned = MagicMock(return_value=True)
    mock_hand_control.goto_ra_dec_precise(90, 180)
    mock_serial.return_value.write.assert_called_with(b"r40000000,80000000")


def test_goto_azm_alt_sends_correct_command_for_non_precise_movement(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.is_aligned = MagicMock(return_value=True)
    mock_hand_control.goto_azm_alt(180, 90)
    mock_serial.return_value.write.assert_called_with(b"B8000,4000")


def test_goto_azm_alt_precise_sends_correct_command_for_precise_movement(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.is_aligned = MagicMock(return_value=True)
    mock_hand_control.goto_azm_alt_precise(180, 90)
    mock_serial.return_value.write.assert_called_with(b"b80000000,40000000")


def test_sync_ra_dec_sends_correct_command(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.sync_ra_dec(180, 90)
    mock_serial.return_value.write.assert_called_with(b"S8000,4000")


def test_sync_ra_dec_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.sync_ra_dec(180, 90)
    assert "Expected an empty response!" in caplog.text


def test_sync_ra_dec_precise_sends_correct_command(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.sync_ra_dec_precise(180, 90)
    mock_serial.return_value.write.assert_called_with(b"s80000000,40000000")


def test_sync_ra_dec_precise_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.sync_ra_dec_precise(180, 90)
    assert "Expected an empty response!" in caplog.text


def test_handle_variable_slew_rate_returns_correct_values_for_positive_rate() -> None:
    direction, rate_high, rate_low = NexStarHandControl._handle_variable_slew_rate(1000)
    assert direction == 6
    assert rate_high == 15
    assert rate_low == 160


def test_handle_variable_slew_rate_returns_correct_values_for_negative_rate() -> None:
    direction, rate_high, rate_low = NexStarHandControl._handle_variable_slew_rate(-1000)
    assert direction == 7
    assert rate_high == 15
    assert rate_low == 160


def test_handle_variable_slew_rate_returns_correct_values_for_max_positive_rate() -> None:
    direction, rate_high, rate_low = NexStarHandControl._handle_variable_slew_rate(16384)
    assert direction == 6
    assert rate_high == 256
    assert rate_low == 0


def test_handle_variable_slew_rate_returns_correct_values_for_max_negative_rate() -> None:
    direction, rate_high, rate_low = NexStarHandControl._handle_variable_slew_rate(-16384)
    assert direction == 7
    assert rate_high == 256
    assert rate_low == 0


def test_handle_variable_slew_rate_raises_assertion_error_for_rate_above_max() -> None:
    with pytest.raises(AssertionError):
        NexStarHandControl._handle_variable_slew_rate(16385)


def test_handle_variable_slew_rate_raises_assertion_error_for_rate_below_min() -> None:
    with pytest.raises(AssertionError):
        NexStarHandControl._handle_variable_slew_rate(-16385)


def test_slew_variable_sends_correct_commands_for_azm_and_alt(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.slew_variable(1000, -500)
    calls = [call(bytes([80, 3, 16, 6, 15, 160, 0, 0])), call(bytes([80, 3, 17, 7, 7, 208, 0, 0]))]
    mock_serial.return_value.write.assert_has_calls(calls)


def test_slew_azm_variable_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.slew_variable(1000, 0)
    assert "Expected an empty response!" in caplog.text


def test_slew_azm_fixed_sends_correct_command_for_negative_rate(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.slew_azm_fixed(-5)
    mock_serial.return_value.write.assert_called_with(bytes([80, 2, 16, 37, 5, 0, 0, 0]))


def test_slew_azm_fixed_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.slew_azm_fixed(-5)
    assert "Expected an empty response!" in caplog.text


def test_slew_fixed_sends_correct_commands_for_azm_and_alt(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_hand_control.slew_fixed(5, -3)
    calls = [call(bytes([80, 2, 16, 36, 5, 0, 0, 0])), call(bytes([80, 2, 17, 37, 3, 0, 0, 0]))]
    mock_serial.return_value.write.assert_has_calls(calls)


def test_slew_alt_fixed_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.slew_fixed(0, -3)
    assert "Expected an empty response!" in caplog.text


def test_slew_stop_sends_correct_command(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.slew_stop()
    calls = [call(bytes([80, 2, 16, 36, 0, 0, 0, 0])), call(bytes([80, 2, 17, 36, 0, 0, 0, 0]))]
    mock_serial.return_value.write.assert_has_calls(calls)


def test_set_tracking_mode_sends_correct_command(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.set_tracking_mode(TrackingMode.ALT_AZ)
    mock_serial.return_value.write.assert_called_with(bytes([84, 1]))


def test_set_tracking_mode_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.set_tracking_mode(TrackingMode.ALT_AZ)
    assert "Expected an empty response!" in caplog.text


def test_get_tracking_mode_returns_correct_mode(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_serial.return_value.read_until.return_value = b"\x02#"
    mode = mock_hand_control.get_tracking_mode()
    assert mode == TrackingMode.EQ_NORTH


def test_get_tracking_mode_raises_assertion_error_for_incorrect_response_length(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x02\x03#"
    with pytest.raises(AssertionError):
        mock_hand_control.get_tracking_mode()


def test_get_device_version_returns_major_and_minor(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x01\x02#"
    major, minor = mock_hand_control.get_device_version(DeviceType.GPS_UNIT)
    assert major == 1
    assert minor == 2


def test_get_device_model_returns_correct_model(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_serial.return_value.read_until.return_value = b"\x09#"
    model = mock_hand_control.get_device_model()
    assert model == DeviceModel.CPC


def test_is_connected_returns_true_when_connected(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"x#"
    assert mock_hand_control.is_connected() is True


def test_is_connected_returns_false_when_not_connected(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"y#"
    assert mock_hand_control.is_connected() is False


def test_is_aligned_returns_true_when_aligned(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_serial.return_value.read_until.return_value = b"\x01#"
    assert mock_hand_control.is_aligned() is True


def test_is_aligned_returns_false_when_not_aligned(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x00#"
    assert mock_hand_control.is_aligned() is False


def test_is_goto_in_progress_returns_true_when_in_progress(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    assert mock_hand_control.is_goto_in_progress() is True


def test_is_goto_in_progress_returns_false_when_not_in_progress(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"0#"
    assert mock_hand_control.is_goto_in_progress() is False


def test_cancel_goto_sends_correct_command(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_hand_control.cancel_goto()
    mock_serial.return_value.write.assert_called_with(b"M")


def test_cancel_goto_logs_warning_when_response_length_is_incorrect(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.cancel_goto()
    assert "Expected an empty response!" in caplog.text


def test_converts_positive_decimal_to_dms() -> None:
    assert to_dms(121.135) == (121, 8, 6)


def test_converts_negative_decimal_to_dms_and_ignores_sign() -> None:
    assert to_dms(-121.135) == (121, 8, 6)


def test_converts_zero_decimal_to_dms() -> None:
    assert to_dms(0) == (0, 0, 0)


def test_converts_decimal_with_only_degrees_to_dms() -> None:
    assert to_dms(45.0) == (45, 0, 0)


def test_converts_decimal_with_degrees_and_minutes_to_dms() -> None:
    assert to_dms(45.5) == (45, 30, 0)


def test_converts_decimal_close_to_next_degree_to_dms() -> None:
    assert to_dms(-45.9999) == (45, 59, 59)


def test_handles_large_decimal_values() -> None:
    assert to_dms(359.9999) == (359, 59, 59)


def test_latitude_creation_with_valid_values() -> None:
    latitude = LatitudeDMS(45, 30, 15, CardinalDirectionLatitude.NORTH)
    assert latitude.degrees == 45
    assert latitude.minutes == 30
    assert latitude.seconds == 15
    assert latitude.direction == CardinalDirectionLatitude.NORTH


def test_latitude_creation_raises_assertion_for_invalid_degrees() -> None:
    with pytest.raises(AssertionError):
        LatitudeDMS(91, 0, 0, CardinalDirectionLatitude.NORTH)

    with pytest.raises(AssertionError):
        LatitudeDMS(-1, 0, 0, CardinalDirectionLatitude.NORTH)


def test_latitude_creation_raises_assertion_for_invalid_minutes() -> None:
    with pytest.raises(AssertionError):
        LatitudeDMS(0, 60, 0, CardinalDirectionLatitude.NORTH)

    with pytest.raises(AssertionError):
        LatitudeDMS(0, -1, 0, CardinalDirectionLatitude.NORTH)


def test_latitude_creation_raises_assertion_for_invalid_seconds() -> None:
    with pytest.raises(AssertionError):
        LatitudeDMS(0, 0, 60, CardinalDirectionLatitude.NORTH)

    with pytest.raises(AssertionError):
        LatitudeDMS(0, 0, -1, CardinalDirectionLatitude.NORTH)


def test_latitude_to_decimal_conversion_north() -> None:
    latitude = LatitudeDMS(45, 30, 0, CardinalDirectionLatitude.NORTH)
    assert latitude.to_decimal() == 45.5


def test_latitude_to_decimal_conversion_south() -> None:
    latitude = LatitudeDMS(45, 30, 15, CardinalDirectionLatitude.SOUTH)
    assert pytest.approx(latitude.to_decimal()) == -45.504167


def test_latitude_from_decimal_positive_value() -> None:
    latitude = LatitudeDMS.from_decimal(45.5)
    assert latitude.degrees == 45
    assert latitude.minutes == 30
    assert latitude.seconds == 0
    assert latitude.direction == CardinalDirectionLatitude.NORTH


def test_latitude_from_decimal_negative_value() -> None:
    latitude = LatitudeDMS.from_decimal(-45.5)
    assert latitude.degrees == 45
    assert latitude.minutes == 30
    assert latitude.seconds == 0
    assert latitude.direction == CardinalDirectionLatitude.SOUTH


def test_latitude_string_representation() -> None:
    latitude = LatitudeDMS(45, 30, 0, CardinalDirectionLatitude.NORTH)
    assert str(latitude) == "45° 30' 0\" N"

    latitude = LatitudeDMS(45, 30, 15, CardinalDirectionLatitude.SOUTH)
    assert str(latitude) == "45° 30' 15\" S"


def test_longitude_creation_with_valid_values() -> None:
    longitude = LongitudeDMS(120, 45, 30, CardinalDirectionLongitude.EAST)
    assert longitude.degrees == 120
    assert longitude.minutes == 45
    assert longitude.seconds == 30
    assert longitude.direction == CardinalDirectionLongitude.EAST


def test_longitude_creation_raises_assertion_for_invalid_degrees() -> None:
    with pytest.raises(AssertionError):
        LongitudeDMS(181, 0, 0, CardinalDirectionLongitude.EAST)


def test_longitude_creation_raises_assertion_for_invalid_minutes() -> None:
    with pytest.raises(AssertionError):
        LongitudeDMS(0, 60, 0, CardinalDirectionLongitude.EAST)


def test_longitude_creation_raises_assertion_for_invalid_seconds() -> None:
    with pytest.raises(AssertionError):
        LongitudeDMS(0, 0, 60, CardinalDirectionLongitude.EAST)


def test_longitude_to_decimal_conversion_east() -> None:
    longitude = LongitudeDMS(120, 45, 30, CardinalDirectionLongitude.EAST)
    assert longitude.to_decimal() == 120.75833333333334


def test_longitude_to_decimal_conversion_west() -> None:
    longitude = LongitudeDMS(120, 45, 30, CardinalDirectionLongitude.WEST)
    assert longitude.to_decimal() == -120.75833333333334


def test_longitude_from_decimal_positive_value() -> None:
    longitude = LongitudeDMS.from_decimal(120.75833333333334)
    assert longitude.degrees == 120
    assert longitude.minutes == 45
    assert longitude.seconds == 30
    assert longitude.direction == CardinalDirectionLongitude.EAST


def test_longitude_from_decimal_negative_value() -> None:
    longitude = LongitudeDMS.from_decimal(-120.75833333333334)
    assert longitude.degrees == 120
    assert longitude.minutes == 45
    assert longitude.seconds == 30
    assert longitude.direction == CardinalDirectionLongitude.WEST


def test_longitude_string_representation() -> None:
    longitude = LongitudeDMS(120, 45, 30, CardinalDirectionLongitude.EAST)
    assert str(longitude) == "120° 45' 30\" E"

    longitude = LongitudeDMS(120, 45, 30, CardinalDirectionLongitude.WEST)
    assert str(longitude) == "120° 45' 30\" W"


def test_get_location_returns_correct_latitude_and_longitude(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x30\x2e\x30\x00\x78\x2e\x30\x01#"
    lat, lon = mock_hand_control.get_location()
    assert (
        lat.degrees == 48
        and lat.minutes == 46
        and lat.seconds == 48
        and lat.direction == CardinalDirectionLatitude.NORTH
    )
    assert (
        lon.degrees == 120
        and lon.minutes == 46
        and lon.seconds == 48
        and lon.direction == CardinalDirectionLongitude.WEST
    )


def test_get_location_handles_invalid_response_length(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x30\x2e\x30\x00"
    with pytest.raises(AssertionError):
        mock_hand_control.get_location()


def test_get_location_handles_invalid_latitude_direction(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    # Invalid direction value for latitude
    mock_serial.return_value.read_until.return_value = b"\x30\x2e\x30\x00\x78\x2e\x30\x02"
    with pytest.raises(ValueError):
        mock_hand_control.get_location()


def test_get_location_handles_invalid_longitude_direction(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    # Invalid direction value for longitude
    mock_serial.return_value.read_until.return_value = b"\x30\x2e\x30\x00\x78\x2e\x30\x03"
    with pytest.raises(ValueError):
        mock_hand_control.get_location()


def test_set_location_sends_correct_commands(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    mock_serial.return_value.read_until.return_value = b"#"
    mock_hand_control.set_location(
        LatitudeDMS(45, 30, 0, CardinalDirectionLatitude.SOUTH),
        LongitudeDMS(120, 45, 0, CardinalDirectionLongitude.EAST),
    )
    mock_serial.return_value.write.assert_called_with(bytes([87, 45, 30, 0, 1, 120, 45, 0, 0]))


def test_set_location_receives_unexpected_response_logs_warning(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    mock_hand_control.set_location(
        LatitudeDMS(45, 30, 0, CardinalDirectionLatitude.SOUTH),
        LongitudeDMS(120, 45, 0, CardinalDirectionLongitude.EAST),
    )
    mock_serial.return_value.write.assert_called_with(bytes([87, 45, 30, 0, 1, 120, 45, 0, 0]))
    assert "Expected an empty response!" in caplog.text


def test_get_time_returns_correct_datetime_for_valid_response(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x07\x1e\x1c\x04\x0a\x14\x0b\x00#"
    expected_datetime = datetime.datetime(
        2020, 4, 10, 7, 30, 28, tzinfo=datetime.timezone(datetime.timedelta(hours=11))
    )
    assert mock_hand_control.get_time() == expected_datetime


def test_get_time_raises_assertion_error_for_invalid_response_length(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x07\x1e\x1c\x04\x0a\x14\x0b#"
    with pytest.raises(AssertionError):
        mock_hand_control.get_time()


def test_get_time_handles_negative_timezone_offset_correctly(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x07\x1e\x1c\x04\x0a\x14\xef\x00#"
    expected_datetime = datetime.datetime(
        2020, 4, 10, 7, 30, 28, tzinfo=datetime.timezone(datetime.timedelta(hours=-17))
    )
    assert mock_hand_control.get_time() == expected_datetime


def test_get_time_accounts_for_daylight_saving_time(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock
) -> None:
    mock_serial.return_value.read_until.return_value = b"\x07\x1e\x1c\x04\x0a\x14\x0b\x01"
    expected_datetime = datetime.datetime(
        2020, 4, 10, 7, 30, 28, tzinfo=datetime.timezone(datetime.timedelta(hours=12))
    )
    assert mock_hand_control.get_time() == expected_datetime


def test_sets_time_with_positive_timezone_offset(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    time_to_set = datetime.datetime(2023, 5, 17, 15, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=5)))
    mock_hand_control.set_time(time_to_set)
    mock_serial.return_value.write.assert_called_with(b"H\x0f\x1e-\x05\x11\x17\x05\x01")


def test_sets_time_with_negative_timezone_offset(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    time_to_set = datetime.datetime(2023, 5, 17, 15, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=-7)))
    mock_hand_control.set_time(time_to_set)
    mock_serial.return_value.write.assert_called_with(b"H\x0f\x1e-\x05\x11\x17\xf9\x01")


def test_sets_time_without_daylight_saving_time(mock_hand_control: NexStarHandControl, mock_serial: MagicMock) -> None:
    # standard time is in January for Vancouver
    time_to_set = datetime.datetime(2023, 1, 17, 15, 30, 45, tzinfo=ZoneInfo("America/Vancouver"))
    mock_hand_control.set_time(time_to_set)
    mock_serial.return_value.write.assert_called_with(b"H\x0f\x1e-\x01\x11\x17\xf8\x00")


def test_set_time_receives_unexpected_response_logs_warning(
    mock_hand_control: NexStarHandControl, mock_serial: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_serial.return_value.read_until.return_value = b"1#"
    time_to_set = datetime.datetime(2023, 5, 17, 15, 30, 45, tzinfo=datetime.timezone.utc)
    mock_hand_control.set_time(time_to_set)
    mock_serial.return_value.write.assert_called_with(b"H\x0f\x1e-\x05\x11\x17\x00\x01")
    assert "Expected an empty response!" in caplog.text
