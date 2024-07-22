#
# Copyright Tristen Georgiou 2024
#
import enum
import logging

import serial


log = logging.getLogger(__name__)

ENCODING = "ascii"


class DeviceType(enum.Enum):
    """
    Device types for the Celestron NexStar Hand Control
    """

    AZM_RA_MOTOR = 16
    ALT_DEC_MOTOR = 17
    GPS_UNIT = 176
    RTC = 178  # CGE only


class DeviceModel(enum.Enum):
    """
    Device models for the Celestron NexStar Hand Control
    """

    GPS_SERIES = 1
    I_SERIES = 3
    I_SERIES_SE = 4
    CGE = 5
    ADVANCED_GT = 6
    SLT = 7
    CPC = 9
    GT = 10
    SE_4_5 = 11
    SE_6_8 = 12


class TrackingMode(enum.Enum):
    """
    Tracking modes for the Celestron NexStar Hand Control
    """

    OFF = 0
    ALT_AZ = 1
    EQ_NORTH = 2
    EQ_SOUTH = 3


class NexStarHandControl:
    """
    Class to communicate with the Celestron NexStar Hand Control and connected devices
    """

    # constants that handle conversions between percentages of a revolution and degrees
    CONVERSION = 2**16 / 360
    CONVERSION_PRECISE = 2**32 / 360

    def __init__(self, port: str):
        """
        Creates serial device to communicate with the Celestron NexStar Hand Control and connected devices

        According to the documentation "Communication to the hand control is 9600 bits/sec, no parity and one stop bit"
        Software drivers should be prepared to wait up to 3.5s (worst case scenario) for a hand control response

        :param port: The serial port the device is connected to
        """
        self.port = port
        self.baudrate = 9600
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.timeout = 3.5
        self.ser = None

        try:
            log.info(f"Opening serial port {port}...")
            self.ser = serial.Serial(
                port, self.baudrate, parity=self.parity, timeout=self.timeout, write_timeout=self.timeout
            )

            log.info(f"Successfully opened serial port {port}")
        except serial.SerialException:
            log.exception(f"Failed to open serial port {port}")
            raise

    def __del__(self) -> None:
        if self.ser is not None:
            log.info(f"Closing serial port {self.port}...")
            self.ser.close()
            log.info(f"Successfully closed serial port {self.port}")

    def write(self, command: bytes) -> None:
        """
        Writes a command to the device without reading a response.

        :param command: The command to write to the device
        :raises serial.SerialException: If the serial port is not open
        """
        if self.ser is None:
            raise serial.SerialException("Serial port is not open")

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Writing command {command} to device...")

        self.ser.write(command)

    def query(self, command: bytes) -> bytes:
        """
        Sends a command to the device and returns the response

        :param command: The command to send to the device
        :return: The response from the device
        :raises serial.SerialException: If the serial port is not open
        """
        self.write(command)
        resp = self.ser.read_until(b"#")

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Received response {resp} from device")

        return resp.strip(b"#")

    def _handle_position_response(self, response: bytes, is_precise: bool) -> tuple[float, float]:
        """
        Handles a position response from the device

        :param response: The response from the device
        :param is_precise: True if the response is precise, False otherwise
        :return: A tuple of floats in degrees
        """
        if is_precise:
            assert len(response) == 17, f"Expected a response with 17 bytes! Actual response was '{response}'"
        else:
            assert len(response) == 9, f"Expected a response with 9 bytes! Actual response was '{response}'"
        x, y = response.split(b",")
        if is_precise:
            x = int(x, base=16) / self.CONVERSION_PRECISE
            y = int(y, base=16) / self.CONVERSION_PRECISE
        else:
            x = int(x, base=16) / self.CONVERSION
            y = int(y, base=16) / self.CONVERSION
        return x, y

    def get_position_ra_dec(self) -> tuple[float, float]:
        """
        Returns the current right ascension and declination position in degrees

        :return: The current right ascension and declination position as a tuple of floats
        """
        response = self.query(b"E")
        return self._handle_position_response(response, is_precise=False)

    def get_position_ra_dec_precise(self) -> tuple[float, float]:
        """
        Returns the current right ascension and declination position in degrees with highest precision

        :return: The current right ascension and declination position as a tuple of floats
        """
        response = self.query(b"e")
        return self._handle_position_response(response, is_precise=True)

    def get_position_azm_alt(self) -> tuple[float, float]:
        """
        Returns the current azimuth and altitude position in degrees

        :return: The current azimuth and altitude position as a tuple of floats
        """
        response = self.query(b"Z")
        return self._handle_position_response(response, is_precise=False)

    def get_position_azm_alt_precise(self) -> tuple[float, float]:
        """
        Returns the current azimuth and altitude position in degrees with highest precision

        :return: The current azimuth and altitude position as a tuple of floats
        """
        response = self.query(b"z")
        return self._handle_position_response(response, is_precise=True)

    def _handle_goto_command(self, x: float, y: float, is_precise: bool, is_ra_dec: bool) -> None:
        """
        Handles a goto command

        :param x: The x position in degrees
        :param y: The y position in degrees
        :param is_precise: True if the command should be precise, False otherwise
        :param is_ra_dec: True if the command is for RA/Dec, False if it is for Azm/Alt
        """
        if not self.is_aligned():
            log.warning("Telescope is not aligned - goto operation may have unpredictable results")

        command = "R" if is_ra_dec else "B"  # RA/Dec or Azm/Alt
        if is_precise:
            command = command.lower()
            x = round(x * self.CONVERSION_PRECISE)
            y = round(y * self.CONVERSION_PRECISE)
            response = self.query(f"{command}{x:08x},{y:08x}".encode(ENCODING))
        else:
            x = round(x * self.CONVERSION)
            y = round(y * self.CONVERSION)
            response = self.query(f"{command}{x:04x},{y:04x}".encode(ENCODING))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def goto_ra_dec(self, ra: float, dec: float) -> None:
        """
        Moves the telescope to the specified right ascension and declination position in degrees

        :param ra: The right ascension position in degrees
        :param dec: The declination position in degrees
        """
        self._handle_goto_command(ra, dec, is_precise=False, is_ra_dec=True)

    def goto_ra_dec_precise(self, ra: float, dec: float) -> None:
        """
        Moves the telescope to the specified right ascension and declination position in degrees with highest precision

        :param ra: The right ascension position in degrees
        :param dec: The declination position in degrees
        """
        self._handle_goto_command(ra, dec, is_precise=True, is_ra_dec=True)

    def goto_azm_alt(self, azm: float, alt: float) -> None:
        """
        Moves the telescope to the specified azimuth and altitude position in degrees

        :param azm: The azimuth position in degrees
        :param alt: The altitude position in degrees
        """
        self._handle_goto_command(azm, alt, is_precise=False, is_ra_dec=False)

    def goto_azm_alt_precise(self, azm: float, alt: float) -> None:
        """
        Moves the telescope to the specified azimuth and altitude position in degrees with highest precision

        :param azm: The azimuth position in degrees
        :param alt: The altitude position in degrees
        """
        self._handle_goto_command(azm, alt, is_precise=True, is_ra_dec=False)

    def sync_ra_dec(self, ra: float, dec: float) -> None:
        """
        Syncs the telescope to the specified right ascension and declination position in degrees

        :param ra: The right ascension position in degrees
        :param dec: The declination position in degrees
        """
        x = round(ra * self.CONVERSION)
        y = round(dec * self.CONVERSION)
        response = self.query(f"S{x:04x},{y:04x}".encode(ENCODING))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def sync_ra_dec_precise(self, ra: float, dec: float) -> None:
        """
        Syncs the telescope to the specified right ascension and declination position in degrees with highest precision

        :param ra: The right ascension position in degrees
        :param dec: The declination position in degrees
        """
        x = round(ra * self.CONVERSION_PRECISE)
        y = round(dec * self.CONVERSION_PRECISE)
        response = self.query(f"s{x:08x},{y:08x}".encode(ENCODING))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    @staticmethod
    def _handle_variable_slew_rate(rate: int) -> tuple[int, int, int]:
        """
        Determines the direction and the high and low bytes for a variable slew rate

        :param rate: The variable slew rate in arcseconds/second
        :return: A tuple of direction, rate_high, rate_low
        """
        assert -16384 <= rate <= 16384, f"Rate must be between -16384 and 16384! Actual rate was '{rate}'"

        direction = 6
        if rate < 0:
            direction = 7  # reverse
            rate = abs(rate)

        rate_high = (rate * 4) // 256
        rate_low = (rate * 4) % 256

        return direction, rate_high, rate_low

    def slew_azm_variable(self, rate: int) -> None:
        """
        Slew the telescope at a variable rate in azimuth

        :param rate: The variable slew rate in arcseconds/second, negative values are reverse
        """
        direction, rate_high, rate_low = self._handle_variable_slew_rate(rate)
        response = self.query(bytes([80, 3, 16, direction, rate_high, rate_low, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def slew_alt_variable(self, rate: int) -> None:
        """
        Slew the telescope at a variable rate in altitude

        :param rate: The variable slew rate in arcseconds/second, negative values are reverse
        """
        direction, rate_high, rate_low = self._handle_variable_slew_rate(rate)
        response = self.query(bytes([80, 3, 17, direction, rate_high, rate_low, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def slew_variable(self, azm_rate: int, alt_rate: int) -> None:
        """
        Slew the telescope at a variable rate in azimuth and altitude simultaneously

        :param azm_rate: The variable slew rate in arcseconds/second for azimuth, negative values are reverse
        :param alt_rate: The variable slew rate in arcseconds/second for altitude, negative values are reverse
        """
        self.slew_azm_variable(azm_rate)
        self.slew_alt_variable(alt_rate)

    def slew_azm_fixed(self, rate: int) -> None:
        """
        Slew the telescope at a fixed rate in azimuth

        :param rate: The fixed slew rate to use [-9, 9] where 0 is stop and negative values are reverse
        """
        assert -9 <= rate <= 9, f"Rate must be between -9 and 9! Actual rate was '{rate}'"

        direction = 36
        if rate < 0:
            direction = 37  # reverse
            rate = abs(rate)

        response = self.query(bytes([80, 2, 16, direction, rate, 0, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def slew_alt_fixed(self, rate: int) -> None:
        """
        Slew the telescope at a fixed rate in altitude

        :param rate: The fixed slew rate to use [-9, 9] where 0 is stop and negative values are reverse
        """
        assert -9 <= rate <= 9, f"Rate must be between -9 and 9! Actual rate was '{rate}'"

        direction = 36
        if rate < 0:
            direction = 37  # reverse
            rate = abs(rate)

        response = self.query(bytes([80, 2, 17, direction, rate, 0, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def slew_fixed(self, azm_rate: int, alt_rate: int) -> None:
        """
        Slew the telescope at a fixed rate in azimuth and altitude simultaneously

        :param azm_rate: The fixed slew rate to use in azimuth [-9, 9] where 0 is stop and negative values are reverse
        :param alt_rate: The fixed slew rate to use in altitude [-9, 9] where 0 is stop and negative values are reverse
        """
        self.slew_azm_fixed(azm_rate)
        self.slew_alt_fixed(alt_rate)

    def slew_stop(self) -> None:
        """
        Stops the telescope from slewing in both azimuth and altitude
        """
        self.slew_fixed(0, 0)

    def get_tracking_mode(self) -> TrackingMode:
        """
        Returns the current tracking mode

        :return: The current tracking mode
        """
        response = self.query(b"t")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was '{response}'"
        return TrackingMode(response[0])

    def set_tracking_mode(self, mode: TrackingMode) -> None:
        """
        Sets the tracking mode

        :param mode: The tracking mode to set
        """
        response = self.query(bytes([84, mode.value]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")

    def get_device_version(self, device_type: DeviceType) -> tuple[int, int]:
        """
        Returns the device version

        :param device_type: The type of device to get the version of
        :return: The device version as a tuple of major and minor version numbers
        """
        response = self.query(bytes([80, 1, device_type.value, 254, 0, 0, 0, 2]))
        assert len(response) == 2, f"Expected a response with 2 bytes! Actual response was '{response}'"
        return int(response[0]), int(response[1])

    def get_device_model(self) -> DeviceModel:
        """
        Returns the device model

        :return: The device model
        """
        response = self.query(b"m")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was '{response}'"
        return DeviceModel(response[0])

    def is_connected(self) -> bool:
        """
        Checks if the device is connected

        :return: True if the device is connected, False otherwise
        """
        response = self.query(b"Kx")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was '{response}'"
        return response == b"x"

    def is_aligned(self) -> bool:
        """
        Checks if the alignment has been completed

        :return: True if the alignment is complete, False otherwise
        """
        response = self.query(b"J")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was '{response}'"
        return response == b"\x01"

    def is_goto_in_progress(self) -> bool:
        """
        Checks if a goto operation is in progress (NOTE: The response is ASCII 1 or 0!)

        :return: True if a goto operation is in progress, False otherwise
        """
        response = self.query(b"L")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was '{response}'"
        return response.decode(ENCODING) == "1"

    def cancel_goto(self) -> None:
        """
        Cancels the current goto operation
        """
        response = self.query(b"M")
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was '{response}'")
