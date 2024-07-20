#
# Copyright Tristen Georgiou 2024
#

import logging
import time

from nexstar_control.device import NexStarHandControl, TrackingMode
from nexstar_control.device import DeviceType

log = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    hc = NexStarHandControl("COM3")
    if not hc.is_connected():
        log.error("Device is not connected!")
        exit(1)

    # get the device versions
    major, minor = hc.get_device_version(DeviceType.AZM_RA_MOTOR)
    log.info(f"Azimuth/Right Ascension motor version: {major}.{minor}")
    major, minor = hc.get_device_version(DeviceType.ALT_DEC_MOTOR)
    log.info(f"Altitude/Declination motor version: {major}.{minor}")

    # get the device model
    model = hc.get_device_model()
    log.info(f"Device model: {model.name}")

    # check alignment status
    if hc.is_aligned():
        log.info("Alignment is complete")
    else:
        log.info("Alignment is not complete")

    # check if a goto operation is in progress
    if hc.is_goto_in_progress():
        log.info("Goto operation is in progress, cancelling...")
        hc.cancel_goto()  # cancel the goto operation
        log.info("Goto operation has been cancelled")
    else:
        log.info("Goto operation is not in progress")

    # get the current position of the telescope in RA/Dec and Alt/Azm
    ra, dec = hc.get_position_ra_dec()
    log.info(f"Right Ascension: {ra}, Declination: {dec}")

    ra, dec = hc.get_position_ra_dec_precise()
    log.info(f"Right Ascension (precise): {ra}, Declination (precise): {dec}")

    azm, alt = hc.get_position_azm_alt()
    log.info(f"Azimuth: {azm}, Altitude: {alt}")

    azm, alt = hc.get_position_azm_alt_precise()
    log.info(f"Azimuth (precise): {azm}, Altitude (precise): {alt}")

    # tracking mode operations
    mode = hc.get_tracking_mode()
    log.info(f"Tracking mode: {mode.name}")

    hc.set_tracking_mode(TrackingMode.ALT_AZ)
    mode = hc.get_tracking_mode()
    log.info(f"Tracking mode: {mode.name}")

    # goto operations
    log.info("Performing goto operation to RA: 180, Dec: 0")
    hc.goto_ra_dec(180, 0)
    while hc.is_goto_in_progress():
        log.info("Goto operation is in progress...")
        time.sleep(1)
    log.info("Goto operation has completed")

    ra, dec = hc.get_position_ra_dec()
    log.info(f"Right Ascension: {ra}, Declination: {dec}")

    log.info("Performing goto operation to Azm: 0, Alt: 0")
    hc.goto_azm_alt_precise(0, 0)
    while hc.is_goto_in_progress():
        log.info("Goto operation is in progress...")
        time.sleep(1)
    log.info("Goto operation has completed")

    ra, dec = hc.get_position_azm_alt_precise()
    log.info(f"Azimuth: {ra}, Altitude: {dec}")

    # sync operations
    # user centres the telescope on a celestial object rougly and applies a sync
    ra, dec = hc.get_position_ra_dec()
    log.info(f"Syncing telescope to RA: {ra}, Dec: {dec}")
    hc.sync_ra_dec(ra, dec)

    # user centres the telescope on a celestial object precisely and applies a sync
    ra, dec = hc.get_position_ra_dec_precise()
    log.info(f"Syncing telescope to RA: {ra}, Dec: {dec}")
    hc.sync_ra_dec_precise(ra, dec)

    # slew operations
    log.info("Slewing in Azimuth with fixed rate 9")
    hc.slew_azm_fixed(9)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_azm_fixed(0)

    log.info("Slewing in Azimuth with fixed rate -8")
    hc.slew_azm_fixed(-8)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_azm_fixed(0)

    log.info("Slewing in Altitude with fixed rate 9")
    hc.slew_alt_fixed(9)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_alt_fixed(0)

    log.info("Slewing in Altitude with fixed rate -8")
    hc.slew_alt_fixed(-9)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_alt_fixed(0)

    # slew in both directions at the same time
    log.info("Slewing in both Azimuth and Altitude with fixed rate 9")
    hc.slew_fixed(-9, -9)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_stop()

    # slew in azimuth by a variable rate
    log.info("Slewing in Azimuth with variable rate -15000")
    hc.slew_azm_variable(-15000)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_stop()

    # slew in altitude by a variable rate
    log.info("Slewing in Altitude with variable rate 15000")
    hc.slew_alt_variable(15000)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_stop()

    # slew in both directions at the same time by a variable rate
    log.info("Slewing in both Azimuth and Altitude with variable rate 15000, -15000")
    hc.slew_variable(15000, -15000)
    time.sleep(2)
    log.info("Stopping slew operation")
    hc.slew_stop()
