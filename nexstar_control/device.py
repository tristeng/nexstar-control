#
# Copyright Tristen Georgiou 2024
#
import datetime
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


class CardinalDirectionLatitude(enum.Enum):
    """
    Cardinal directions for latitude
    """

    NORTH = 0
    SOUTH = 1


class CardinalDirectionLongitude(enum.Enum):
    """
    Cardinal directions for longitude
    """

    EAST = 0
    WEST = 1


def to_dms(value: float) -> tuple[int, int, int]:
    """
    Converts a decimal value to degrees, minutes, and seconds
    NOTE: This function converts negative values to positive - user is responsible for direction

    :param value: The decimal value to convert
    :return: A tuple of degrees, minutes, and seconds
    """
    value = abs(value)
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = int((value - degrees - minutes / 60) * 3600)
    return degrees, minutes, seconds


class LatitudeDMS:
    """
    Class to represent latitude in degrees, minutes, and seconds
    """

    def __init__(self, degrees: int, minutes: int, seconds: int, direction: CardinalDirectionLatitude):
        """
        Creates a latitude object

        :param degrees: the degrees of the latitude
        :param minutes: the minutes of the latitude
        :param seconds: the seconds of the latitude
        :param direction: the direction of the latitude
        :raises AssertionError: if the degrees, minutes, or seconds are out of range
        """
        assert 0 <= degrees <= 90, f"Degrees must be between 0 and 90! Actual degrees was '{degrees}'"
        assert 0 <= minutes <= 59, f"Minutes must be between 0 and 59! Actual minutes was '{minutes}'"
        assert 0 <= seconds <= 59, f"Seconds must be between 0 and 59! Actual seconds was '{seconds}'"
        self.degrees = degrees
        self.minutes = minutes
        self.seconds = seconds
        self.direction = direction

    def __str__(self) -> str:
        """
        Returns a user friendly string representation of the latitude

        :return: a string representation of the latitude
        """
        return f"{self.degrees}° {self.minutes}' {self.seconds}\" {self.direction.name[0]}"

    def to_decimal(self) -> float:
        """
        Converts the latitude to decimal degrees

        :return: the latitude in decimal degrees
        """
        absval = self.degrees + self.minutes / 60 + self.seconds / 3600
        return absval if self.direction == CardinalDirectionLatitude.NORTH else -absval

    @staticmethod
    def from_decimal(value: float) -> "LatitudeDMS":
        """
        Converts a decimal value to a latitude

        :param value: The decimal value to convert
        """
        assert -90 <= value <= 90, f"Value must be between -90 and 90! Actual value was '{value}'"

        direction = CardinalDirectionLatitude.NORTH if value >= 0 else CardinalDirectionLatitude.SOUTH
        degrees, minutes, seconds = to_dms(value)
        return LatitudeDMS(degrees, minutes, seconds, direction)


class LongitudeDMS:
    """
    Class to represent longitude in degrees, minutes, and seconds
    """

    def __init__(self, degrees: int, minutes: int, seconds: int, direction: CardinalDirectionLongitude):
        """
        Creates a longitude object

        :param degrees: the degrees of the longitude
        :param minutes: the minutes of the longitude
        :param seconds: the seconds of the longitude
        :param direction: the direction of the longitude
        :raises AssertionError: if the degrees, minutes, or seconds are out of range
        """
        assert 0 <= degrees <= 180, f"Degrees must be between 0 and 180! Actual degrees was '{degrees}'"
        assert 0 <= minutes <= 59, f"Minutes must be between 0 and 59! Actual minutes was '{minutes}'"
        assert 0 <= seconds <= 59, f"Seconds must be between 0 and 59! Actual seconds was '{seconds}'"
        self.degrees = degrees
        self.minutes = minutes
        self.seconds = seconds
        self.direction = direction

    def __str__(self) -> str:
        """
        Returns a user friendly string representation of the longitude

        :return: a string representation of the longitude
        """
        return f"{self.degrees}° {self.minutes}' {self.seconds}\" {self.direction.name[0]}"

    def to_decimal(self) -> float:
        """
        Converts the longitude to decimal degrees

        :return: the longitude in decimal degrees
        """
        absval = self.degrees + self.minutes / 60 + self.seconds / 3600
        return absval if self.direction == CardinalDirectionLongitude.EAST else -absval

    @staticmethod
    def from_decimal(value: float) -> "LongitudeDMS":
        """
        Converts a decimal value to a longitude

        :param value: The decimal value to convert
        """
        assert -180 <= value <= 180, f"Value must be between -180 and 180! Actual value was '{value}'"

        direction = CardinalDirectionLongitude.EAST if value >= 0 else CardinalDirectionLongitude.WEST
        degrees, minutes, seconds = to_dms(value)
        return LongitudeDMS(degrees, minutes, seconds, direction)


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
            assert len(response) == 17, f"Expected a response with 17 bytes! Actual response was {response}"
        else:
            assert len(response) == 9, f"Expected a response with 9 bytes! Actual response was {response}"
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
            log.warning(f"Expected an empty response! Actual response was {response}")

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
            log.warning(f"Expected an empty response! Actual response was {response}")

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
            log.warning(f"Expected an empty response! Actual response was {response}")

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
        response = self.query(bytes([ord("P"), 3, 16, direction, rate_high, rate_low, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

    def slew_alt_variable(self, rate: int) -> None:
        """
        Slew the telescope at a variable rate in altitude

        :param rate: The variable slew rate in arcseconds/second, negative values are reverse
        """
        direction, rate_high, rate_low = self._handle_variable_slew_rate(rate)
        response = self.query(bytes([ord("P"), 3, 17, direction, rate_high, rate_low, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

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

        response = self.query(bytes([ord("P"), 2, 16, direction, rate, 0, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

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

        response = self.query(bytes([ord("P"), 2, 17, direction, rate, 0, 0, 0]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

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

    def get_location(self) -> tuple[LatitudeDMS, LongitudeDMS]:
        """
        Returns the current location of the telescope

        :return: A tuple of the latitude and longitude
        """
        response = self.query(b"w")
        assert len(response) == 8, f"Expected a response with 8 bytes! Actual response was {response}"
        lat_deg, lat_min, lat_sec, lat_dir = response[0], response[1], response[2], response[3]
        lon_deg, lon_min, lon_sec, lon_dir = response[4], response[5], response[6], response[7]
        return (
            LatitudeDMS(lat_deg, lat_min, lat_sec, CardinalDirectionLatitude(lat_dir)),
            LongitudeDMS(lon_deg, lon_min, lon_sec, CardinalDirectionLongitude(lon_dir)),
        )

    def set_location(self, lat: LatitudeDMS, lng: LongitudeDMS) -> None:
        """
        Sets the location of the telescope

        :param lat: The latitude of the telescope
        :param lng: The longitude of the telescope
        """
        response = self.query(
            bytes(
                [
                    ord("W"),
                    lat.degrees,
                    lat.minutes,
                    lat.seconds,
                    lat.direction.value,
                    lng.degrees,
                    lng.minutes,
                    lng.seconds,
                    lng.direction.value,
                ]
            )
        )
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

    def get_time(self) -> datetime.datetime:
        """
        Returns the current time of the telescope

        :return: The current time of the telescope
        """
        response = self.query(b"h")
        assert len(response) == 8, f"Expected a response with 8 bytes! Actual response was {response}"
        hour, minute, second, month, day, year, zone_offset, dst = (
            response[0],
            response[1],
            response[2],
            response[3],
            response[4],
            response[5],
            response[6],
            response[7],
        )
        if zone_offset > 24:
            # negative offsets are encoded as 256 - offset
            zone_offset -= 256
        if dst == 1:
            # DST is automatically applied during set, so doesn't need to be re-applied when getting time
            log.info("Daylight Savings Time is active")
        tz = datetime.timezone(datetime.timedelta(hours=zone_offset))
        return datetime.datetime(year + 2000, month, day, hour, minute, second, tzinfo=tz)

    def set_time(self, time: datetime.datetime) -> None:
        """
        Sets the time of the telescope

        :param time: The time to set
        """
        zone_offset = int(time.utcoffset().total_seconds() // 3600)
        # if zone offset is negative, it is encoded as 256 - offset
        if zone_offset < 0:
            zone_offset += 256
        dst = 1 if time.dst() != datetime.timedelta(0) else 0
        response = self.query(
            bytes(
                [
                    ord("H"),
                    time.hour,
                    time.minute,
                    time.second,
                    time.month,
                    time.day,
                    time.year - 2000,
                    zone_offset,
                    dst,
                ]
            )
        )
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

    def get_tracking_mode(self) -> TrackingMode:
        """
        Returns the current tracking mode

        :return: The current tracking mode
        """
        response = self.query(b"t")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was {response}"
        return TrackingMode(response[0])

    def set_tracking_mode(self, mode: TrackingMode) -> None:
        """
        Sets the tracking mode

        :param mode: The tracking mode to set
        """
        response = self.query(bytes([84, mode.value]))
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")

    def get_device_version(self, device_type: DeviceType) -> tuple[int, int]:
        """
        Returns the device version

        :param device_type: The type of device to get the version of
        :return: The device version as a tuple of major and minor version numbers
        """
        response = self.query(bytes([80, 1, device_type.value, 254, 0, 0, 0, 2]))
        assert len(response) == 2, f"Expected a response with 2 bytes! Actual response was {response}"
        return int(response[0]), int(response[1])

    def get_device_model(self) -> DeviceModel:
        """
        Returns the device model

        :return: The device model
        """
        response = self.query(b"m")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was {response}"
        return DeviceModel(response[0])

    def is_connected(self) -> bool:
        """
        Checks if the device is connected

        :return: True if the device is connected, False otherwise
        """
        response = self.query(b"Kx")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was {response}"
        return response == b"x"

    def is_aligned(self) -> bool:
        """
        Checks if the alignment has been completed

        :return: True if the alignment is complete, False otherwise
        """
        response = self.query(b"J")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was {response}"
        return response == b"\x01"

    def is_goto_in_progress(self) -> bool:
        """
        Checks if a goto operation is in progress (NOTE: The response is ASCII 1 or 0!)

        :return: True if a goto operation is in progress, False otherwise
        """
        response = self.query(b"L")
        assert len(response) == 1, f"Expected a response with 1 byte! Actual response was {response}"
        return response.decode(ENCODING) == "1"

    def cancel_goto(self) -> None:
        """
        Cancels the current goto operation
        """
        response = self.query(b"M")
        if len(response) != 0:
            log.warning(f"Expected an empty response! Actual response was {response}")
